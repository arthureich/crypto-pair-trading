"""Tests for the pre-declared conservative execution model (TASK-DEPLOY-001, Phase 3)."""

from __future__ import annotations

import math

import pandas as pd

from src.research.execution_model import DECLARED_COST_BPS_PER_LEG, ExecutionCostModel


def test_base_cost_is_fee_plus_half_spread_at_zero_participation():
    m = ExecutionCostModel()
    d = m.per_leg_cost_bps(0.0)
    assert d.slippage_bps == 0.0
    assert math.isclose(d.total_bps, m.taker_fee_bps + m.half_spread_bps)


def test_cost_monotonic_in_participation():
    m = ExecutionCostModel()
    lo = m.per_leg_cost_bps(0.1).total_bps
    hi = m.per_leg_cost_bps(0.5).total_bps
    assert hi > lo


def test_participation_clipped():
    m = ExecutionCostModel(max_participation=1.0)
    at_cap = m.per_leg_cost_bps(1.0).total_bps
    over_cap = m.per_leg_cost_bps(5.0).total_bps
    assert math.isclose(at_cap, over_cap)  # clipped, no runaway slippage


def test_decomposition_sums_to_total():
    d = ExecutionCostModel().per_leg_cost_bps(0.3)
    assert math.isclose(d.total_bps, d.fee_bps + d.half_spread_bps + d.slippage_bps)


def test_executable_worse_than_theoretical_at_base_size():
    # base executable cost 6.5 bps > declared 6.0 bps -> executable slightly worse
    m = ExecutionCostModel()
    gross = pd.Series([0.02, 0.01, -0.005])
    turn = pd.Series([0.5, 0.4, 0.6])
    theo = m.theoretical_net(gross, turn)
    exe = m.executable_net(gross, turn)
    assert (exe <= theo + 1e-12).all()
    assert exe.sum() < theo.sum()


def test_theoretical_uses_declared_6bps():
    m = ExecutionCostModel()
    gross = pd.Series([0.02])
    turn = pd.Series([1.0])
    theo = m.theoretical_net(gross, turn)
    assert math.isclose(theo.iloc[0], 0.02 - DECLARED_COST_BPS_PER_LEG / 10_000.0)


def test_executable_is_memoryless_no_lookahead():
    # changing a LATER rebalance's turnover must not change an EARLIER net value
    m = ExecutionCostModel()
    gross = pd.Series([0.01, 0.01, 0.01])
    turn_a = pd.Series([0.3, 0.3, 0.3])
    turn_b = pd.Series([0.3, 0.3, 9.9])  # only the last differs
    a = m.executable_net(gross, turn_a)
    b = m.executable_net(gross, turn_b)
    assert math.isclose(a.iloc[0], b.iloc[0])
    assert math.isclose(a.iloc[1], b.iloc[1])
    assert not math.isclose(a.iloc[2], b.iloc[2])


def test_participation_increases_cost_reduces_net():
    m = ExecutionCostModel()
    gross = pd.Series([0.02, 0.02])
    turn = pd.Series([1.0, 1.0])
    small = m.executable_net(gross, turn, participation=pd.Series([0.0, 0.0]))
    big = m.executable_net(gross, turn, participation=pd.Series([0.5, 0.5]))
    assert (big < small).all()
