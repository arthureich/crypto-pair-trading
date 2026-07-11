#!/usr/bin/env python3
"""TASK-FC-II-008: vol-targeted TSM with perp funding P&L included.

Per docs/pre_registers/TASK-FC-II-008.md (ADR-0027). Adds funding P&L over each
5d hold to the LOCKED FC-II-005 signal and reports funding-off vs funding-on
dev metrics plus the funding-on cost breakeven. In-sample, descriptive, no verdict.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, replace
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
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_tsm_funding.json"
REPORT_MD = PROJECT_ROOT / "reports/fc_tsm_funding.md"
REALISTIC_BAND = (10.0, 15.0)
_USECOLS = ["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"]


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=_USECOLS)
    off_cfg = TsmTrendConfig()
    on_cfg = replace(off_cfg, include_funding=True)

    off = summarize_tsm_trend(run_tsm_trend_backtest(bars, off_cfg), off_cfg)
    on = summarize_tsm_trend(run_tsm_trend_backtest(bars, on_cfg), on_cfg)

    on_zero = summarize_tsm_trend(
        run_tsm_trend_backtest(bars, replace(on_cfg, cost_bps_per_leg=0.0)),
        replace(on_cfg, cost_bps_per_leg=0.0),
    )
    total_turnover = on_zero.mean_turnover * on_zero.n_rebalances
    breakeven_bps = (
        on_zero.tsm_net_pnl * 10_000.0 / total_turnover if total_turnover > 0 else float("inf")
    )

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-FC-II-008 TSM with funding P&L",
        "phase": "DEVELOPMENT descriptive; NO verdict",
        "funding_off": asdict(off),
        "funding_on": asdict(on),
        "funding_on_net_pnl_breakeven_cost_bps": breakeven_bps,
        "realistic_band_bps": list(REALISTIC_BAND),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    print(
        f"funding OFF: Sharpe {off.tsm_sharpe:.3f} net {off.tsm_net_pnl:.4f} | "
        f"funding ON: Sharpe {on.tsm_sharpe:.3f} net {on.tsm_net_pnl:.4f} "
        f"(baseline {on.baseline_sharpe:.3f}); ON breakeven {breakeven_bps:.1f} bps/leg",
        file=sys.stderr,
    )
    print("NO VERDICT -- development (ADR-0027).", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(payload: dict) -> None:
    off = payload["funding_off"]
    on = payload["funding_on"]
    lo, hi = payload["realistic_band_bps"]
    be = payload["funding_on_net_pnl_breakeven_cost_bps"]
    survives = on["tsm_sharpe"] > on["baseline_sharpe"] and on["tsm_net_pnl"] > 0 and be >= hi
    lines = [
        "# TASK-FC-II-008 -- Vol-Targeted TSM with Perp Funding P&L",
        "",
        "Per `docs/pre_registers/TASK-FC-II-008.md` (ADR-0027). Adds funding P&L "
        "(long pays when funding>0, short receives) over each 5d hold to the "
        "LOCKED FC-II-005 signal. In-sample, descriptive, no verdict. Closes the "
        "gap flagged in FC-II-005/007 (a perp book held 5d incurs funding).",
        "",
        "## Funding off vs on (6 bps/leg cost)",
        "",
        "| Metric | Funding OFF | Funding ON |",
        "|---|---:|---:|",
        f"| Sharpe | {off['tsm_sharpe']:.3f} | {on['tsm_sharpe']:.3f} |",
        f"| Net PnL | {off['tsm_net_pnl']:.4f} | {on['tsm_net_pnl']:.4f} |",
        f"| Max drawdown | {off['tsm_max_drawdown']:.4f} | {on['tsm_max_drawdown']:.4f} |",
        f"| Baseline Sharpe | {off['baseline_sharpe']:.3f} | {on['baseline_sharpe']:.3f} |",
        "",
        f"Funding-on net-PnL breakeven cost: **{be:.1f} bps/leg** "
        f"(realistic band {lo:.0f}-{hi:.0f}).",
        "",
        "## Reading",
        "",
        (
            f"SURVIVES funding: with funding P&L included, Sharpe {on['tsm_sharpe']:.3f} still "
            f"beats baseline {on['baseline_sharpe']:.3f} with positive net PnL, and the cost "
            f"breakeven stays above the realistic band. The last cheap in-sample gap is closed "
            f"favorably -> the lead now merits an OOS pursuit."
            if survives
            else f"WEAKENS/DIES with funding: Sharpe {on['tsm_sharpe']:.3f} vs baseline "
            f"{on['baseline_sharpe']:.3f}, breakeven {be:.1f} bps. Funding materially erodes the "
            f"edge -> the perp-carry cost of holding the book is a real drag; reassess before OOS."
        ),
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
