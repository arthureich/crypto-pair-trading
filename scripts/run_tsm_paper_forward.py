#!/usr/bin/env python3
"""Vol-targeted TSM forward paper-validation track (ADR-0027, FC-II-005/008).

Runs the FIXED TSM (with funding P&L) and counts ONLY rebalances whose decision
time is after the 2026-05-31 dev cutoff as genuine OOS. Pre-cutoff bars are used
solely to form the causal 28d trailing signal (a lookback, not a test set), so
including them is not contamination -- the params are literature-fixed and were
never fit to any data. Monitoring, not a verdict: a real TSM OOS needs many 5d
rebalances (~1-2 years); the value is the accumulating record.
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

from src.research.paper_forward import DEV_CUTOFF_MS  # noqa: E402
from src.research.tsm_trend import (  # noqa: E402
    TsmTrendConfig,
    TsmTrendResult,
    run_tsm_trend_backtest,
    summarize_tsm_trend,
)

NORMALIZED = PROJECT_ROOT / "data/research/binance_public/normalized"
DEV_BARS = NORMALIZED / "sprint7_binance_usdm_202306_202605_bars.csv.gz"
# Post-cutoff monthly bar files (add more as they are downloaded).
OOS_BARS = (NORMALIZED / "sprint_alt_funding_divergence_202606_bars.csv.gz",)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_paper_forward.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_paper_forward.md"
TRIGGER_REBALANCES = 100  # ~1.4y at 5d rebalance for a meaningful OOS Sharpe
_USECOLS = ["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"]


def main() -> int:
    present_oos = [p for p in OOS_BARS if p.exists()]
    if not present_oos:
        print("No post-cutoff OOS bar files yet; nothing to record.", file=sys.stderr)
        return 0

    frames = [pd.read_csv(DEV_BARS, usecols=_USECOLS)]
    frames += [pd.read_csv(p, usecols=_USECOLS) for p in present_oos]
    bars = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["symbol", "open_time"])
        .sort_values(["open_time", "symbol"], kind="mergesort")
        .reset_index(drop=True)
    )

    config = TsmTrendConfig(include_funding=True)
    result = run_tsm_trend_backtest(bars, config)
    oos = _slice_from(result, DEV_CUTOFF_MS)

    n_oos = len(oos.rebalance_times)
    summary = summarize_tsm_trend(oos, config) if n_oos >= 2 else None  # noqa: PLR2004
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "vol-targeted TSM forward paper track (ADR-0027)",
        "phase": "MONITORING: genuine OOS accruing; verdict only at >= trigger rebalances",
        "oos_rebalances": n_oos,
        "trigger_rebalances": TRIGGER_REBALANCES,
        "rebalances_remaining_to_trigger": max(0, TRIGGER_REBALANCES - n_oos),
        "summary": asdict(summary) if summary is not None else None,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    if summary is not None:
        print(
            f"OOS TSM: Sharpe {summary.tsm_sharpe:.3f}, net {summary.tsm_net_pnl:.4f}, "
            f"{n_oos} rebalances ({payload['rebalances_remaining_to_trigger']} to trigger)",
            file=sys.stderr,
        )
    else:
        print(f"OOS TSM: only {n_oos} rebalance(s) -- too few to summarize.", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _slice_from(result: TsmTrendResult, cutoff_ms: int) -> TsmTrendResult:
    idx = [i for i, t in enumerate(result.rebalance_times) if t >= cutoff_ms]

    def take(seq: tuple) -> tuple:
        return tuple(seq[i] for i in idx)

    return TsmTrendResult(
        rebalance_times=take(result.rebalance_times),
        tsm_net=take(result.tsm_net),
        tsm_long_only_net=take(result.tsm_long_only_net),
        baseline=take(result.baseline),
        tsm_turnover=take(result.tsm_turnover),
        tsm_long_sleeve=take(result.tsm_long_sleeve),
        tsm_short_sleeve=take(result.tsm_short_sleeve),
    )


def _write_report(payload: dict) -> None:
    s = payload["summary"]
    lines = [
        "# Vol-Targeted TSM -- Forward Paper Track (genuine OOS)",
        "",
        "Per ADR-0027 (FC-II-005/008). The FIXED TSM (with funding P&L) run so that "
        "ONLY rebalances after the 2026-05-31 dev cutoff count as OOS; pre-cutoff "
        "bars form the causal 28d signal (a lookback, not a test set). **Monitoring, "
        "not a verdict** -- a meaningful TSM OOS needs ~100 5d-rebalances (~1-2y).",
        "",
        f"OOS rebalances so far: **{payload['oos_rebalances']}** "
        f"(trigger {payload['trigger_rebalances']}; "
        f"{payload['rebalances_remaining_to_trigger']} remaining).",
        "",
    ]
    if s is not None:
        lines += [
            "## OOS track so far (in-development scale -- NOT a verdict)",
            "",
            "| Metric | TSM (OOS) | Baseline |",
            "|---|---:|---:|",
            f"| Sharpe | {s['tsm_sharpe']:.3f} | {s['baseline_sharpe']:.3f} |",
            f"| Net PnL | {s['tsm_net_pnl']:.4f} | {s['baseline_net_pnl']:.4f} |",
            f"| Max drawdown | {s['tsm_max_drawdown']:.4f} | {s['baseline_max_drawdown']:.4f} |",
            "",
            "A handful of rebalances is pure noise. Do NOT read this as evidence; it is "
            "the seed of an accumulating track that only becomes informative near the "
            "trigger. Re-run as each new month is downloaded.",
        ]
    else:
        lines.append("Too few OOS rebalances to summarize yet. Re-run as new months accrue.")
    lines.append("")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str | int) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
