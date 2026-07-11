"""Tests for src/research/paper_forward.py (ADR-0027 forward OOS track).

The central test is the OOS-contamination guard: any bar at or before the
development cutoff must fail closed, since it would invalidate the
out-of-sample claim.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.research.funding_carry import FundingCarryConfig
from src.research.paper_forward import (
    DEV_CUTOFF_MS,
    PaperForwardError,
    assemble_oos_bars,
    summarize_forward_track,
)

HOUR_MS = 3_600_000
STEP_MS = 8 * HOUR_MS


def _oos_bars(n_rebalances: int) -> pd.DataFrame:
    # Post-cutoff bars, 2 symbols, K=1-friendly; AAA low funding, BBB high.
    rows = []
    for i in range(n_rebalances + 1):  # +1 so the last rebalance has a forward
        t = DEV_CUTOFF_MS + i * STEP_MS
        rows.append((t, "AAA", 0.01 * (i % 5), 1000.0, -0.001))
        rows.append((t, "BBB", 0.02 * (i % 3), 1000.0, 0.001))
    return pd.DataFrame(
        rows, columns=["open_time", "symbol", "log_price", "quote_volume", "funding_rate_asof"]
    )


def test_summarize_forward_track_reports_oos_progress() -> None:
    bars = _oos_bars(12)
    summary = summarize_forward_track(bars, FundingCarryConfig(k=1), trigger_rebalances=500)

    assert summary.oos_start_ms >= DEV_CUTOFF_MS
    assert summary.resolved_rebalances > 0
    assert not summary.meets_trigger  # ~12 rebalances is far below 500
    assert summary.rebalances_remaining_to_trigger == 500 - summary.resolved_rebalances


def test_fails_closed_on_a_bar_at_or_before_the_dev_cutoff() -> None:
    bars = _oos_bars(12)
    # Inject one contaminating in-sample bar (one hour before the cutoff).
    leak = pd.DataFrame(
        [(DEV_CUTOFF_MS - HOUR_MS, "AAA", 0.0, 1000.0, -0.001)],
        columns=["open_time", "symbol", "log_price", "quote_volume", "funding_rate_asof"],
    )
    contaminated = pd.concat([bars, leak], ignore_index=True)
    with pytest.raises(PaperForwardError, match="contaminate the OOS"):
        summarize_forward_track(contaminated, FundingCarryConfig(k=1))


def test_assemble_oos_bars_concats_and_guards() -> None:
    first = _oos_bars(6)
    second = _oos_bars(6).assign(open_time=lambda d: d["open_time"] + 100 * STEP_MS)
    combined = assemble_oos_bars([first, second])
    assert len(combined) == len(first) + len(second)
    assert combined["open_time"].is_monotonic_increasing

    leak = first.assign(open_time=lambda d: d["open_time"] - 200 * STEP_MS)
    with pytest.raises(PaperForwardError, match="contaminate the OOS"):
        assemble_oos_bars([first, leak])


def test_assemble_fails_closed_on_empty_and_missing_columns() -> None:
    with pytest.raises(PaperForwardError, match="no frames"):
        assemble_oos_bars([])
    with pytest.raises(PaperForwardError, match="missing required columns"):
        assemble_oos_bars([_oos_bars(3).drop(columns=["funding_rate_asof"])])


def test_summarize_fails_closed_on_invalid_trigger() -> None:
    with pytest.raises(PaperForwardError, match="trigger_rebalances"):
        summarize_forward_track(_oos_bars(6), FundingCarryConfig(k=1), trigger_rebalances=0)
