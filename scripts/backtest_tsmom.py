#!/usr/bin/env python3
"""Run the pre-registered TSMOM Donchian-breakout backtest (TASK-TSMOM-001).

Single, pre-registered configuration (24h Donchian window, 14h ATR, 3x ATR
trailing stop, 12.0bps round-trip cost, gate: net PF >= 1.20 AND win rate
>= 30%) on the existing 20-symbol Sprint 7 dataset. No new data, no
parameter sweep -- see docs/pre_registers/TASK-TSMOM-001.md.
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

from src.research.tsmom_breakout import (  # noqa: E402
    TradeStatus,
    TSMOMConfig,
    run_tsmom_backtest,
    summarize_tsmom_backtest,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsmom_backtest_results.json"
OUTPUT_CSV = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsmom_trades.csv"
REPORT_MD = PROJECT_ROOT / "reports/tsmom_backtest_final.md"
EXPECTED_SYMBOL_COUNT = 20


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "high", "low", "close"])
    symbol_count = bars["symbol"].nunique()
    if symbol_count != EXPECTED_SYMBOL_COUNT:
        raise ValueError(
            f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}, got {symbol_count}"
        )

    config = TSMOMConfig()  # pre-registered defaults, no sweep
    trades = run_tsmom_backtest(bars, config)
    summary = summarize_tsmom_backtest(trades, config)

    per_symbol_rows = _per_symbol_breakdown(trades)
    gate_decision = "PASSA" if summary.gate_pass else "NAO_PASSA"

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "config": asdict(config),
        "summary": asdict(summary),
        "gate_decision": gate_decision,
        "per_symbol": per_symbol_rows,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_trades_csv(trades)
    _write_report(config, summary, per_symbol_rows, gate_decision)

    console_payload = {"summary": asdict(summary), "gate_decision": gate_decision}
    print(json.dumps(_json_ready(console_payload), indent=2))
    print(f"GATE: {gate_decision}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {OUTPUT_CSV}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _per_symbol_breakdown(trades: tuple[Any, ...]) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[Any]] = {}
    for trade in trades:
        by_symbol.setdefault(trade.symbol, []).append(trade)

    rows = []
    for symbol in sorted(by_symbol):
        symbol_trades = by_symbol[symbol]
        resolved = [t for t in symbol_trades if t.status is TradeStatus.RESOLVED]
        open_at_end = sum(1 for t in symbol_trades if t.status is TradeStatus.OPEN_AT_END)
        wins = sum(1 for t in resolved if t.net_return is not None and t.net_return > 0.0)
        net_bps = sum((t.weight * t.net_return * 10_000.0) for t in resolved)
        rows.append(
            {
                "symbol": symbol,
                "trade_count": len(symbol_trades),
                "resolved_count": len(resolved),
                "open_at_end_count": open_at_end,
                "win_count": wins,
                "win_rate": (wins / len(resolved)) if resolved else None,
                "net_pnl_bps": net_bps,
            }
        )
    return rows


def _write_trades_csv(trades: tuple[Any, ...]) -> None:
    rows = [
        {
            "symbol": t.symbol,
            "side": t.side.value,
            "status": t.status.value,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "entry_atr": t.entry_atr,
            "gross_return": t.gross_return,
            "net_return": t.net_return,
            "weight": t.weight,
        }
        for t in trades
    ]
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUTPUT_CSV, index=False)


def _write_report(
    config: TSMOMConfig,
    summary: Any,
    per_symbol_rows: list[dict[str, Any]],
    gate_decision: str,
) -> None:
    lines = [
        "# TSMOM Donchian Breakout Backtest (TASK-TSMOM-001) - Final Result",
        "",
        "Status: real result for the single pre-registered configuration in "
        "`docs/pre_registers/TASK-TSMOM-001.md`. No parameter sweep.",
        "",
        f"**GATE: {gate_decision}**",
        "",
        "## Configuration",
        "",
        "```text",
        json.dumps(_json_ready(asdict(config)), indent=2),
        "```",
        "",
        "## Aggregate result",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total trades | {summary.trade_count} |",
        f"| Resolved trades | {summary.resolved_count} |",
        f"| Open at end (excluded) | {summary.open_at_end_count} |",
        f"| Win rate | {_fmt_pct(summary.win_rate)} |",
        f"| Gross PnL (bps) | {_fmt(summary.gross_pnl_bps)} |",
        f"| Cost (bps) | {_fmt(summary.cost_bps)} |",
        f"| Net PnL (bps) | {_fmt(summary.net_pnl_bps)} |",
        f"| Net profit factor | {_fmt(summary.profit_factor)} |",
        f"| Max drawdown (bps) | {_fmt(summary.max_drawdown_bps)} |",
        f"| Gate (PF>=1.20 and win_rate>=30%) | {gate_decision} |",
        "",
        "## Per-symbol breakdown",
        "",
        "| Symbol | Trades | Resolved | Open at end | Wins | Win rate | Net PnL (bps) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in per_symbol_rows:
        lines.append(
            f"| {row['symbol']} | {row['trade_count']} | {row['resolved_count']} | "
            f"{row['open_at_end_count']} | {row['win_count']} | "
            f"{_fmt_pct(row['win_rate'])} | {_fmt(row['net_pnl_bps'])} |"
        )
    lines.append("")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _fmt(value: float) -> str:
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
