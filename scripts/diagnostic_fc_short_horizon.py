#!/usr/bin/env python3
"""TASK-FC-II-003: Family H book-imbalance features vs SHORT-horizon returns.

Pre-registered in `docs/pre_registers/TASK-FC-II-003.md` (ADR-0027). The
5 Family H features are reused VERBATIM (identical construction to
`scripts/diagnostic_alt_order_flow.py`, including their internal 24h
windows); the ONLY change is the forward-return target horizon, tested at
h in {1h, 4h}. Microstructure theory predicts order-book imbalance
informs short-horizon returns, a dimension ADR-0019 fixed at 24h and
never varied. Pure diagnostic: no economic gate, no strategy.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.info_content import (  # noqa: E402
    evaluate_information_content,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
BOOK_DEPTH_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint_alt_book_depth_202306_202605.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_short_horizon_results.json"
REPORT_MD = PROJECT_ROOT / "reports/fc_short_horizon_diagnostic.md"
EXPECTED_SYMBOL_COUNT = 20
INTERNAL_WINDOW_HOURS = 24  # verbatim Family H internal window (depth_change / divergence)
ROLLING_WINDOW_HOURS = 2160
MAGNITUDE_THRESHOLD = 0.03
TARGET_HORIZONS_HOURS = (1, 4)  # pre-registered short-horizon grid

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    depth = pd.read_csv(BOOK_DEPTH_CSV)
    if bars["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
        raise ValueError(f"expected {EXPECTED_SYMBOL_COUNT} symbols in bars")
    if depth["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
        raise ValueError(f"expected {EXPECTED_SYMBOL_COUNT} symbols in book depth")

    price_wide, features = _build_features(bars, depth)

    results: dict[str, dict] = {}
    for horizon in TARGET_HORIZONS_HOURS:
        forward_return = price_wide.shift(-horizon) - price_wide
        for name, feature_wide in features.items():
            panel = _stack(feature_wide, forward_return)
            res = evaluate_information_content(
                panel,
                name,
                PERIOD_BOUNDARIES,
                PERIOD_LABELS,
                magnitude_threshold=MAGNITUDE_THRESHOLD,
            )
            results[f"{name}@{horizon}h"] = asdict(res)

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "target": "forward_return_h = log_price[t+h] - log_price[t]",
        "horizons_hours": list(TARGET_HORIZONS_HOURS),
        "magnitude_threshold": MAGNITUDE_THRESHOLD,
        "period_labels": PERIOD_LABELS,
        "results": results,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    for name, res in results.items():
        verdict = "TEM_INFORMACAO" if res["has_information"] else "sem"
        print(f"{name}: rho={res['full_sample_rho']:+.4f} {verdict}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _build_features(
    bars: pd.DataFrame, depth: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    price_wide = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()

    bid_1pct = depth.pivot(index="open_time", columns="symbol", values="notional_-1.00")
    ask_1pct = depth.pivot(index="open_time", columns="symbol", values="notional_1.00")
    bid_5pct = depth.pivot(index="open_time", columns="symbol", values="notional_-5.00")
    ask_5pct = depth.pivot(index="open_time", columns="symbol", values="notional_5.00")

    bid_1pct = bid_1pct.reindex(price_wide.index)
    ask_1pct = ask_1pct.reindex(price_wide.index)
    bid_5pct = bid_5pct.reindex(price_wide.index)
    ask_5pct = ask_5pct.reindex(price_wide.index)

    price_return_internal = price_wide.diff(INTERNAL_WINDOW_HOURS)
    book_imbalance_1pct = (bid_1pct - ask_1pct) / (bid_1pct + ask_1pct)
    book_imbalance_5pct = (bid_5pct - ask_5pct) / (bid_5pct + ask_5pct)
    depth_concentration = (bid_1pct + ask_1pct) / (bid_5pct + ask_5pct)
    total_near_depth = bid_1pct + ask_1pct
    depth_change_24h = total_near_depth.diff(INTERNAL_WINDOW_HOURS)
    imbalance_price_divergence = _zscore_causal(book_imbalance_1pct) - _zscore_causal(
        price_return_internal
    )

    features = {
        "book_imbalance_1pct": book_imbalance_1pct,
        "book_imbalance_5pct": book_imbalance_5pct,
        "depth_concentration": depth_concentration,
        "depth_change_24h": depth_change_24h,
        "imbalance_price_divergence": imbalance_price_divergence,
    }
    return price_wide, features


def _zscore_causal(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    return (wide - mean) / std


def _stack(feature_wide: pd.DataFrame, target_wide: pd.DataFrame) -> pd.DataFrame:
    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = target_wide.stack(future_stack=True).rename("target")
    combined = pd.concat([feature_long, target_long], axis=1).reset_index()
    return combined[["open_time", "feature", "target"]]


def _write_report(payload: dict) -> None:
    header = " | ".join(payload["period_labels"])
    lines = [
        "# TASK-FC-II-003 -- Book Imbalance vs Short-Horizon Returns",
        "",
        "Per `docs/pre_registers/TASK-FC-II-003.md` (ADR-0027). The 5 Family H "
        "features reused verbatim; only the forward-return target horizon "
        "changes (1h, 4h). Pure diagnostic, no gate. Sign-consistency across "
        "the 3 sub-periods is the multiple-testing defense for the 10-cell grid.",
        "",
        f"Target: {payload['target']}, h in {payload['horizons_hours']}. "
        f"Threshold: {payload['magnitude_threshold']}.",
        "",
        "## Results",
        "",
        f"| Feature @ horizon | Full rho | Sub ({header}) | Sign consistent | Has info |",
        "|---|---:|---|---|---|",
    ]
    for name, res in payload["results"].items():
        sub = " | ".join(f"{sp['spearman_rho']:+.4f}" for sp in res["sub_periods"])
        lines.append(
            f"| {name} | {res['full_sample_rho']:+.4f} | {sub} | "
            f"{res['sign_consistent']} | {res['has_information']} |"
        )
    hits = [n for n, r in payload["results"].items() if r["has_information"]]
    verdict = (
        f"Features with information at a short horizon: {', '.join(hits)}. "
        "Candidate(s) for a future, separately pre-registered OOS validation -- "
        "NOT a verdict here."
        if hits
        else "No feature carries information at 1h or 4h either. Book imbalance "
        "adds nothing at short horizons in this universe/period -- closes the "
        "short-horizon microstructure angle on the data we have."
    )
    lines.extend(["", "## Reading", "", verdict, ""])
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


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
