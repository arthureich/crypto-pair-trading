#!/usr/bin/env python3
"""TSM forward paper-validation track (ADR-0027 / ADR-0031, TASK-TSM-008).

Records the genuine OOS track of the TSM candidates: the PRIMARY is now the
combined ERC + volatility-targeting TSM (TASK-TSM-008, the lead OOS candidate),
with the base vol-targeted TSM kept as a reference line. Counts ONLY rebalances
whose decision time is after the 2026-05-31 dev cutoff as OOS; pre-cutoff bars
form the causal signal / vol-target history (a lookback, not a test set). The
params/overlays are fixed (validated in development) and were never fit here.
Monitoring, not a verdict: a meaningful OOS needs ~100 5d-rebalances (~1-2y).

Causality note: the vol-target overlay is applied to the FULL ERC return series
(so each OOS rebalance's scale uses only its trailing history) and only THEN
sliced to the post-cutoff window.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.paper_forward import DEV_CUTOFF_MS  # noqa: E402
from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest  # noqa: E402
from src.research.vol_target import apply_vol_target  # noqa: E402

NORMALIZED = PROJECT_ROOT / "data/research/binance_public/normalized"
DEV_BARS = NORMALIZED / "sprint7_binance_usdm_202306_202605_bars.csv.gz"
# Post-cutoff monthly bar files (add more as they are downloaded).
OOS_BARS = (NORMALIZED / "sprint_alt_funding_divergence_202606_bars.csv.gz",)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_paper_forward.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_paper_forward.md"
TRIGGER_REBALANCES = 100  # ~1.4y at 5d rebalance for a meaningful OOS Sharpe
HOLD_HOURS = 120
_ANN = math.sqrt(24 * 365 / HOLD_HOURS)
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

    base = run_tsm_trend_backtest(bars, TsmTrendConfig(include_funding=True))
    erc = run_tsm_trend_backtest(bars, TsmTrendConfig(include_funding=True, portfolio_erc=True))
    base_net = pd.Series(base.tsm_net, index=list(base.rebalance_times))
    combined_net = apply_vol_target(pd.Series(erc.tsm_net, index=list(erc.rebalance_times)))
    baseline = pd.Series(base.baseline, index=list(base.rebalance_times))

    combined_oos = _slice_from(combined_net, DEV_CUTOFF_MS)
    base_oos = _slice_from(base_net, DEV_CUTOFF_MS)
    baseline_oos = _slice_from(baseline, DEV_CUTOFF_MS)

    n_oos = len(combined_oos)
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TSM forward paper track -- PRIMARY: combined ERC+vol-target (TASK-TSM-008)",
        "phase": "MONITORING: genuine OOS accruing; verdict only at >= trigger rebalances",
        "oos_rebalances": n_oos,
        "trigger_rebalances": TRIGGER_REBALANCES,
        "rebalances_remaining_to_trigger": max(0, TRIGGER_REBALANCES - n_oos),
        "combined_primary": _metrics(combined_oos),
        "base_reference": _metrics(base_oos),
        "buy_hold_baseline": _metrics(baseline_oos),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    c = payload["combined_primary"]
    if c["sharpe"] is not None:
        print(
            f"OOS combined: Sharpe {c['sharpe']:.3f}, net {c['net']:.4f}, "
            f"{n_oos} rebalances ({payload['rebalances_remaining_to_trigger']} to trigger)",
            file=sys.stderr,
        )
    else:
        print(f"OOS combined: only {n_oos} rebalance(s) -- too few to summarize.", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _slice_from(series: pd.Series, cutoff_ms: int) -> pd.Series:
    return series[series.index >= cutoff_ms]


def _metrics(series: pd.Series) -> dict:
    r = np.asarray(series.dropna(), dtype=float)
    if len(r) < 2:  # noqa: PLR2004
        return {"n": int(len(r)), "sharpe": None, "max_dd": None, "net": None}
    std = r.std(ddof=1)
    sharpe = float(r.mean() / std * _ANN) if std > 0 else None
    equity = np.cumsum(r)
    max_dd = float(np.max(np.maximum.accumulate(equity) - equity))
    return {"n": int(len(r)), "sharpe": sharpe, "max_dd": max_dd, "net": float(r.sum())}


def _write_report(payload: dict) -> None:
    lines = [
        "# TSM Forward Paper Track (genuine OOS) -- PRIMARY: combined ERC + vol-targeting",
        "",
        "Per ADR-0027 / ADR-0031 (TASK-TSM-008). The lead OOS candidate is the combined "
        "ERC + volatility-targeting TSM; the base vol-targeted TSM is a reference line. "
        "ONLY post-2026-05-31 rebalances count as OOS; pre-cutoff bars form the causal "
        "signal + vol-target history (a lookback, not a test set). **Monitoring, not a "
        "verdict** -- a meaningful OOS needs ~100 5d-rebalances (~1-2y).",
        "",
        f"OOS rebalances so far: **{payload['oos_rebalances']}** "
        f"(trigger {payload['trigger_rebalances']}; "
        f"{payload['rebalances_remaining_to_trigger']} remaining).",
        "",
    ]
    c, b, bh = (
        payload["combined_primary"],
        payload["base_reference"],
        payload["buy_hold_baseline"],
    )
    if c["sharpe"] is not None:
        lines += [
            "## OOS track so far (in-development scale -- NOT a verdict)",
            "",
            "| Metric | Combined (primary) | Base TSM (ref) | Buy-hold |",
            "|---|---:|---:|---:|",
            f"| Sharpe | {_f(c['sharpe'])} | {_f(b['sharpe'])} | {_f(bh['sharpe'])} |",
            f"| Net PnL | {_f(c['net'])} | {_f(b['net'])} | {_f(bh['net'])} |",
            f"| Max drawdown | {_f(c['max_dd'])} | {_f(b['max_dd'])} | {_f(bh['max_dd'])} |",
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


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.4f}"


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
