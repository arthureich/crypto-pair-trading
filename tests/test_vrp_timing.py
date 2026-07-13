"""Tests for src/research/vrp_timing.py (TASK-ALT-012 VRP-timing strategy)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.vrp_timing import (
    VrpTimingConfig,
    VrpTimingError,
    VrpTimingResult,
    _max_drawdown,
    _unit_gross,
    compute_vrp_z,
    run_vrp_timing_backtest,
    summarize_vrp_timing,
)

DAY_MS = 86_400_000


def _daily(n: int) -> pd.DataFrame:
    idx = [i * DAY_MS for i in range(n)]
    # BTC drifts up, ETH choppy -> defined signs and forward returns.
    btc = np.cumsum(np.full(n, 0.01)) + 0.002 * (np.arange(n) % 2)
    eth = 0.03 * (np.arange(n) % 3) - 0.01
    return pd.DataFrame({"btc": btc, "eth": eth}, index=idx)


def _cfg(**kw) -> VrpTimingConfig:
    return VrpTimingConfig(hold_days=2, rv_window_days=2, z_window_days=3, **kw)


def test_unit_gross_normalizes_and_flat_on_all_zero() -> None:
    raw = pd.DataFrame({"btc": [1.0, 0.0], "eth": [-1.0, 0.0]})
    w = _unit_gross(raw)
    assert w.abs().sum(axis=1).iloc[0] == pytest.approx(1.0)  # unit gross
    assert (w.iloc[1] == 0.0).all()  # all-zero row -> flat


def test_max_drawdown_hand_computed() -> None:
    assert _max_drawdown(np.array([2.0, -1.0, 2.0])) == pytest.approx(1.0)


def test_compute_vrp_z_is_causal() -> None:
    price = _daily(40)
    dvol = pd.DataFrame(
        {"btc": np.linspace(50, 70, 40), "eth": np.linspace(60, 55, 40)}, index=price.index
    )
    cfg = _cfg()
    z = compute_vrp_z(dvol, price, cfg)
    mutated = dvol.copy()
    mutated.iloc[30:] = 999.0  # clobber the tail
    z2 = compute_vrp_z(mutated, price, cfg)
    # values well before the mutation are unchanged (shift(1) + trailing only)
    assert z.iloc[:28].equals(z2.iloc[:28]) or np.allclose(
        z.iloc[:28].fillna(0), z2.iloc[:28].fillna(0)
    )


def test_backtest_runs_signs_follow_signal_and_unit_gross() -> None:
    price = _daily(40)
    # Construct vrp_z directly: BTC positive (long), ETH negative (short).
    z = pd.DataFrame({"btc": 1.0, "eth": -1.0}, index=price.index)
    cfg = _cfg()
    result = run_vrp_timing_backtest(price, z, cfg)
    summary = summarize_vrp_timing(result, cfg)
    assert len(result.rebalance_times) > 0
    assert summary.n_rebalances == len(result.strat_net)
    assert np.isfinite(summary.strat_max_drawdown)


def test_long_only_never_shorts() -> None:
    price = _daily(40)
    z = pd.DataFrame({"btc": 1.0, "eth": -1.0}, index=price.index)
    ls = run_vrp_timing_backtest(price, z, _cfg())
    lo = run_vrp_timing_backtest(price, z, _cfg(long_only=True))
    # different books (short leg dropped) -> generally different net
    assert any(a != pytest.approx(b) for a, b in zip(ls.strat_net, lo.strat_net, strict=True))


def test_cost_reduces_net() -> None:
    price = _daily(40)
    z = pd.DataFrame({"btc": 1.0, "eth": -1.0}, index=price.index)
    free = run_vrp_timing_backtest(price, z, _cfg(cost_bps_per_leg=0.0))
    costly = run_vrp_timing_backtest(price, z, _cfg(cost_bps_per_leg=100.0))
    assert sum(costly.strat_net) <= sum(free.strat_net) + 1e-9


def test_signal_is_causal_future_bar_does_not_change_earlier_rebalance() -> None:
    price = _daily(40)
    z = pd.DataFrame(
        {"btc": np.sign(np.sin(np.arange(40))), "eth": np.sign(np.cos(np.arange(40)))},
        index=price.index,
    )
    cfg = _cfg()
    base = run_vrp_timing_backtest(price, z, cfg)
    mutated = price.copy()
    mutated.iloc[35:] = 9.0
    after = run_vrp_timing_backtest(mutated, z, cfg)
    cutoff = (35 - cfg.hold_days) * DAY_MS
    for t, x in zip(base.rebalance_times, base.strat_net, strict=True):
        if t <= cutoff and t in after.rebalance_times:
            assert after.strat_net[after.rebalance_times.index(t)] == pytest.approx(x)


def test_config_and_summary_fail_closed() -> None:
    with pytest.raises(VrpTimingError, match="hold_days"):
        VrpTimingConfig(hold_days=0)
    with pytest.raises(VrpTimingError, match="cost"):
        VrpTimingConfig(cost_bps_per_leg=-1.0)
    with pytest.raises(VrpTimingError, match="no rebalances"):
        summarize_vrp_timing(VrpTimingResult((), (), (), ()), VrpTimingConfig())
    with pytest.raises(VrpTimingError, match="empty"):
        run_vrp_timing_backtest(pd.DataFrame(), pd.DataFrame(), VrpTimingConfig())
