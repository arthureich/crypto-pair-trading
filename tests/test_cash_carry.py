"""Tests for cash-and-carry mechanics (TASK-BASIS-001, ADR-0034).

The central test is delta-neutrality: the locked return equals the entry basis for
ANY settlement price (the profit does not depend on the price path).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.research.cash_carry import (
    annualize_return,
    annualized_basis,
    basis_fraction,
    capital_employed_return,
    clears_deploy_hurdle,
    funding_carry_return,
    locked_carry_return,
    net_carry_return,
    worst_adverse_mtm,
)


def test_basis_fraction():
    assert math.isclose(basis_fraction(100_000.0, 103_000.0), 0.03)


def test_basis_fraction_rejects_nonpositive_spot():
    with pytest.raises(ValueError, match="spot"):
        basis_fraction(0.0, 100.0)


def test_annualized_basis():
    # 3% over 90 days -> ~12.17% APR
    apr = annualized_basis(100_000.0, 103_000.0, 90.0)
    assert math.isclose(apr, 0.03 * 365.0 / 90.0, rel_tol=1e-9)


def test_locked_return_is_path_independent():
    # entry basis 3%; the realized return must be 3% for ANY settlement price
    entry_spot, entry_fut = 100_000.0, 103_000.0
    expected = 0.03
    for settle in (50_000.0, 100_000.0, 130_000.0, 250_000.0):
        assert math.isclose(
            locked_carry_return(entry_spot, entry_fut, settle), expected, rel_tol=1e-12
        )


def test_net_carry_subtracts_costs():
    # 3% gross, 4 legs * 6.5bps = 26bps cost -> 2.74% net
    net = net_carry_return(100_000.0, 103_000.0, cost_bps_per_leg=6.5, n_legs_roundtrip=4)
    assert math.isclose(net, 0.03 - 4 * 6.5 / 10_000.0, rel_tol=1e-9)


def test_net_carry_can_go_negative_when_basis_below_cost():
    # tiny basis (5bps) vs 26bps cost -> negative net (fees eat the spread)
    net = net_carry_return(100_000.0, 100_050.0, cost_bps_per_leg=6.5, n_legs_roundtrip=4)
    assert net < 0.0


def test_worst_adverse_mtm_when_basis_widens():
    # basis widens from 3000 to 5000 mid-trade -> adverse MTM = -(5000-3000)/100000
    entry_spot, entry_fut = 100_000.0, 103_000.0
    spot_path = np.array([100_000.0, 100_000.0, 100_000.0])
    fut_path = np.array([103_000.0, 105_000.0, 103_000.0])  # widens then converges
    mtm = worst_adverse_mtm(entry_spot, entry_fut, spot_path, fut_path)
    assert math.isclose(mtm, -(5_000.0 - 3_000.0) / 100_000.0, rel_tol=1e-9)


def test_worst_adverse_mtm_nonpositive_when_basis_only_narrows():
    entry_spot, entry_fut = 100_000.0, 103_000.0
    spot_path = np.array([100_000.0, 100_000.0])
    fut_path = np.array([103_000.0, 101_000.0])  # only narrows (favorable)
    mtm = worst_adverse_mtm(entry_spot, entry_fut, spot_path, fut_path)
    assert mtm >= 0.0  # never marked adversely


def test_capital_employed_return_scaling():
    # 2.74% on spot notional, 10% margin -> capital employed 1.10
    roc = capital_employed_return(0.0274, margin_fraction=0.10)
    assert math.isclose(roc["return_on_capital_employed"], 0.0274 / 1.10, rel_tol=1e-9)
    assert math.isclose(roc["return_on_margin"], 0.0274 / 0.10, rel_tol=1e-9)
    assert math.isclose(roc["capital_employed_per_unit_spot"], 1.10)


def test_capital_employed_rejects_bad_margin():
    with pytest.raises(ValueError, match="margin_fraction"):
        capital_employed_return(0.02, margin_fraction=0.0)


def test_funding_carry_sums_rates_minus_cost():
    # short perp receives +sum(rate); 3 settlements of +1bp = +3bps gross
    rates = [0.0001, 0.0001, 0.0001]
    net = funding_carry_return(rates, cost_bps_per_leg=6.5, n_legs_roundtrip=4)
    assert math.isclose(net, 0.0003 - 4 * 6.5 / 10_000.0, rel_tol=1e-9)


def test_funding_carry_negative_when_funding_turns_negative():
    # persistently negative funding (bear) -> short perp PAYS -> negative carry
    rates = [-0.0002] * 10
    assert funding_carry_return(rates, cost_bps_per_leg=6.5) < 0.0


def test_annualize_return():
    assert math.isclose(annualize_return(0.03, 90.0), 0.03 * 365.0 / 90.0, rel_tol=1e-9)
    with pytest.raises(ValueError, match="days_held"):
        annualize_return(0.03, 0.0)


def test_clears_deploy_hurdle():
    # above hurdle with enough settlements -> deployable
    assert clears_deploy_hurdle(0.15, 0.11, 400, min_settlements=90) is True
    # below hurdle -> not deployable even with many settlements
    assert clears_deploy_hurdle(0.07, 0.11, 400, min_settlements=90) is False
    # above hurdle but too few settlements -> not a valid read
    assert clears_deploy_hurdle(0.15, 0.11, 50, min_settlements=90) is False
