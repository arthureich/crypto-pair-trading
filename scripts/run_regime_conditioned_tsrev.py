#!/usr/bin/env python3
"""Run TASK-ALT-004 regime-conditioned TSREV feasibility diagnostic.

This is a feasibility screen only, per ADR-0022. It applies one
pre-registered high-volatility regime filter to the existing TSREV
Family A 24h strategy and compares the filtered OOS result against the
original TSREV OOS baseline. A positive result cannot authorize paper or
live trading; it only motivates a future new-OOS validation.
"""

from __future__ import annotations

import json
import math
import numbers
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsrev import (  # noqa: E402
    TimeSeriesReversalConfig,
    TradeStatus,
    TSREVTrade,
    buy_and_hold_max_drawdown_bps,
    run_time_series_reversal_backtest,
    summarize_time_series_reversal,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/regime_conditioned_tsrev_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/regime_conditioned_tsrev_feasibility.md"
EXPECTED_SYMBOL_COUNT = 20
OOS_START = "2025-06-01"
PRIMARY_HORIZON_HOURS = 24
REALIZED_VOL_WINDOW_HOURS = 168
QUANTILE_LOOKBACK_HOURS = 2160
HIGH_VOL_QUANTILE = 0.67
HOUR_MS = 3_600_000
MIN_ROLLING_WINDOW_HOURS = 2


class RegimeConditioningError(ValueError):
    """Raised when regime-conditioning inputs are invalid."""


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    symbol_count = bars["symbol"].nunique()
    if symbol_count != EXPECTED_SYMBOL_COUNT:
        raise RegimeConditioningError(
            f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}, got {symbol_count}"
        )

    config = TimeSeriesReversalConfig(horizon_hours=PRIMARY_HORIZON_HOURS)
    oos_start_ms = int(pd.Timestamp(OOS_START, tz="UTC").timestamp() * 1000)
    oos_bars = bars[bars["open_time"] >= oos_start_ms].copy()
    oos_wide = oos_bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    baseline_dd_bps = buy_and_hold_max_drawdown_bps(oos_wide)

    trades = run_time_series_reversal_backtest(bars, config)
    oos_trades = tuple(trade for trade in trades if trade.entry_time >= oos_start_ms)
    baseline_summary = summarize_time_series_reversal(oos_trades, config, baseline_dd_bps)

    allow_entry, _, _ = build_high_vol_regime_filter(bars)
    filtered_raw = filter_trades_by_regime(oos_trades, allow_entry)
    filtered_trades = renormalize_tsrev_trade_weights(filtered_raw)
    filtered_summary = summarize_time_series_reversal(filtered_trades, config, baseline_dd_bps)

    gate_decision = "PASSA" if filtered_summary.gate_pass else "NAO_PASSA"
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "oos_start": OOS_START,
        "config": asdict(config),
        "filter": {
            "feature": "realized_vol_168h",
            "realized_vol_window_hours": REALIZED_VOL_WINDOW_HOURS,
            "quantile_lookback_hours": QUANTILE_LOOKBACK_HOURS,
            "high_vol_quantile": HIGH_VOL_QUANTILE,
            "allow_rule": "realized_vol_168h[t] <= prior_90d_q67[t]",
            "missing_regime": "BLOCK_ENTRY",
        },
        "baseline_max_drawdown_bps_oos": baseline_dd_bps,
        "baseline_summary": asdict(baseline_summary),
        "filtered_summary": asdict(filtered_summary),
        "total_oos_trades": len(oos_trades),
        "filtered_oos_trades": len(filtered_trades),
        "blocked_oos_trades": len(oos_trades) - len(filtered_trades),
        "gate_decision": gate_decision,
        "scope_warning": (
            "feasibility only; 2025-06/2026-05 was already analyzed, so PASSA "
            "would still require a future new-OOS validation"
        ),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    print(json.dumps(_json_ready(payload["filtered_summary"]), indent=2))
    print(f"GATE (filtered feasibility): {gate_decision}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def build_high_vol_regime_filter(
    bars: pd.DataFrame,
    realized_vol_window_hours: int = REALIZED_VOL_WINDOW_HOURS,
    quantile_lookback_hours: int = QUANTILE_LOOKBACK_HOURS,
    high_vol_quantile: float = HIGH_VOL_QUANTILE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (allow_entry, realized_vol, q_threshold), all indexed by open_time.

    ``allow_entry`` is false when the regime inputs are missing. The
    quantile threshold is causal because it shifts the realized-vol panel
    before calculating the rolling quantile.
    """

    _validate_filter_inputs(
        bars, realized_vol_window_hours, quantile_lookback_hours, high_vol_quantile
    )
    frame = bars[["symbol", "open_time", "log_price"]].copy()
    frame["open_time"] = pd.to_numeric(frame["open_time"], errors="raise")
    frame["log_price"] = pd.to_numeric(frame["log_price"], errors="raise")
    wide = frame.pivot(index="open_time", columns="symbol", values="log_price").sort_index()

    hourly_return = wide.diff()
    realized_vol = hourly_return.shift(1).rolling(realized_vol_window_hours).std()
    threshold = realized_vol.shift(1).rolling(quantile_lookback_hours).quantile(
        high_vol_quantile
    )
    allow_entry = (realized_vol <= threshold).fillna(False).astype(bool)
    return allow_entry, realized_vol, threshold


def _validate_filter_inputs(
    bars: pd.DataFrame,
    realized_vol_window_hours: int,
    quantile_lookback_hours: int,
    high_vol_quantile: float,
) -> None:
    required = {"symbol", "open_time", "log_price"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise RegimeConditioningError(f"missing required columns: {missing}")
    if bars.duplicated(["symbol", "open_time"]).any():
        raise RegimeConditioningError("duplicate (symbol, open_time) rows")
    if realized_vol_window_hours < MIN_ROLLING_WINDOW_HOURS:
        raise RegimeConditioningError("realized_vol_window_hours must be >= 2")
    if quantile_lookback_hours < MIN_ROLLING_WINDOW_HOURS:
        raise RegimeConditioningError("quantile_lookback_hours must be >= 2")
    if not math.isfinite(high_vol_quantile) or not 0.0 < high_vol_quantile < 1.0:
        raise RegimeConditioningError("high_vol_quantile must be between 0 and 1")


def filter_trades_by_regime(
    trades: tuple[TSREVTrade, ...],
    allow_entry: pd.DataFrame,
) -> tuple[TSREVTrade, ...]:
    """Keep only trades whose entry symbol/time has allow_entry=True."""

    kept = []
    for trade in trades:
        if trade.symbol not in allow_entry.columns or trade.entry_time not in allow_entry.index:
            continue
        if bool(allow_entry.at[trade.entry_time, trade.symbol]):
            kept.append(trade)
    return tuple(kept)


def renormalize_tsrev_trade_weights(trades: tuple[TSREVTrade, ...]) -> tuple[TSREVTrade, ...]:
    """Renormalize resolved TSREV trades by inverse entry sigma after filtering."""

    resolved = [trade for trade in trades if trade.status is TradeStatus.RESOLVED]
    if not resolved:
        return trades
    inverse_sigmas = [
        1.0 / trade.entry_sigma_h
        if math.isfinite(trade.entry_sigma_h) and trade.entry_sigma_h > 0.0
        else 0.0
        for trade in resolved
    ]
    mean_inverse_sigma = sum(inverse_sigmas) / len(inverse_sigmas)
    if mean_inverse_sigma <= 0.0:
        return tuple(
            replace(trade, weight=0.0) if trade.status is TradeStatus.RESOLVED else trade
            for trade in trades
        )

    weight_by_key = {
        (trade.symbol, trade.entry_time): inverse_sigma / mean_inverse_sigma
        for trade, inverse_sigma in zip(resolved, inverse_sigmas, strict=True)
    }
    return tuple(
        replace(trade, weight=weight_by_key[(trade.symbol, trade.entry_time)])
        if trade.status is TradeStatus.RESOLVED
        else replace(trade, weight=0.0)
        for trade in trades
    )


def _write_report(payload: dict[str, Any]) -> None:
    baseline = payload["baseline_summary"]
    filtered = payload["filtered_summary"]
    lines = [
        "# Regime-Conditioned TSREV Feasibility Diagnostic",
        "",
        "TASK-ALT-004, ADR-0022. Feasibility only: the OOS window used here "
        "(2025-06 through 2026-05) has already been analyzed elsewhere, so a "
        "PASSA would still require future new-OOS validation.",
        "",
        f"**GATE (filtered feasibility): {payload['gate_decision']}**",
        "",
        "Filter: block TSREV 24h entries when `realized_vol_168h[t]` is above "
        "the symbol's causal 90-day 67th percentile. Missing regime data blocks "
        "entry. Remaining trades are renormalized by the original inverse-vol "
        "sizing convention.",
        "",
        f"Buy-and-hold benchmark max drawdown (OOS): "
        f"{_fmt(payload['baseline_max_drawdown_bps_oos'])} bps.",
        "",
        "## Results",
        "",
        "| Cell | Trades | Win rate | Net PnL (bps) | Net PF | Max DD (bps) | Gate |",
        "|---|---:|---:|---:|---:|---:|---|",
        _summary_row("Original TSREV 24h OOS", baseline),
        _summary_row("Regime-filtered TSREV 24h OOS", filtered),
        "",
        "## Trade Flow",
        "",
        f"- Total OOS trades before filter: {payload['total_oos_trades']}",
        f"- Kept after regime filter: {payload['filtered_oos_trades']}",
        f"- Blocked by regime/missing-regime: {payload['blocked_oos_trades']}",
        "",
        "## Interpretation",
        "",
        "This diagnostic tests whether regime information can plausibly reduce "
        "TSREV's drawdown problem. It is not a clean confirmation because the "
        "same OOS year has already informed prior project decisions.",
        "",
        "Result: the pre-registered high-volatility block does not solve the "
        "problem. It reduces the original TSREV max drawdown only modestly, "
        "keeps drawdown far above the buy-and-hold benchmark, and flips net "
        "PnL negative. This regime-conditioning variant stops here.",
        "",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _summary_row(label: str, summary: dict[str, Any]) -> str:
    gate = summary.get("gate_pass")
    gate_text = "PASSA" if gate else "NAO_PASSA"
    return (
        f"| {label} | {summary['resolved_count']} | {_fmt_pct(summary['win_rate'])} | "
        f"{_fmt(summary['net_pnl_bps'])} | {_fmt(summary['profit_factor'])} | "
        f"{_fmt(summary['max_drawdown_bps'])} | {gate_text} |"
    )


def _fmt(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    if isinstance(value, float) and math.isinf(value):
        return "+inf" if value > 0 else "-inf"
    return f"{value:.2f}"


def _fmt_pct(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{value * 100.0:.2f}%"


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
