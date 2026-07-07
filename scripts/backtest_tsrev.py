#!/usr/bin/env python3
"""Run the pre-registered TSREV backtest grid (TASK-TSREV-001/002).

Exactly one cell is decisive: Family A (time-series reversal), 24h
horizon, gate evaluated ONLY on the out-of-sample period (2025-06 through
2026-05). Every other cell -- Family A at 6h/12h/48h, Family B
(cross-sectional) at 6h/12h/24h/48h -- is descriptive only and reported
for context/robustness, never substituted for the primary result. See
docs/pre_registers/TASK-TSREV-001.md and project_control/DECISIONS.md
ADR-0014.
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

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsrev import (  # noqa: E402
    CrossSectionalReversalConfig,
    TimeSeriesReversalConfig,
    buy_and_hold_max_drawdown_bps,
    run_cross_sectional_reversal_backtest,
    run_time_series_reversal_backtest,
    split_out_of_sample,
    summarize_cross_sectional_reversal,
    summarize_time_series_reversal,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsrev_backtest_results.json"
REPORT_MD = PROJECT_ROOT / "reports/tsrev_backtest_final.md"
EXPECTED_SYMBOL_COUNT = 20
OOS_START = "2025-06-01"
PRIMARY_HORIZON = 24
SECONDARY_A_HORIZONS = (6, 12, 48)
SECONDARY_B_HORIZONS = (6, 12, 24, 48)


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    symbol_count = bars["symbol"].nunique()
    if symbol_count != EXPECTED_SYMBOL_COUNT:
        raise ValueError(
            f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}, got {symbol_count}"
        )

    oos_start_ms = int(pd.Timestamp(OOS_START, tz="UTC").timestamp() * 1000)
    _, oos_bars = split_out_of_sample(bars, oos_start_ms)
    oos_wide = oos_bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    baseline_dd_bps = buy_and_hold_max_drawdown_bps(oos_wide)

    family_a_cells: dict[int, dict[str, Any]] = {}
    for horizon in (PRIMARY_HORIZON, *SECONDARY_A_HORIZONS):
        config = TimeSeriesReversalConfig(horizon_hours=horizon)
        trades = run_time_series_reversal_backtest(bars, config)
        oos_trades = tuple(t for t in trades if t.entry_time >= oos_start_ms)
        is_trades = tuple(t for t in trades if t.entry_time < oos_start_ms)
        is_baseline = None  # in-sample is context only, never gated
        family_a_cells[horizon] = {
            "config": asdict(config),
            "oos_summary": asdict(
                summarize_time_series_reversal(oos_trades, config, baseline_dd_bps)
            ),
            "in_sample_summary": asdict(
                summarize_time_series_reversal(is_trades, config, is_baseline)
            ),
            "full_sample_summary": asdict(summarize_time_series_reversal(trades, config)),
        }

    family_b_cells: dict[int, dict[str, Any]] = {}
    for horizon in SECONDARY_B_HORIZONS:
        config = CrossSectionalReversalConfig(horizon_hours=horizon)
        results = run_cross_sectional_reversal_backtest(bars, config)
        family_b_cells[horizon] = {
            "config": asdict(config),
            "full_sample_summary": summarize_cross_sectional_reversal(results),
        }

    primary_gate_pass = family_a_cells[PRIMARY_HORIZON]["oos_summary"]["gate_pass"]
    gate_decision = "PASSA" if primary_gate_pass else "NAO_PASSA"

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "oos_start": OOS_START,
        "baseline_max_drawdown_bps_oos": baseline_dd_bps,
        "primary_horizon_hours": PRIMARY_HORIZON,
        "gate_decision": gate_decision,
        "family_a_cells": family_a_cells,
        "family_b_cells": family_b_cells,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    console_payload = {
        "gate_decision": gate_decision,
        "baseline_max_drawdown_bps_oos": baseline_dd_bps,
        "primary_oos_summary": family_a_cells[PRIMARY_HORIZON]["oos_summary"],
    }
    print(json.dumps(_json_ready(console_payload), indent=2))
    print(f"GATE (primary, TSREV 24h, out-of-sample only): {gate_decision}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(payload: dict[str, Any]) -> None:
    primary = payload["family_a_cells"][PRIMARY_HORIZON]
    lines = [
        "# TSREV Backtest Final Result (Research Family C)",
        "",
        "Status: real result for the pre-registered grid in "
        "`docs/pre_registers/TASK-TSREV-001.md`. Only the primary cell "
        "(Family A, 24h, out-of-sample) decides the gate.",
        "",
        f"**GATE (primary, decisive): {payload['gate_decision']}**",
        "",
        f"Out-of-sample period: {payload['oos_start']} through end of dataset.",
        f"Buy-and-hold benchmark max drawdown (OOS): "
        f"{_fmt(payload['baseline_max_drawdown_bps_oos'])} bps.",
        "",
        "## Primary cell: Family A (Time-Series Reversal), 24h",
        "",
        "| Period | Trades | Win rate | Net PnL (bps) | Net PF | Max DD (bps) | Gate |",
        "|---|---:|---:|---:|---:|---:|---|",
        _summary_row("Out-of-sample (decisive)", primary["oos_summary"]),
        _summary_row("In-sample (context only)", primary["in_sample_summary"]),
        _summary_row("Full sample (context only)", primary["full_sample_summary"]),
        "",
        "## Secondary cells: Family A (Time-Series Reversal), other horizons",
        "",
        "Descriptive only -- cannot decide the gate, cannot override the "
        "primary result above, per the pre-registered rule.",
        "",
        "| Horizon | Trades (OOS) | Win rate (OOS) | Net PnL bps (OOS) | Net PF (OOS) |",
        "|---|---:|---:|---:|---:|",
    ]
    for horizon in SECONDARY_A_HORIZONS:
        cell = payload["family_a_cells"][horizon]["oos_summary"]
        lines.append(
            f"| {horizon}h | {cell['resolved_count']} | {_fmt_pct(cell['win_rate'])} | "
            f"{_fmt(cell['net_pnl_bps'])} | {_fmt(cell['profit_factor'])} |"
        )
    lines += [
        "",
        "## Secondary cells: Family B (Cross-Sectional Reversal), full sample",
        "",
        "Descriptive only. Full sample (no OOS split -- purely exploratory).",
        "",
        "| Horizon | Rebalances | Net PnL (bps) | Net PF |",
        "|---|---:|---:|---:|",
    ]
    for horizon in SECONDARY_B_HORIZONS:
        cell = payload["family_b_cells"][horizon]["full_sample_summary"]
        lines.append(
            f"| {horizon}h | {cell['resolved_count']} | {_fmt(cell['net_pnl_bps'])} | "
            f"{_fmt(cell['profit_factor'])} |"
        )
    lines.append("")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _summary_row(label: str, summary: dict[str, Any]) -> str:
    gate = summary.get("gate_pass")
    gate_text = "PASSA" if gate else ("NAO_PASSA" if gate is not None else "NA")
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
