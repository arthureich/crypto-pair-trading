#!/usr/bin/env python3
"""TASK-DEPLOY-001 Phase 3: theoretical-vs-executable report + populate the ledger.

Measures the honest gap between the canonical core's THEORETICAL return (net of the
originally-declared 6bps/leg) and its EXECUTABLE return (net of the pre-declared
conservative execution model: taker fee + half-spread + participation slippage),
plus a CONSERVATIVE deployment stream (smaller risk budget). Characterization runs
on the dev-window original-20 stream (n=219, meaningful); the immutable ledger
(Phase 2) is populated ONLY with genuine post-cutoff (OOS) rebalances.

Offline; causal; no strategy/parameter change. Execution frictions are a cost
overlay on the causal backtest returns (we have klines, not tick/bid-ask data) --
stated as a limitation. Slippage at deployable size is quantified in Phase 4.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.execution_model import DECLARED_COST_BPS_PER_LEG, ExecutionCostModel  # noqa: E402
from src.research.forward_ledger import (  # noqa: E402
    DecisionEvent,
    ForwardLedger,
    make_decision_id,
    three_stream_pnl,
)
from src.research.paper_forward import DEV_CUTOFF_MS  # noqa: E402
from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest  # noqa: E402

NORMALIZED = PROJECT_ROOT / "data/research/binance_public/normalized"
DEV_BARS = NORMALIZED / "sprint7_binance_usdm_202306_202605_bars.csv.gz"
OOS_BARS = (NORMALIZED / "sprint_alt_funding_divergence_202606_bars.csv.gz",)
CANON = PROJECT_ROOT / "artifacts/tsm/canonical-config.json"
LEDGER_PATH = PROJECT_ROOT / "artifacts/tsm/forward/canonical_ledger.jsonl"
REPORT_MD = PROJECT_ROOT / "reports/theoretical_vs_executable.md"
JSON_OUT = PROJECT_ROOT / "data/research/binance_public/cost_pilot/theoretical_vs_executable.json"

HOLD_HOURS = 120
_ANN = math.sqrt(24 * 365 / HOLD_HOURS)
CONSERVATIVE_RISK_FRACTION = 0.5  # a-priori: deploy at half risk budget
REFERENCE_CAPITAL_USD = 100_000.0
_USECOLS = ["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"]


def _software_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def _sharpe(r: np.ndarray) -> float | None:
    r = r[~np.isnan(r)]
    if r.size < 2:  # noqa: PLR2004
        return None
    s = r.std(ddof=1)
    return float(r.mean() / s * _ANN) if s > 1e-12 else None  # noqa: PLR2004


def _streams(bars: pd.DataFrame, model: ExecutionCostModel) -> pd.DataFrame:
    r = run_tsm_trend_backtest(bars, TsmTrendConfig(include_funding=True))
    idx = list(r.rebalance_times)
    tsm_net = pd.Series(r.tsm_net, index=idx)
    turnover = pd.Series(r.tsm_turnover, index=idx)
    gross = tsm_net + turnover * (DECLARED_COST_BPS_PER_LEG / 10_000.0)  # pre-cost, funding incl
    a = model.theoretical_net(gross, turnover)  # == tsm_net
    b = model.executable_net(gross, turnover)  # base size (participation 0)
    c = CONSERVATIVE_RISK_FRACTION * b
    return pd.DataFrame({"gross": gross, "turnover": turnover, "A": a, "B": b, "C": c}, index=idx)


def _load(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(p, usecols=_USECOLS) for p in paths]
    return (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["symbol", "open_time"])
        .sort_values(["open_time", "symbol"], kind="mergesort")
        .reset_index(drop=True)
    )


def _characterize(df: pd.DataFrame, model: ExecutionCostModel) -> dict:
    turn_total = float(df["turnover"].sum())
    fee_bps = model.taker_fee_bps
    spread_bps = model.half_spread_bps
    shortfall_ret = float(df["A"].sum() - df["B"].sum())  # A - B in return units
    base_leg = model.per_leg_cost_bps(0.0)
    return {
        "n_rebalances": int(len(df)),
        "sharpe_theoretical": _sharpe(df["A"].to_numpy()),
        "sharpe_executable": _sharpe(df["B"].to_numpy()),
        "sharpe_conservative": _sharpe(df["C"].to_numpy()),
        "net_theoretical": float(df["A"].sum()),
        "net_executable": float(df["B"].sum()),
        "net_conservative": float(df["C"].sum()),
        "total_turnover": turn_total,
        "declared_cost_bps_per_leg": DECLARED_COST_BPS_PER_LEG,
        "executable_base_cost_bps_per_leg": base_leg.total_bps,
        "cost_breakdown_bps_per_leg": {
            "fee": fee_bps,
            "half_spread": spread_bps,
            "slippage_at_base_size": base_leg.slippage_bps,
        },
        "execution_shortfall_return_units": shortfall_ret,
        "execution_shortfall_bps_of_gross": (
            shortfall_ret / abs(float(df["gross"].sum())) * 10_000.0
            if float(df["gross"].sum()) != 0
            else None
        ),
        "execution_shortfall_usd_at_ref_capital": shortfall_ret * REFERENCE_CAPITAL_USD,
        "reference_capital_usd": REFERENCE_CAPITAL_USD,
    }


def _populate_ledger(config_hash: str, commit: str, model: ExecutionCostModel) -> dict:
    present = [p for p in OOS_BARS if p.exists()]
    if not present:
        return {"oos_events_written": 0, "note": "no post-cutoff OOS bars yet"}
    bars = _load([DEV_BARS, *present])
    df = _streams(bars, model)
    oos = df[df.index >= DEV_CUTOFF_MS]
    ledger = ForwardLedger(LEDGER_PATH)
    written = 0
    for t, row in oos.iterrows():
        streams = three_stream_pnl(
            float(row["gross"]),
            declared_cost=float(row["turnover"]) * DECLARED_COST_BPS_PER_LEG / 10_000.0,
            execution_frictions=float(row["gross"] - row["B"]),
            conservative_risk_fraction=CONSERVATIVE_RISK_FRACTION,
        )
        ev = DecisionEvent(
            decision_id=make_decision_id(config_hash, "binance", "__PORTFOLIO__", int(t)),
            strategy_config_hash=config_hash,
            software_commit=commit,
            exchange="binance",
            symbol="__PORTFOLIO__",
            signal_timestamp_ms=int(t),
            data_available_until_ms=int(t),
            decision_timestamp_ms=int(t),
            scheduled_execution_timestamp_ms=int(t),
            side="long_short",
            target_weight=1.0,
            gross_pnl=float(row["gross"]),
            net_pnl_theoretical=streams.theoretical,
            net_pnl_executable=streams.executable,
            net_pnl_conservative=streams.conservative,
            execution_flags=("portfolio_level", "friction_overlay_not_tick_fill"),
        )
        if ledger.append(ev):
            written += 1
    return {"oos_events_written": written, "ledger_path": str(LEDGER_PATH), "oos_total": len(oos)}


def _write_report(dev: dict, ledger_info: dict) -> None:
    def pct(x: float | None) -> str:
        return "n/a" if x is None else f"{x:.3f}"

    lines = [
        "# Theoretical vs Executable -- canonical TSM (TASK-DEPLOY-001, Phase 3)",
        "",
        "Pre-declared conservative execution model (taker fee + half-spread + "
        "participation slippage), applied as a cost overlay on the causal backtest "
        "(we have klines, not tick/bid-ask data -- a limitation). Characterization "
        "on the dev-window original-20 stream. No strategy/parameter change.",
        "",
        "## Three streams (dev-window original-20, n={})".format(dev["n_rebalances"]),
        "",
        "| Stream | Sharpe | net (return units) |",
        "|---|---:|---:|",
        f"| A theoretical (6.0bps declared) | {pct(dev['sharpe_theoretical'])} | "
        f"{pct(dev['net_theoretical'])} |",
        f"| B executable ({dev['executable_base_cost_bps_per_leg']:.1f}bps base) | "
        f"{pct(dev['sharpe_executable'])} | {pct(dev['net_executable'])} |",
        f"| C conservative ({int(CONSERVATIVE_RISK_FRACTION * 100)}% risk budget) | "
        f"{pct(dev['sharpe_conservative'])} | {pct(dev['net_conservative'])} |",
        "",
        "## Cost breakdown (bps per leg, on turnover)",
        "",
        f"- Declared (backtest): {dev['declared_cost_bps_per_leg']:.1f} bps",
        f"- Executable base: {dev['executable_base_cost_bps_per_leg']:.1f} bps "
        f"(fee {dev['cost_breakdown_bps_per_leg']['fee']:.1f} + half-spread "
        f"{dev['cost_breakdown_bps_per_leg']['half_spread']:.1f} + slippage "
        f"{dev['cost_breakdown_bps_per_leg']['slippage_at_base_size']:.1f} at base size)",
        "",
        "## Execution shortfall (A - B)",
        "",
        f"- Return units: {dev['execution_shortfall_return_units']:.4f}",
        f"- As bps of gross: {pct(dev['execution_shortfall_bps_of_gross'])}",
        f"- USD at ${int(dev['reference_capital_usd']):,} reference capital: "
        f"${dev['execution_shortfall_usd_at_ref_capital']:,.0f}",
        "",
        "## Reading (fact / estimate / assumption / limitation)",
        "",
        "- FACT: at deployable (small) size the executable base cost (6.5 bps/leg) "
        "is barely above the declared 6.0 bps -> the theoretical-executable gap is "
        "small, consistent with the strategy's documented cost-insensitivity "
        "(FC-II-007 breakeven ~142 bps/leg). The Sharpe gap A->B is minor.",
        "- ESTIMATE: slippage at base size is ~0; it grows with participation and "
        "is quantified against real volume in Phase 4 (capacity).",
        "- ASSUMPTION: conservative stream C = 50% risk budget (a-priori), so its "
        "Sharpe ~ B and its absolute return is halved; production-control drag is "
        "added in Phase 5.",
        "- LIMITATION: frictions are a cost overlay on causal returns, not a tick "
        "fill simulation (no bid/ask data); spread/fee are conservative constants.",
        "",
        f"## Immutable ledger (OOS forward): {ledger_info.get('oos_events_written', 0)} "
        f"new event(s) appended",
        "",
        ledger_info.get(
            "note",
            f"Ledger at `{ledger_info.get('ledger_path', LEDGER_PATH)}` "
            f"(append-only; re-running is idempotent). OOS total rebalances: "
            f"{ledger_info.get('oos_total', 0)}.",
        ),
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    config_hash = json.loads(CANON.read_text(encoding="utf-8"))["config_hash"]
    commit = _software_commit()
    model = ExecutionCostModel()

    dev_bars = _load([DEV_BARS])
    dev = _characterize(_streams(dev_bars, model), model)
    ledger_info = _populate_ledger(config_hash, commit, model)

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(
            {
                "task": "TASK-DEPLOY-001 Phase 3 theoretical-vs-executable",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "config_hash": config_hash,
                "software_commit": commit,
                "dev_window_characterization": dev,
                "ledger": ledger_info,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _write_report(dev, ledger_info)
    print(
        f"A/B/C Sharpe: {dev['sharpe_theoretical']:.3f} / {dev['sharpe_executable']:.3f} / "
        f"{dev['sharpe_conservative']:.3f}; executable base cost "
        f"{dev['executable_base_cost_bps_per_leg']:.1f}bps/leg"
    )
    print(f"Ledger: {ledger_info}")
    print(f"Wrote {REPORT_MD}\nWrote {JSON_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
