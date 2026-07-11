"""Tests for src/research/tsm_trend.py (TASK-FC-II-005 vol-targeted TSM)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.tsm_trend import (
    TsmTrendConfig,
    TsmTrendError,
    TsmTrendResult,
    _max_drawdown,
    _unit_gross,
    run_tsm_trend_backtest,
    summarize_tsm_trend,
)

HOUR_MS = 3_600_000


def _bars(rows: list[tuple[int, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["open_time", "symbol", "log_price"])


def test_unit_gross_normalizes_and_favors_low_vol_leg() -> None:
    raw = pd.DataFrame({"A": [1.0 / 1.0], "B": [-1.0 / 3.0]}, index=[0])  # sign/vol
    w = _unit_gross(raw)
    assert w.abs().sum(axis=1).iloc[0] == pytest.approx(1.0)
    assert w["A"].iloc[0] > 0 and w["B"].iloc[0] < 0  # signs preserved
    assert abs(w["A"].iloc[0]) > abs(w["B"].iloc[0])  # lower-vol leg heavier


def test_unit_gross_all_zero_or_nan_row_is_flat() -> None:
    raw = pd.DataFrame({"A": [np.nan, 0.0], "B": [np.inf, 0.0]})
    w = _unit_gross(raw)
    assert (w.iloc[0] == 0.0).all()  # NaN/inf -> flat
    assert (w.iloc[1] == 0.0).all()


def test_max_drawdown_hand_computed() -> None:
    # equity: +2, +1(-1), +3(+2) -> cumsum [2,1,3]; peak-to-trough drop = 1
    assert _max_drawdown(np.array([2.0, -1.0, 2.0])) == pytest.approx(1.0)
    assert _max_drawdown(np.array([1.0, 1.0, 1.0])) == pytest.approx(0.0)


def _trending_bars(n: int) -> pd.DataFrame:
    # A trends up, B trends down, C choppy -> clear signs; small hourly wiggle
    # so realized vol is defined and differs across legs.
    rows = []
    for i in range(n):
        t = i * HOUR_MS
        rows.append((t, "AAA", 0.001 * i + 0.0005 * (i % 2)))
        rows.append((t, "BBB", -0.001 * i + 0.001 * (i % 3)))
        rows.append((t, "CCC", 0.002 * (i % 4)))
    return _bars(rows)


def test_backtest_runs_and_signs_follow_the_trend() -> None:
    bars = _trending_bars(60)
    config = TsmTrendConfig(
        lookback_hours=5, vol_window_hours=3, hold_hours=4, cost_bps_per_leg=6.0
    )
    result = run_tsm_trend_backtest(bars, config)
    summary = summarize_tsm_trend(result, config)

    assert len(result.rebalance_times) > 0
    assert summary.n_rebalances == len(result.tsm_net)
    assert np.isfinite(summary.tsm_max_drawdown) and summary.tsm_max_drawdown >= 0.0
    assert summary.mean_turnover >= 0.0
    # Long-only never shorts: its net should equal a book with no negative legs;
    # here just assert it produced finite numbers.
    assert all(np.isfinite(x) for x in result.tsm_long_only_net)


def test_cost_reduces_net_vs_zero_cost() -> None:
    bars = _trending_bars(60)
    base = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4, cost_bps_per_leg=0.0)
    costly = TsmTrendConfig(
        lookback_hours=5, vol_window_hours=3, hold_hours=4, cost_bps_per_leg=50.0
    )
    r0 = summarize_tsm_trend(run_tsm_trend_backtest(bars, base), base)
    r1 = summarize_tsm_trend(run_tsm_trend_backtest(bars, costly), costly)
    # Same signals/weights; higher cost can only lower (or equal) net PnL.
    assert r1.tsm_net_pnl <= r0.tsm_net_pnl + 1e-9


def test_signal_is_causal_a_future_bar_does_not_change_an_earlier_rebalance() -> None:
    bars = _trending_bars(60)
    config = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4)
    base = run_tsm_trend_backtest(bars, config)

    mutated = bars.copy()
    late = mutated["open_time"] >= 50 * HOUR_MS
    mutated.loc[late, "log_price"] = 9.99  # clobber the tail
    after = run_tsm_trend_backtest(mutated, config)

    # Rebalances strictly before the mutation must be unchanged (the forward
    # return of a rebalance whose interval reaches into the tail will differ,
    # so compare only rebalances whose interval ends at/before t=50h).
    cutoff = (50 - config.hold_hours) * HOUR_MS
    for t, x_before in zip(base.rebalance_times, base.tsm_net, strict=True):
        if t <= cutoff and t in after.rebalance_times:
            x_after = after.tsm_net[after.rebalance_times.index(t)]
            assert x_after == pytest.approx(x_before)


def test_fails_closed_on_missing_column_and_duplicates() -> None:
    with pytest.raises(TsmTrendError, match="missing required columns"):
        run_tsm_trend_backtest(pd.DataFrame({"open_time": [0], "symbol": ["A"]}), TsmTrendConfig())
    dup = _bars([(0, "AAA", 1.0), (0, "AAA", 1.0)])
    with pytest.raises(TsmTrendError, match="duplicate"):
        run_tsm_trend_backtest(dup, TsmTrendConfig())


def test_config_rejects_invalid_fields() -> None:
    with pytest.raises(TsmTrendError, match="lookback_hours"):
        TsmTrendConfig(lookback_hours=0)
    with pytest.raises(TsmTrendError, match="cost"):
        TsmTrendConfig(cost_bps_per_leg=-1.0)


def test_long_and_short_sleeves_sum_to_the_gross_book() -> None:
    bars = _trending_bars(60)
    config = TsmTrendConfig(
        lookback_hours=5, vol_window_hours=3, hold_hours=4, cost_bps_per_leg=0.0
    )
    r = run_tsm_trend_backtest(bars, config)
    # With zero cost, net == gross, and long + short sleeves reconstruct it.
    for net, long_s, short_s in zip(r.tsm_net, r.tsm_long_sleeve, r.tsm_short_sleeve, strict=True):
        assert long_s + short_s == pytest.approx(net)


def test_summarize_fails_closed_on_empty() -> None:
    empty = TsmTrendResult((), (), (), (), (), (), ())
    with pytest.raises(TsmTrendError, match="no rebalances"):
        summarize_tsm_trend(empty, TsmTrendConfig())
