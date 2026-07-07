#!/usr/bin/env python3
"""Run the pre-registered cross-sectional mean reversion backtest (TASK-CS-002).

A single, fixed hypothesis at a 24h horizon -- deliberately NOT the same
168h horizon as CS-001 (mirroring that exact horizon/ranking with sides
swapped would make OOS net PnL negative by mathematical construction, an
uninformative test; see project_control/DECISIONS.md ADR-0018). Gate is
evaluated ONLY on the out-of-sample period (2025-06 through 2026-05, the
same boundary already pre-registered in TASK-TSREV-001/TASK-CS-001,
reused here without re-choosing it). No sweep, no secondary cells -- see
docs/pre_registers/TASK-CS-002.md.
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

from src.research.cs_reversion import (  # noqa: E402
    CrossSectionalReversionConfig,
    buy_and_hold_max_drawdown_bps,
    run_cross_sectional_reversion_backtest,
    split_out_of_sample,
    summarize_cross_sectional_reversion,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/cs_reversion_backtest_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/cs_reversion_backtest_final.md"
EXPECTED_SYMBOL_COUNT = 20
OOS_START = "2025-06-01"


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    symbol_count = bars["symbol"].nunique()
    if symbol_count != EXPECTED_SYMBOL_COUNT:
        raise ValueError(
            f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}, got {symbol_count}"
        )

    oos_start_ms = int(pd.Timestamp(OOS_START, tz="UTC").timestamp() * 1000)
    is_bars, oos_bars = split_out_of_sample(bars, oos_start_ms)
    oos_wide = oos_bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    baseline_dd_bps = buy_and_hold_max_drawdown_bps(oos_wide)

    config = CrossSectionalReversionConfig()
    trades = run_cross_sectional_reversion_backtest(bars, config)
    oos_trades = tuple(t for t in trades if t.entry_time >= oos_start_ms)
    is_trades = tuple(t for t in trades if t.entry_time < oos_start_ms)

    oos_summary = summarize_cross_sectional_reversion(oos_trades, config, baseline_dd_bps)
    is_summary = summarize_cross_sectional_reversion(is_trades, config)
    full_summary = summarize_cross_sectional_reversion(trades, config)

    gate_decision = "PASSA" if oos_summary.gate_pass else "NAO_PASSA"

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "oos_start": OOS_START,
        "baseline_max_drawdown_bps_oos": baseline_dd_bps,
        "config": asdict(config),
        "gate_decision": gate_decision,
        "oos_summary": asdict(oos_summary),
        "in_sample_summary": asdict(is_summary),
        "full_sample_summary": asdict(full_summary),
        "in_sample_bar_count": int(len(is_bars)),
        "out_of_sample_bar_count": int(len(oos_bars)),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    console_payload = {"gate_decision": gate_decision, "oos_summary": asdict(oos_summary)}
    print(json.dumps(_json_ready(console_payload), indent=2))
    print(f"GATE (TASK-CS-002, 24h mean reversion, OOS only): {gate_decision}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(payload: dict[str, Any]) -> None:
    lines = [
        "# Cross-Sectional Mean Reversion Backtest Final Result (Research Family E, TASK-CS-002)",
        "",
        "Status: real result for the pre-registered hypothesis in "
        "`docs/pre_registers/TASK-CS-002.md` -- 24h horizon, deliberately "
        "distinct from CS-001's 168h (a same-horizon mirror would fail the "
        "gate by mathematical construction, see ADR-0018). Gate is decided "
        "ONLY on the out-of-sample period.",
        "",
        f"**GATE (decisive): {payload['gate_decision']}**",
        "",
        f"Out-of-sample period: {payload['oos_start']} through end of dataset "
        f"({payload['out_of_sample_bar_count']} hourly bars).",
        f"Buy-and-hold benchmark max drawdown (OOS): "
        f"{_fmt(payload['baseline_max_drawdown_bps_oos'])} bps.",
        "",
        "## Configuration",
        "",
        "```text",
        json.dumps(payload["config"], indent=2, sort_keys=True),
        "```",
        "",
        "## Result",
        "",
        "| Period | Legs resolved | Win rate | Net PnL (bps) | Net PF | Max DD (bps) | Gate |",
        "|---|---:|---:|---:|---:|---:|---|",
        _summary_row("Out-of-sample (decisive)", payload["oos_summary"]),
        _summary_row("In-sample (context only)", payload["in_sample_summary"]),
        _summary_row("Full sample (context only)", payload["full_sample_summary"]),
        "",
    ]
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
