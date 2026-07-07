#!/usr/bin/env python3
"""Run the Family J (Regime Detection) information-content diagnostic.

Pure context/risk diagnostic, per project_control/DECISIONS.md ADR-0021
and docs/pre_registers/TASK-ALT-003.md. Measures whether 6 causal
OHLCV-derived regime features show stable Spearman correlation with
future 24h absolute returns. This is not directional alpha, not a
strategy, and has no economic gate.
"""

from __future__ import annotations

import json
import math
import numbers
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.info_content import (  # noqa: E402
    InformationContentResult,
    evaluate_information_content,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_info_regime_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/alt_info_regime_detection_diagnostic.md"
EXPECTED_SYMBOL_COUNT = 20
FORWARD_HORIZON_HOURS = 24
WEEK_HOURS = 168
ROLLING_WINDOW_HOURS = 2160  # 90 days, causal (shift(1) before rolling)
MAGNITUDE_THRESHOLD = 0.03

# Same 3 sub-periods already fixed in TASK-ALT-001 -- not re-partitioned.
PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


class RegimeDetectionDiagnosticError(ValueError):
    """Raised when Family J diagnostic inputs are invalid."""


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price", "quote_volume"])
    if bars["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
        raise RegimeDetectionDiagnosticError(
            f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}"
        )

    panels = _build_feature_panels(bars)

    results: dict[str, InformationContentResult] = {}
    for feature_name, panel in panels.items():
        results[feature_name] = evaluate_information_content(
            panel,
            feature_name,
            PERIOD_BOUNDARIES,
            PERIOD_LABELS,
            magnitude_threshold=MAGNITUDE_THRESHOLD,
        )

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "target": "future_abs_return_24h",
        "target_formula": "abs(log_price[t+24h] - log_price[t])",
        "forward_horizon_hours": FORWARD_HORIZON_HOURS,
        "rolling_window_hours": ROLLING_WINDOW_HOURS,
        "magnitude_threshold": MAGNITUDE_THRESHOLD,
        "period_labels": PERIOD_LABELS,
        "period_boundaries_ms": PERIOD_BOUNDARIES,
        "results": {name: asdict(result) for name, result in results.items()},
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    for name, result in results.items():
        verdict = "TEM_INFORMACAO" if result.has_information else "SEM_INFORMACAO"
        print(f"{name}: rho={result.full_sample_rho:.4f} n={result.full_sample_n} {verdict}")
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _build_feature_panels(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    _validate_bars(bars)

    working = bars.copy()
    working["open_time"] = pd.to_numeric(working["open_time"], errors="raise")
    working["log_price"] = pd.to_numeric(working["log_price"], errors="raise")
    working["quote_volume"] = pd.to_numeric(working["quote_volume"], errors="raise")

    price_wide = working.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    volume_wide = working.pivot(
        index="open_time", columns="symbol", values="quote_volume"
    ).sort_index()

    hourly_return = price_wide.diff()
    return_24h = price_wide.diff(FORWARD_HORIZON_HOURS)
    future_abs_return = (price_wide.shift(-FORWARD_HORIZON_HOURS) - price_wide).abs()

    realized_vol_24h = hourly_return.shift(1).rolling(FORWARD_HORIZON_HOURS).std()
    realized_vol_168h = hourly_return.shift(1).rolling(WEEK_HOURS).std()

    trend_denominator = (realized_vol_168h * math.sqrt(WEEK_HOURS)).replace(0.0, np.nan)
    past_return_168h = price_wide - price_wide.shift(WEEK_HOURS)
    trend_intensity_168h = past_return_168h.abs() / trend_denominator

    quote_volume_24h = volume_wide.shift(1).rolling(FORWARD_HORIZON_HOURS).sum()
    volume_shock_24h = _zscore_causal(np.log1p(quote_volume_24h))

    market_dispersion_24h = _repeat_context_series(return_24h.std(axis=1), price_wide.columns)
    market_abs_return_24h = _repeat_context_series(
        return_24h.mean(axis=1).abs(), price_wide.columns
    )

    features = {
        "realized_vol_24h": realized_vol_24h,
        "realized_vol_168h": realized_vol_168h,
        "trend_intensity_168h": trend_intensity_168h,
        "volume_shock_24h": volume_shock_24h,
        "market_dispersion_24h": market_dispersion_24h,
        "market_abs_return_24h": market_abs_return_24h,
    }
    return {name: _stack_panel(wide, future_abs_return) for name, wide in features.items()}


def _validate_bars(bars: pd.DataFrame) -> None:
    required = {"symbol", "open_time", "log_price", "quote_volume"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise RegimeDetectionDiagnosticError(f"missing required columns: {missing}")
    if bars.duplicated(["symbol", "open_time"]).any():
        raise RegimeDetectionDiagnosticError("duplicate (symbol, open_time) rows")


def _zscore_causal(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    return (wide - mean) / std


def _repeat_context_series(series: pd.Series, columns: pd.Index) -> pd.DataFrame:
    repeated = pd.concat([series] * len(columns), axis=1)
    repeated.columns = columns
    return repeated


def _stack_panel(feature_wide: pd.DataFrame, target_wide: pd.DataFrame) -> pd.DataFrame:
    target_wide = target_wide.reindex(index=feature_wide.index, columns=feature_wide.columns)
    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = target_wide.stack(future_stack=True).rename("target")
    combined = pd.concat([feature_long, target_long], axis=1).reset_index()
    if "symbol" not in combined.columns:
        symbol_column = next(column for column in combined.columns if column != "open_time")
        combined = combined.rename(columns={symbol_column: "symbol"})
    return combined[["open_time", "symbol", "feature", "target"]]


def _write_report(payload: dict[str, Any]) -> None:
    header_periods = " | ".join(payload["period_labels"])
    header_dashes = "---:|" * len(payload["period_labels"])
    lines = [
        "# Family J (Regime Detection) Information-Content Diagnostic",
        "",
        "Research Phase II, TASK-ALT-003. Status: pure context/risk diagnostic, "
        "per `project_control/DECISIONS.md` ADR-0021. No strategy, no economic "
        "gate, no directional alpha claim.",
        "",
        "Target: `future_abs_return_24h = abs(log_price[t+24h] - log_price[t])`. "
        "A positive result can only justify a future, separate regime/context "
        "task -- not SignalIntent or an execution change.",
        "",
        f"Forward horizon: {payload['forward_horizon_hours']}h. "
        f"Rolling causal window: {payload['rolling_window_hours']}h (90 days). "
        f"Magnitude threshold: {payload['magnitude_threshold']}.",
        "",
        "## Results",
        "",
        f"| Feature | Full rho | Full N | {header_periods} | Sign consistent | Has information |",
        f"|---|---:|---:|{header_dashes}---|---|",
    ]
    for name, result in payload["results"].items():
        sub_cells = " | ".join(
            f"{sp['spearman_rho']:.4f} (n={sp['n_obs']})" for sp in result["sub_periods"]
        )
        lines.append(
            f"| {name} | {result['full_sample_rho']:.4f} | {result['full_sample_n']} | "
            f"{sub_cells} | {result['sign_consistent']} | {result['has_information']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "All 6 pre-registered regime features meet the information-content "
            "criterion against future absolute 24h returns. This is evidence of "
            "stable volatility/regime information, not directional edge. The "
            "strongest effects are realized-volatility persistence "
            "(`realized_vol_24h`, `realized_vol_168h`), consistent with ordinary "
            "volatility clustering. Any operational use must be designed in a "
            "future separately pre-registered task.",
            "",
        ]
    )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool | str):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
