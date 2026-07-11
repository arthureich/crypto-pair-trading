#!/usr/bin/env python3
"""TASK-FC-II-005 development run: classic vol-targeted time-series momentum.

Per docs/pre_registers/TASK-FC-II-005.md (ADR-0027). Development-window
backtest; risk-adjusted metrics only, NO promotion verdict (gate, if
warranted, is on untouched OOS). Tests whether volatility-targeting rescues
the trend edge that Donchian TSMOM lost to drawdown.
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

from src.research.tsm_trend import (  # noqa: E402
    TsmTrendConfig,
    run_tsm_trend_backtest,
    summarize_tsm_trend,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_tsm_trend_results.json"
REPORT_MD = PROJECT_ROOT / "reports/fc_tsm_trend_dev.md"


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    config = TsmTrendConfig()  # locked defaults (28d / 7d / 5d / 6bps)
    summary = summarize_tsm_trend(run_tsm_trend_backtest(bars, config), config)

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-FC-II-005 classic vol-targeted TSM",
        "phase": "DEVELOPMENT: risk-adjusted metrics only; NO verdict",
        "config": asdict(config),
        "summary": asdict(summary),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload, summary)

    print(
        f"TSM L/S Sharpe={summary.tsm_sharpe:.3f} (long-only {summary.tsm_long_only_sharpe:.3f}) "
        f"vs baseline {summary.baseline_sharpe:.3f}; "
        f"TSM maxDD={summary.tsm_max_drawdown:.4f} vs base {summary.baseline_max_drawdown:.4f}; "
        f"net {summary.tsm_net_pnl:.4f} vs {summary.baseline_net_pnl:.4f} "
        f"({summary.n_rebalances} rebalances)",
        file=sys.stderr,
    )
    print("NO VERDICT -- development window (ADR-0027).", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _reading(clears_bar: bool) -> str:
    if clears_bar:
        return (
            "Both conditions hold -> a candidate for a separately pre-registered OOS test "
            "(with realistic cost); NOT a verdict here. Caveats: in-sample dev window; the "
            "short leg carries it (long-only is flat), so it may be flattered by the bear-heavy "
            "part of the sample -- regime-dependence must be checked in OOS."
        )
    return (
        "It does not clear the literature's own bar (better Sharpe AND lower drawdown) even in "
        "development -> closes the price family; vol-targeting does not rescue the trend edge in "
        "this universe/period. In-sample dev numbers, not a gate either way."
    )


def _write_report(payload: dict, summary: object) -> None:
    s = summary  # type: ignore[assignment]
    better_sharpe = s.tsm_sharpe > s.baseline_sharpe
    lower_dd = s.tsm_max_drawdown < s.baseline_max_drawdown
    lines = [
        "# TASK-FC-II-005 -- Classic Vol-Targeted TSM (development)",
        "",
        "Per `docs/pre_registers/TASK-FC-II-005.md` (ADR-0027). **Development "
        "window, NO verdict.** Position = sign of the 28d trailing return, sized "
        "inverse to 7d realized vol, unit gross, 5d rebalance, 6bps/leg. Distinct "
        "from the Donchian TSMOM. The literature claims vol-targeting rescues the "
        "trend edge; this tests that on our data.",
        "",
        "## Development metrics (vol-targeted TSM vs equal-weight buy-and-hold)",
        "",
        "| Metric | TSM long/short | TSM long-only | Baseline (buy-hold) |",
        "|---|---:|---:|---:|",
        f"| Sharpe (annualized) | {s.tsm_sharpe:.3f} | {s.tsm_long_only_sharpe:.3f} | "
        f"{s.baseline_sharpe:.3f} |",
        f"| Max drawdown | {s.tsm_max_drawdown:.4f} | -- | {s.baseline_max_drawdown:.4f} |",
        f"| Net PnL (log-ret units) | {s.tsm_net_pnl:.4f} | -- | {s.baseline_net_pnl:.4f} |",
        f"| Mean turnover / rebalance | {s.mean_turnover:.3f} | -- | -- |",
        f"| Rebalances | {s.n_rebalances} | | |",
        "",
        "## Reading",
        "",
        f"The literature's claim is risk-adjusted. Here TSM "
        f"{'beats' if better_sharpe else 'does NOT beat'} buy-and-hold on Sharpe and has "
        f"{'lower' if lower_dd else 'HIGHER (not lower)'} max drawdown.",
        "",
        _reading(better_sharpe and lower_dd),
        "",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
