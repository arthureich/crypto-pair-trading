"""Edge-case tests for the canonical drawdown module (TASK-DEPLOY-001, Phase 1).

Covers every case named in the task spec: the canonical 1.00->0.20 = 80% check,
flat / monotone-up / drop-no-recovery / drop-with-recovery / recovery-on-last-bar
series, off-by-one duration, NaN returns, non-positive equity, and float-near-zero.
"""

from __future__ import annotations

import math

import numpy as np

from src.research.drawdown import compute_drawdown


def test_canonical_80_percent_drawdown():
    # equity 1.00 -> 0.20 : maxDD = 0.80 = 80% (the spec's explicit check)
    d = compute_drawdown([0.0, -0.8], compound=True)
    assert math.isclose(d.max_drawdown, 0.80, rel_tol=1e-9)
    assert math.isclose(d.max_drawdown_percent, 80.0, rel_tol=1e-9)
    assert math.isclose(d.peak_equity, 1.0, rel_tol=1e-9)
    assert math.isclose(d.trough_equity, 0.20, rel_tol=1e-9)
    assert d.unrecovered is True


def test_flat_series_no_drawdown():
    d = compute_drawdown([0.0, 0.0, 0.0], compound=True)
    assert d.max_drawdown == 0.0
    assert d.time_underwater_fraction == 0.0
    assert d.peak_index is None


def test_monotonic_up_no_drawdown():
    d = compute_drawdown([0.01, 0.02, 0.03, 0.01], compound=True)
    assert d.max_drawdown == 0.0
    assert d.time_underwater_fraction == 0.0
    assert d.unrecovered is False


def test_drop_without_recovery():
    # up to peak at idx1, then down and never back
    d = compute_drawdown([0.10, 0.10, -0.20, -0.05], compound=True)
    assert d.unrecovered is True
    assert d.recovery_index is None
    assert d.peak_index == 1
    assert d.trough_index == 3
    # duration = end(3) - peak(1) = 2 bars (peak -> end, unrecovered lower bound)
    assert d.duration_bars == 2


def test_drop_with_recovery_and_offbyone():
    # equity: 1.1, 1.21, 0.968(-0.2), 1.0648(+0.1), 1.22(+0.145) recovers above peak
    r = [0.10, 0.10, -0.20, 0.10, 0.145]
    d = compute_drawdown(r, compound=True)
    assert d.peak_index == 1
    assert d.trough_index == 2
    assert d.recovery_index == 4  # first bar regaining peak equity
    assert d.unrecovered is False
    # peak(1) -> recovery(4) inclusive span = 3 bars (off-by-one guard)
    assert d.duration_bars == 3


def test_recovery_on_last_bar():
    # peak at idx0 (1.0), dip, exactly back to >= peak on the final bar
    # returns: 0.0, -0.5 (0.5), +1.0 (1.0) -> recovers to peak on last bar
    d = compute_drawdown([0.0, -0.5, 1.0], compound=True)
    assert d.trough_index == 1
    assert d.recovery_index == 2
    assert d.unrecovered is False
    assert d.duration_bars == 2  # peak(0) -> recovery(2)


def test_nan_returns_treated_as_zero_and_flagged():
    d = compute_drawdown([0.10, np.nan, -0.20], compound=True)
    assert d.had_nan is True
    # NaN bar contributes 0 return; equity 1.1, 1.1, 0.88 -> maxDD = 1 - 0.88/1.1 = 0.20
    assert math.isclose(d.max_drawdown, 0.20, rel_tol=1e-9)


def test_non_positive_equity_flagged():
    # a return <= -1 wipes equity; compounded drawdown is total (>=100%)
    d = compute_drawdown([0.0, -1.0, 0.5], compound=True)
    assert d.equity_non_positive is True
    assert d.max_drawdown >= 1.0


def test_float_near_zero_returns_no_spurious_drawdown():
    d = compute_drawdown([1e-18, -1e-18, 1e-18], compound=True)
    assert d.max_drawdown < 1e-9


def test_empty_series():
    d = compute_drawdown([], compound=True)
    assert d.n == 0
    assert d.max_drawdown == 0.0


def test_additive_mode_reports_return_units_not_percent():
    # additive: cumsum equity 0.1, 0.3, 0.1 -> peak 0.3, trough 0.1, DD = 0.2 (return units)
    d = compute_drawdown([0.1, 0.2, -0.2], compound=False)
    assert d.mode == "additive"
    assert math.isclose(d.max_drawdown, 0.20, rel_tol=1e-9)
    assert d.max_drawdown_percent is None  # additive is NOT a percent


def test_timestamps_filled_when_times_given():
    times = [1_685_577_600_000, 1_685_664_000_000, 1_685_750_400_000]
    d = compute_drawdown([0.0, -0.5, 0.0], times=times, compound=True)
    assert d.peak_timestamp is not None
    assert d.trough_timestamp is not None
    assert "2023" in d.peak_timestamp


def test_compounded_vs_additive_differ_on_large_moves():
    r = [0.5, -0.4, 0.3, -0.4]
    comp = compute_drawdown(r, compound=True)
    add = compute_drawdown(r, compound=False)
    # the two framings must not coincide on large moves (documents the unit gap)
    assert not math.isclose(comp.max_drawdown, add.max_drawdown, rel_tol=1e-3)
