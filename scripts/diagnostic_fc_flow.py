#!/usr/bin/env python3
"""TASK-FC-II-004: Family E (Flow) information-content diagnostic.

Pre-registered in `docs/pre_registers/TASK-FC-II-004.md` (ADR-0027).
Aggressor taker flow (from the sprint7 bars) and long/short positioning
ratios (from the `metrics` archives already downloaded for Open Interest)
-- both on disk, never tested for flow. 5 causal features vs the forward
return at 24h and 4h. Pure diagnostic: no economic gate, no strategy.
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

from src.research.info_content import evaluate_information_content  # noqa: E402

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
METRICS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint_alt_open_interest_202306_202605.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_flow_results.json"
REPORT_MD = PROJECT_ROOT / "reports/fc_flow_diagnostic.md"
EXPECTED_SYMBOL_COUNT = 20
ROLLING_WINDOW_HOURS = 2160
MAGNITUDE_THRESHOLD = 0.03
TARGET_HORIZONS_HOURS = (24, 4)

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


def main() -> int:
    bars = pd.read_csv(
        BARS_CSV,
        usecols=["symbol", "open_time", "log_price", "quote_volume", "taker_buy_quote_volume"],
    )
    metrics = pd.read_csv(METRICS_CSV)
    for frame, name in ((bars, "bars"), (metrics, "metrics")):
        if frame["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
            raise ValueError(f"expected {EXPECTED_SYMBOL_COUNT} symbols in {name}")

    price_wide, features = _build_features(bars, metrics)

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
    bars: pd.DataFrame, metrics: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    price_wide = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    quote = bars.pivot(index="open_time", columns="symbol", values="quote_volume")
    taker_buy = bars.pivot(index="open_time", columns="symbol", values="taker_buy_quote_volume")
    taker_buy_fraction = (taker_buy / quote).reindex(price_wide.index)

    def metric_wide(column: str) -> pd.DataFrame:
        return metrics.pivot(index="open_time", columns="symbol", values=column).reindex(
            price_wide.index
        )

    features = {
        "taker_buy_fraction": taker_buy_fraction,
        "taker_buy_fraction_z": _zscore_causal(taker_buy_fraction),
        "taker_lsv_ratio_z": _zscore_causal(metric_wide("sum_taker_long_short_vol_ratio")),
        "toptrader_ls_ratio_z": _zscore_causal(metric_wide("sum_toptrader_long_short_ratio")),
        "global_ls_ratio_z": _zscore_causal(metric_wide("count_long_short_ratio")),
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
        "# TASK-FC-II-004 -- Family E (Flow) Information-Content Diagnostic",
        "",
        "Per `docs/pre_registers/TASK-FC-II-004.md` (ADR-0027). Aggressor taker "
        "flow (bars) + long/short positioning ratios (metrics archives already "
        "on disk), 5 causal features vs 24h and 4h forward return. Pure "
        "diagnostic. Sign-consistency across 3 sub-periods is the "
        "multiple-testing defense for the 10-cell grid.",
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
        f"Features with information: {', '.join(hits)}. Each must pass the "
        "descriptive economic check (gross spread vs cost) before any strategy "
        "pre-registration -- information is not a tradeable edge."
        if hits
        else "No flow feature carries information at 24h or 4h. Family E (Flow) "
        "closes: no economically-relevant directional information in aggressor "
        "taker flow or long/short positioning ratios in this universe/period."
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
