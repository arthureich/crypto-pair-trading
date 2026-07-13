"""Tests for src/research/tsm_ensemble.py (TASK-TSM-005 trend+carry ensemble)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.research.tsm_ensemble import (
    TsmEnsembleError,
    blend_diagnostic,
    weekly_pnl,
)

HOUR_MS = 3_600_000
DAY_MS = 24 * HOUR_MS


def test_weekly_pnl_buckets_by_calendar_week() -> None:
    # Three points in one week + one in the next.
    base = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp() * 1000)  # Monday
    times = [base, base + DAY_MS, base + 2 * DAY_MS, base + 8 * DAY_MS]
    pnl = [1.0, 2.0, 3.0, 10.0]
    wk = weekly_pnl(times, pnl)
    assert len(wk) == 2
    assert wk.iloc[0] == pytest.approx(6.0)  # 1+2+3
    assert wk.iloc[1] == pytest.approx(10.0)


def test_weekly_pnl_length_mismatch_and_empty() -> None:
    with pytest.raises(TsmEnsembleError, match="length mismatch"):
        weekly_pnl([1, 2], [1.0])
    assert weekly_pnl([], []).empty


def test_blend_diagnostic_uncorrelated_streams_beat_either_alone() -> None:
    # Two uncorrelated streams with IDENTICAL stats (carry = a permutation of
    # tsm) -> equal Sharpes, and the equal-risk blend has ~sqrt(2)x the Sharpe
    # of each component (textbook diversification of like-Sharpe uncorrelated
    # sources). A permutation guarantees equal mean/std, isolating the effect.
    rng = np.random.default_rng(0)
    weeks = pd.period_range("2024-01-01", periods=200, freq="W-MON").start_time
    a = rng.normal(0.3, 1.0, 200)
    b = rng.permutation(a)  # same mean/std as a, ~uncorrelated
    tsm = pd.Series(a, index=weeks)
    carry = pd.Series(b, index=weeks)
    s = blend_diagnostic(tsm, carry)
    assert s.n_weeks == 200  # noqa: PLR2004
    assert abs(s.correlation) < 0.2  # noqa: PLR2004
    assert s.tsm_sharpe == pytest.approx(s.carry_sharpe)  # identical stats
    assert s.blend_sharpe > s.tsm_sharpe
    # blend Sharpe ~ sqrt(2) x a component for uncorrelated equal-Sharpe streams
    assert s.blend_sharpe == pytest.approx(math.sqrt(2) * s.tsm_sharpe, rel=0.3)


def test_blend_diagnostic_only_overlapping_weeks_used() -> None:
    weeks = pd.period_range("2024-01-01", periods=10, freq="W-MON").start_time
    tsm = pd.Series(np.linspace(0.1, 1.0, 10), index=weeks)
    carry = pd.Series(np.linspace(0.2, 2.0, 6), index=weeks[:6])  # only 6 overlap
    s = blend_diagnostic(tsm, carry)
    assert s.n_weeks == 6  # noqa: PLR2004


def test_blend_diagnostic_fails_closed_on_too_few_overlap() -> None:
    weeks = pd.period_range("2024-01-01", periods=3, freq="W-MON").start_time
    tsm = pd.Series([0.1, 0.2, 0.3], index=weeks)
    carry = pd.Series([0.1], index=weeks[:1])
    with pytest.raises(TsmEnsembleError, match="overlapping"):
        blend_diagnostic(tsm, carry)


def test_blend_diagnostic_negatively_correlated_cuts_drawdown() -> None:
    # Perfectly anti-correlated equal streams -> blend is ~flat (low risk),
    # drawdown far below the standalone TSM's.
    weeks = pd.period_range("2024-01-01", periods=50, freq="W-MON").start_time
    swing = np.tile([1.0, -1.0], 25)
    tsm = pd.Series(0.05 + swing, index=weeks)
    carry = pd.Series(0.05 - swing, index=weeks)
    s = blend_diagnostic(tsm, carry)
    assert s.correlation < -0.9  # noqa: PLR2004
    assert s.blend_max_drawdown < s.tsm_max_drawdown
