"""Forward paper-validation track for the funding-carry K=5 signal.

Per ADR-0027 ("Funding Iteration 2"): rather than wait idly for a large new
historical window, run the FIXED, already-pre-registered incremental K=5
policy on data that accrues AFTER the development cutoff (2026-05-31) and
record its out-of-sample performance as a growing track. Because the signal
and all its parameters were frozen before this data existed, every post-
cutoff bar is genuine OOS -- it could not have influenced the hypothesis.

This module computes the track; it does not change the signal. The hard
invariant is the OOS guard: if ANY bar at or before the dev cutoff leaks in,
it fails closed, because that would contaminate the out-of-sample claim.

The track is MONITORING, not a verdict: a promotion decision follows the
pre-registered gate only once enough OOS rebalances have accrued
(``trigger_rebalances``, default 500). A single short window is itself
noisy; the value is in the accumulating record.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.research.funding_carry import (
    FundingCarryConfig,
    run_incremental_funding_carry_backtest,
    summarize_funding_carry_backtest,
)

# OOS begins at 2026-06-01 00:00 UTC -- development data runs through 2026-05-31.
DEV_CUTOFF_MS = int(pd.Timestamp("2026-06-01", tz="UTC").timestamp() * 1000)
DEFAULT_TRIGGER_REBALANCES = 500
_REQUIRED_COLUMNS = ("symbol", "open_time", "funding_rate_asof", "log_price")


class PaperForwardError(ValueError):
    """Raised when forward-track inputs are invalid or would contaminate OOS."""


@dataclass(frozen=True, slots=True)
class ForwardTrackSummary:
    oos_start_ms: int
    oos_end_ms: int
    resolved_rebalances: int
    trigger_rebalances: int
    rebalances_remaining_to_trigger: int
    net_pnl_bps: float
    profit_factor: float
    hit_rate: float
    meets_trigger: bool


def assemble_oos_bars(
    frames: list[pd.DataFrame],
    *,
    dev_cutoff_ms: int = DEV_CUTOFF_MS,
) -> pd.DataFrame:
    """Concatenate accruing monthly OOS frames; fail closed on any dev-window leak."""

    if not frames:
        raise PaperForwardError("no frames to assemble")
    combined = pd.concat(frames, ignore_index=True)
    _require_all_oos(combined, dev_cutoff_ms)
    combined = combined.drop_duplicates(subset=["symbol", "open_time"]).sort_values(
        ["open_time", "symbol"], kind="mergesort"
    )
    return combined.reset_index(drop=True)


def summarize_forward_track(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
    *,
    dev_cutoff_ms: int = DEV_CUTOFF_MS,
    trigger_rebalances: int = DEFAULT_TRIGGER_REBALANCES,
) -> ForwardTrackSummary:
    """Run the FIXED K=5 policy on post-cutoff bars and summarize the OOS track."""

    if trigger_rebalances < 1:
        raise PaperForwardError("trigger_rebalances must be >= 1")
    _require_all_oos(bars, dev_cutoff_ms)

    summary = summarize_funding_carry_backtest(
        run_incremental_funding_carry_backtest(bars, config), config
    )
    resolved = summary.resolved_count
    open_times = pd.to_numeric(bars["open_time"], errors="raise")
    return ForwardTrackSummary(
        oos_start_ms=int(open_times.min()),
        oos_end_ms=int(open_times.max()),
        resolved_rebalances=resolved,
        trigger_rebalances=trigger_rebalances,
        rebalances_remaining_to_trigger=max(0, trigger_rebalances - resolved),
        net_pnl_bps=summary.net_pnl_bps,
        profit_factor=summary.profit_factor,
        hit_rate=summary.hit_rate,
        meets_trigger=resolved >= trigger_rebalances,
    )


def _require_all_oos(bars: pd.DataFrame, dev_cutoff_ms: int) -> None:
    missing = [column for column in _REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise PaperForwardError(f"missing required columns: {missing}")
    open_times = pd.to_numeric(bars["open_time"], errors="raise")
    if bool((open_times < dev_cutoff_ms).any()):
        raise PaperForwardError(
            "forward track received bars at or before the dev cutoff "
            f"({dev_cutoff_ms}); this would contaminate the OOS claim"
        )
