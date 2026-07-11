#!/usr/bin/env python3
"""TASK-FC-II-002: information-content diagnostic of the spot-futures basis.

Pre-registered in `docs/pre_registers/TASK-FC-II-002.md` (under ADR-0027).
Tests whether the instantaneous basis (Binance premium index, already in the
sprint7 futures bars) carries information about the 24h forward return, and
-- the decisive question -- whether it carries information INCREMENTAL to the
settled funding rate (partial Spearman controlling for funding). Pure
diagnostic: no economic gate, no strategy, no real action.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.info_content import (  # noqa: E402
    evaluate_information_content,
    partial_spearman_rho,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_basis_results.json"
REPORT_MD = PROJECT_ROOT / "reports/fc_basis_diagnostic.md"
EXPECTED_SYMBOL_COUNT = 20
FORWARD_HORIZON_HOURS = 24
ROLLING_WINDOW_HOURS = 2160
MAGNITUDE_THRESHOLD = 0.03

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


class BasisDiagnosticError(ValueError):
    """Raised when the basis diagnostic inputs are invalid."""


def main() -> int:
    bars = pd.read_csv(
        BARS_CSV,
        usecols=["symbol", "open_time", "log_price", "premium_close", "funding_rate_asof"],
    )
    if bars["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
        raise BasisDiagnosticError(f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}")

    panels = _build_feature_panels(bars)

    results = {}
    for name, panel in panels.items():
        standard = evaluate_information_content(
            panel[["open_time", "symbol", "feature", "target"]],
            name,
            PERIOD_BOUNDARIES,
            PERIOD_LABELS,
            magnitude_threshold=MAGNITUDE_THRESHOLD,
        )
        incremental = _partial_over_funding(panel)
        results[name] = {"standard": standard, "incremental": incremental}

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "target": "forward_return_24h = log_price[t+24h] - log_price[t]",
        "control_for_incremental": "funding_rate_asof",
        "magnitude_threshold": MAGNITUDE_THRESHOLD,
        "period_labels": PERIOD_LABELS,
        "results": {
            name: {
                "standard_full_rho": r["standard"].full_sample_rho,
                "standard_has_information": r["standard"].has_information,
                "standard_sub_rho": [sp.spearman_rho for sp in r["standard"].sub_periods],
                "incremental_full_partial_rho": r["incremental"]["full_partial_rho"],
                "incremental_sub_partial_rho": r["incremental"]["sub_partial_rho"],
                "incremental_sign_consistent": r["incremental"]["sign_consistent"],
                "has_incremental_information": r["incremental"]["has_incremental_information"],
            }
            for name, r in results.items()
        },
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    for name, r in results.items():
        std = r["standard"]
        inc = r["incremental"]
        std_v = "TEM" if std.has_information else "sem"
        inc_v = "TEM" if inc["has_incremental_information"] else "sem"
        print(
            f"{name}: rho={std.full_sample_rho:+.4f} ({std_v} info) | "
            f"partial|funding={inc['full_partial_rho']:+.4f} ({inc_v} info incremental)",
            file=sys.stderr,
        )
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _build_feature_panels(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if bars.duplicated(["symbol", "open_time"]).any():
        raise BasisDiagnosticError("duplicate (symbol, open_time) rows")
    working = bars.copy()
    for column in ("open_time", "log_price", "premium_close", "funding_rate_asof"):
        working[column] = pd.to_numeric(working[column], errors="raise")

    price = working.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    premium = working.pivot(
        index="open_time", columns="symbol", values="premium_close"
    ).sort_index()
    funding = working.pivot(
        index="open_time", columns="symbol", values="funding_rate_asof"
    ).sort_index()

    future_return = price.shift(-FORWARD_HORIZON_HOURS) - price

    premium_mean = premium.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    premium_std = premium.shift(1).rolling(ROLLING_WINDOW_HOURS).std()

    features = {
        "basis_level": premium,
        "basis_zscore": (premium - premium_mean) / premium_std,
        "basis_change_24h": premium - premium.shift(FORWARD_HORIZON_HOURS),
        "basis_excess_funding": premium - funding,
    }
    return {
        name: _stack(feature_wide, future_return, funding)
        for name, feature_wide in features.items()
    }


def _stack(feature: pd.DataFrame, target: pd.DataFrame, control: pd.DataFrame) -> pd.DataFrame:
    target = target.reindex(index=feature.index, columns=feature.columns)
    control = control.reindex(index=feature.index, columns=feature.columns)
    long = pd.concat(
        [
            feature.stack(future_stack=True).rename("feature"),
            target.stack(future_stack=True).rename("target"),
            control.stack(future_stack=True).rename("control"),
        ],
        axis=1,
    ).reset_index()
    if "symbol" not in long.columns:
        named = ("open_time", "feature", "target", "control")
        symbol_column = next(c for c in long.columns if c not in named)
        long = long.rename(columns={symbol_column: "symbol"})
    return long[["open_time", "symbol", "feature", "target", "control"]]


def _partial_over_funding(panel: pd.DataFrame) -> dict:
    full_rho, _ = partial_spearman_rho(panel["feature"], panel["target"], panel["control"])
    sub_rhos = []
    for start, end in zip(PERIOD_BOUNDARIES[:-1], PERIOD_BOUNDARIES[1:], strict=True):
        window = panel[(panel["open_time"] >= start) & (panel["open_time"] < end)]
        rho, _ = partial_spearman_rho(window["feature"], window["target"], window["control"])
        sub_rhos.append(rho)

    all_rhos = [full_rho, *sub_rhos]
    all_finite = all(math.isfinite(r) for r in all_rhos)
    sign_consistent = all_finite and (all(r > 0 for r in all_rhos) or all(r < 0 for r in all_rhos))
    has_incremental = (
        math.isfinite(full_rho) and abs(full_rho) >= MAGNITUDE_THRESHOLD and sign_consistent
    )
    return {
        "full_partial_rho": full_rho,
        "sub_partial_rho": sub_rhos,
        "sign_consistent": sign_consistent,
        "has_incremental_information": has_incremental,
    }


def _write_report(payload: dict) -> None:
    header = " | ".join(payload["period_labels"])
    lines = [
        "# TASK-FC-II-002 -- Spot-Futures Basis Information-Content Diagnostic",
        "",
        "Per `docs/pre_registers/TASK-FC-II-002.md` (ADR-0027). Pure diagnostic: "
        "no economic gate. The decisive column is INCREMENTAL information over "
        "funding (partial Spearman controlling for `funding_rate_asof`) -- a "
        "feature that passes only the standard test but not the incremental one "
        "is merely re-expressing the carry we already have.",
        "",
        f"Target: {payload['target']}. Threshold: {payload['magnitude_threshold']}.",
        "",
        "## Results",
        "",
        f"| Feature | Standard rho | Standard sub ({header}) | Has info | "
        f"Partial rho \\| funding | Partial sub | Incremental info |",
        "|---|---:|---|---|---:|---|---|",
    ]
    for name, r in payload["results"].items():
        std_sub = ", ".join(f"{v:+.4f}" for v in r["standard_sub_rho"])
        inc_sub = ", ".join(
            f"{v:+.4f}" if v is not None else "nan" for v in r["incremental_sub_partial_rho"]
        )
        lines.append(
            f"| {name} | {r['standard_full_rho']:+.4f} | {std_sub} | "
            f"{r['standard_has_information']} | {r['incremental_full_partial_rho']:+.4f} | "
            f"{inc_sub} | {r['has_incremental_information']} |"
        )
    lines.extend(["", "## Reading", "", _verdict_prose(payload), ""])
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _verdict_prose(payload: dict) -> str:
    incremental = [n for n, r in payload["results"].items() if r["has_incremental_information"]]
    if incremental:
        return (
            "Features with INCREMENTAL information over funding: "
            f"{', '.join(incremental)}. These are legitimate candidates for a "
            "future, separately pre-registered strategy task -- NOT a strategy "
            "here, and NOT validated out-of-sample. Everything else either shows "
            "no information or only re-expresses the funding carry."
        )
    return (
        "No feature carries information INCREMENTAL to the funding rate. The "
        "basis adds nothing beyond the carry already captured by funding in "
        "this universe/period -- consistent with the Family G null. Basis closes "
        "as a standalone avenue; move to a source with higher independent-"
        "information prior (options IV/skew, on-chain), accepting their higher "
        "data-acquisition cost."
    )


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
