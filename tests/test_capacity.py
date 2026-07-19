"""Tests for the capacity analysis helpers (TASK-DEPLOY-001, Phase 4)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.research.capacity import (
    capacity_net_returns,
    participation_matrix,
    slippage_bps_matrix,
    turnover_matrix,
)


def test_turnover_matrix_from_flat_then_deltas():
    w = [[0.5, -0.5], [0.5, -0.5], [0.0, 1.0]]
    t = turnover_matrix(w)
    # row0 enters from flat -> |w0|; row1 no change -> 0; row2 = |Δ|
    assert np.allclose(t[0], [0.5, 0.5])
    assert np.allclose(t[1], [0.0, 0.0])
    assert np.allclose(t[2], [0.5, 1.5])


def test_turnover_requires_2d():
    with pytest.raises(ValueError, match="2D"):
        turnover_matrix([0.1, 0.2, 0.3])


def test_participation_scales_with_capital_and_handles_zero_volume():
    turn = np.array([[0.5, 0.5]])
    dv = np.array([[1_000_000.0, 0.0]])  # second symbol has no volume data
    p_small = participation_matrix(turn, dv, capital=10_000.0)
    p_big = participation_matrix(turn, dv, capital=100_000.0)
    assert math.isclose(p_small[0, 0], 10_000.0 * 0.5 / 1_000_000.0)
    assert p_big[0, 0] == 10 * p_small[0, 0]  # linear in capital
    assert p_small[0, 1] == 0.0  # zero-volume -> participation 0 (no div blowup)


def test_slippage_clipped_at_max_participation():
    part = np.array([[0.5, 2.0]])  # second exceeds max
    slip = slippage_bps_matrix(part, slippage_bps_at_full=10.0, max_participation=1.0)
    assert math.isclose(slip[0, 0], 5.0)  # 10 * 0.5
    assert math.isclose(slip[0, 1], 10.0)  # clipped at 1.0 -> 10 bps


def test_capacity_net_subtracts_size_and_slippage_cost():
    gross = np.array([0.02])
    turn = np.array([[0.5, 0.5]])  # total turnover 1.0
    slip = np.array([[0.0, 0.0]])  # no slippage
    net = capacity_net_returns(gross, turn, slip, base_cost_bps=6.5)
    # cost = 1.0 * 6.5bps = 0.00065 -> net = 0.02 - 0.00065
    assert math.isclose(net[0], 0.02 - 0.00065, rel_tol=1e-9)


def test_capacity_net_monotonic_worse_with_more_slippage():
    gross = np.array([0.02, 0.01])
    turn = np.array([[0.5, 0.5], [0.4, 0.4]])
    low = capacity_net_returns(gross, turn, np.zeros_like(turn), base_cost_bps=6.5)
    high = capacity_net_returns(gross, turn, np.full_like(turn, 30.0), base_cost_bps=6.5)
    assert (high <= low).all()
    assert high.sum() < low.sum()
