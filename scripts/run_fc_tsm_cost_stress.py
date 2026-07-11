#!/usr/bin/env python3
"""TASK-FC-II-007: cost sensitivity (stress) of the vol-targeted TSM (FC-II-005).

Per docs/pre_registers/TASK-FC-II-007.md (ADR-0027). Sensitivity, NOT tuning:
sweeps cost_bps_per_leg over a fixed grid with the LOCKED FC-II-005 signal
params, and reports the full degradation curve plus the net-PnL breakeven cost.
In-sample, descriptive, no verdict.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
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
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_tsm_cost_stress.json"
REPORT_MD = PROJECT_ROOT / "reports/fc_tsm_cost_stress.md"
COST_GRID_BPS = (0.0, 3.0, 6.0, 10.0, 15.0, 20.0, 30.0, 50.0)
REALISTIC_BAND = (10.0, 15.0)


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    base_config = TsmTrendConfig()

    # gross (zero-cost) run gives the pieces for the analytic breakeven.
    zero = summarize_tsm_trend(
        run_tsm_trend_backtest(bars, replace(base_config, cost_bps_per_leg=0.0)),
        replace(base_config, cost_bps_per_leg=0.0),
    )
    total_turnover = zero.mean_turnover * zero.n_rebalances
    breakeven_bps = (
        zero.tsm_net_pnl * 10_000.0 / total_turnover if total_turnover > 0 else float("inf")
    )

    curve = []
    for cost in COST_GRID_BPS:
        config = replace(base_config, cost_bps_per_leg=cost)
        s = summarize_tsm_trend(run_tsm_trend_backtest(bars, config), config)
        curve.append(
            {
                "cost_bps": cost,
                "sharpe": s.tsm_sharpe,
                "net_pnl": s.tsm_net_pnl,
                "beats_baseline": s.tsm_sharpe > s.baseline_sharpe and s.tsm_net_pnl > 0.0,
            }
        )

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-FC-II-007 TSM cost stress",
        "phase": "DEVELOPMENT sensitivity; NO verdict",
        "baseline_sharpe": zero.baseline_sharpe,
        "baseline_net_pnl": zero.baseline_net_pnl,
        "mean_turnover_per_rebalance": zero.mean_turnover,
        "net_pnl_breakeven_cost_bps": breakeven_bps,
        "realistic_band_bps": list(REALISTIC_BAND),
        "curve": curve,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    print(
        f"net-PnL breakeven cost = {breakeven_bps:.1f} bps/leg; "
        f"mean turnover/rebalance = {zero.mean_turnover:.3f}",
        file=sys.stderr,
    )
    for row in curve:
        print(
            f"  {row['cost_bps']:>4.0f} bps: Sharpe={row['sharpe']:+.3f} "
            f"net={row['net_pnl']:+.4f} beats_baseline={row['beats_baseline']}",
            file=sys.stderr,
        )
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(payload: dict) -> None:
    lo, hi = payload["realistic_band_bps"]
    be = payload["net_pnl_breakeven_cost_bps"]
    lines = [
        "# TASK-FC-II-007 -- Vol-Targeted TSM Cost Stress",
        "",
        "Per `docs/pre_registers/TASK-FC-II-007.md` (ADR-0027). Sensitivity, NOT "
        "tuning: the LOCKED FC-II-005 signal with cost_bps_per_leg swept over a "
        "fixed grid. In-sample, descriptive, no verdict.",
        "",
        f"Baseline (buy-hold) Sharpe {payload['baseline_sharpe']:.3f}. Mean turnover "
        f"per rebalance {payload['mean_turnover_per_rebalance']:.3f}. **Net-PnL "
        f"breakeven cost = {be:.1f} bps/leg.** Realistic band for alt-perp L/S: "
        f"{lo:.0f}-{hi:.0f} bps/leg.",
        "",
        "## Degradation curve",
        "",
        "| Cost (bps/leg) | Sharpe | Net PnL | Beats buy-hold |",
        "|---:|---:|---:|---|",
    ]
    for row in payload["curve"]:
        lines.append(
            f"| {row['cost_bps']:.0f} | {row['sharpe']:+.3f} | {row['net_pnl']:+.4f} | "
            f"{row['beats_baseline']} |"
        )
    survives_15 = any(r["cost_bps"] == hi and r["beats_baseline"] for r in payload["curve"])
    lines.extend(["", "## Reading", "", _verdict(be, survives_15, lo, hi), ""])
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _verdict(breakeven: float, survives_15: bool, lo: float, hi: float) -> str:
    if survives_15:
        return (
            f"SURVIVES: beats buy-hold with positive net PnL at {hi:.0f} bps/leg, and the "
            f"net-PnL breakeven is {breakeven:.1f} bps/leg -- comfortably above realistic "
            f"cost. The lead survives the most likely killer -> merits OOS pursuit."
        )
    if breakeven >= lo:
        return (
            f"MARGINAL: net-PnL breakeven {breakeven:.1f} bps/leg sits inside/near the "
            f"realistic {lo:.0f}-{hi:.0f} bps band. Tradeability is fragile to cost; OOS only "
            f"warranted if execution cost can be held near the low end."
        )
    return (
        f"DIES ON COST: net-PnL breakeven {breakeven:.1f} bps/leg is below realistic cost "
        f"({lo:.0f}-{hi:.0f}). The in-sample Sharpe does not survive turnover cost -> not "
        f"tradeable as-is; do not spend OOS effort. Same pattern as the microstructure hit."
    )


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
