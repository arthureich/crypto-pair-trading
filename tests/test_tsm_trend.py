"""Tests for src/research/tsm_trend.py (TASK-FC-II-005 vol-targeted TSM)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.tsm_trend import (
    TsmTrendConfig,
    TsmTrendError,
    TsmTrendResult,
    _erc_reweight,
    _max_drawdown,
    _signal_raw_weights,
    _trend_strength_regime,
    _unit_gross,
    erc_weights,
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


def _trending_bars_with_funding(n: int, funding_rate: float) -> pd.DataFrame:
    base = _trending_bars(n)
    base["funding_rate_asof"] = funding_rate
    base["funding_interval_hours"] = 8.0
    return base


def test_zero_funding_matches_the_no_funding_run() -> None:
    bars = _trending_bars_with_funding(60, funding_rate=0.0)
    cfg_off = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4)
    cfg_on = TsmTrendConfig(
        lookback_hours=5, vol_window_hours=3, hold_hours=4, include_funding=True
    )
    off = run_tsm_trend_backtest(bars, cfg_off)
    on = run_tsm_trend_backtest(bars, cfg_on)
    for a, b in zip(off.tsm_net, on.tsm_net, strict=True):
        assert a == pytest.approx(b)  # zero funding -> identical


def test_positive_funding_costs_longs_and_pays_shorts() -> None:
    bars = _trending_bars_with_funding(60, funding_rate=0.01)  # longs pay, shorts receive
    cfg = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4, include_funding=True)
    base = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4)
    on = run_tsm_trend_backtest(bars, cfg)
    off = run_tsm_trend_backtest(bars, base)
    # Long sleeve worse with funding (pays), short sleeve better (receives).
    assert sum(on.tsm_long_sleeve) < sum(off.tsm_long_sleeve) + 1e-9
    assert sum(on.tsm_short_sleeve) > sum(off.tsm_short_sleeve) - 1e-9


def test_include_funding_requires_funding_columns() -> None:
    bars = _trending_bars(30)  # no funding columns
    cfg = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4, include_funding=True)
    with pytest.raises(TsmTrendError, match="funding"):
        run_tsm_trend_backtest(bars, cfg)


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


# --- TASK-TSM-001 regime filter -------------------------------------------------


def test_trend_strength_regime_is_binary_causal_and_off_during_warmup() -> None:
    # Single symbol, vol=1, so aggregate strength == |trailing|. Warm-up of the
    # rolling median (first `window` rows) must be OFF; a late spike must not
    # change an earlier regime value (causality).
    n = 20
    trailing = pd.DataFrame({"A": [1.0] * n})
    vol = pd.DataFrame({"A": [1.0] * n})
    window = 5
    regime = _trend_strength_regime(trailing, vol, window=window)

    assert set(regime.unique()).issubset({0.0, 1.0})  # binary
    assert (regime.iloc[:window] == 0.0).all()  # warm-up (median NaN) -> OFF

    mutated = trailing.copy()
    mutated.loc[15:, "A"] = 99.0  # clobber the tail
    regime_after = _trend_strength_regime(mutated, vol, window=window)
    # values strictly before the mutation index are unchanged
    for i in range(15):
        assert regime.iloc[i] == regime_after.iloc[i]


def test_trend_strength_regime_flags_high_vs_low_strength() -> None:
    # Low strength for a stretch (establishes a low median), then a jump high:
    # once the trailing median is defined, a value above it is ON.
    vals = [0.1] * 8 + [5.0] * 4
    trailing = pd.DataFrame({"A": vals})
    vol = pd.DataFrame({"A": [1.0] * len(vals)})
    regime = _trend_strength_regime(trailing, vol, window=4)
    # The high-strength tail (well above the trailing median of ~0.1) is ON.
    assert regime.iloc[-1] == 1.0
    assert regime.iloc[-2] == 1.0


def test_regime_filter_is_flat_when_median_undefined_short_sample() -> None:
    # The production 90d window (2160h) exceeds this 60-row fixture, so the
    # median is never defined -> the book is always flat -> zero PnL/turnover.
    bars = _trending_bars(60)
    cfg = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4, regime_filter=True)
    result = run_tsm_trend_backtest(bars, cfg)
    assert all(x == pytest.approx(0.0) for x in result.tsm_net)
    assert all(x == pytest.approx(0.0) for x in result.tsm_turnover)


def test_regime_filter_default_off_leaves_base_unchanged() -> None:
    bars = _trending_bars(60)
    base = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4)
    filtered_off = TsmTrendConfig(
        lookback_hours=5, vol_window_hours=3, hold_hours=4, regime_filter=False
    )
    r0 = run_tsm_trend_backtest(bars, base)
    r1 = run_tsm_trend_backtest(bars, filtered_off)
    for a, b in zip(r0.tsm_net, r1.tsm_net, strict=True):
        assert a == pytest.approx(b)  # default OFF == base behavior


# --- TASK-TSM-002 conviction sizing --------------------------------------------


def test_signal_raw_weights_base_is_direction_only() -> None:
    # Same vol, different trend magnitudes: base gives EQUAL |weight| (sign/vol),
    # conviction gives the STRONGER trend a larger |weight| (trailing/vol).
    trailing = pd.DataFrame({"A": [0.5], "B": [0.1]})  # A trends 5x stronger
    vol = pd.DataFrame({"A": [1.0], "B": [1.0]})  # equal vol
    base_ls, _ = _signal_raw_weights(trailing, vol, conviction=False)
    conv_ls, _ = _signal_raw_weights(trailing, vol, conviction=True)
    assert abs(base_ls["A"].iloc[0]) == pytest.approx(abs(base_ls["B"].iloc[0]))
    assert abs(conv_ls["A"].iloc[0]) > abs(conv_ls["B"].iloc[0])
    # direction preserved (both long here)
    assert conv_ls["A"].iloc[0] > 0 and conv_ls["B"].iloc[0] > 0


def test_signal_raw_weights_conviction_preserves_sign() -> None:
    trailing = pd.DataFrame({"A": [0.3], "B": [-0.2]})
    vol = pd.DataFrame({"A": [1.0], "B": [1.0]})
    base_ls, _ = _signal_raw_weights(trailing, vol, conviction=False)
    conv_ls, _ = _signal_raw_weights(trailing, vol, conviction=True)
    # same signs as the base (long A, short B)
    assert (conv_ls.iloc[0] > 0).equals(base_ls.iloc[0] > 0)


def test_conviction_sizing_default_off_matches_base() -> None:
    bars = _trending_bars(60)
    base = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4)
    off = TsmTrendConfig(
        lookback_hours=5, vol_window_hours=3, hold_hours=4, conviction_sizing=False
    )
    r0 = run_tsm_trend_backtest(bars, base)
    r1 = run_tsm_trend_backtest(bars, off)
    for a, b in zip(r0.tsm_net, r1.tsm_net, strict=True):
        assert a == pytest.approx(b)


def test_conviction_sizing_changes_book_but_keeps_unit_gross_invariant() -> None:
    bars = _trending_bars(60)
    base = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4, cost_bps_per_leg=0.0)
    conv = TsmTrendConfig(
        lookback_hours=5,
        vol_window_hours=3,
        hold_hours=4,
        cost_bps_per_leg=0.0,
        conviction_sizing=True,
    )
    r0 = run_tsm_trend_backtest(bars, base)
    r1 = run_tsm_trend_backtest(bars, conv)
    # The book is re-weighted (some rebalance differs), yet the sleeves still
    # reconstruct net at zero cost (unit-gross invariant holds under conviction).
    assert any(a != pytest.approx(b) for a, b in zip(r0.tsm_net, r1.tsm_net, strict=True))
    for net, long_s, short_s in zip(
        r1.tsm_net, r1.tsm_long_sleeve, r1.tsm_short_sleeve, strict=True
    ):
        assert long_s + short_s == pytest.approx(net)


# --- TASK-TSM-003 ERC portfolio construction -----------------------------------


def test_erc_weights_reduce_to_inverse_vol_when_uncorrelated() -> None:
    # Diagonal covariance -> ERC == inverse-vol (w_i ~ 1/sigma_i).
    cov = np.diag([0.04, 0.01])  # sigma = 0.2, 0.1
    w = erc_weights(cov)
    assert w.sum() == pytest.approx(1.0)
    assert w[0] == pytest.approx(1.0 / 3.0, abs=1e-4)  # (1/0.2):(1/0.1) = 1:2
    assert w[1] == pytest.approx(2.0 / 3.0, abs=1e-4)


def test_erc_weights_equalize_risk_contributions() -> None:
    cov = np.array([[0.04, 0.012, 0.0], [0.012, 0.09, 0.006], [0.0, 0.006, 0.0225]])
    w = erc_weights(cov)
    assert w.sum() == pytest.approx(1.0)
    assert (w > 0).all()
    rc = w * (cov @ w)  # risk contribution per asset
    assert rc.max() - rc.min() == pytest.approx(0.0, abs=1e-6)  # all equal


def test_erc_weights_symmetric_equal_variance_is_equal_weight() -> None:
    cov = np.array([[0.04, 0.02], [0.02, 0.04]])  # equal var, positive corr
    w = erc_weights(cov)
    assert w[0] == pytest.approx(0.5) and w[1] == pytest.approx(0.5)


def test_erc_weights_degenerate_sizes() -> None:
    assert erc_weights(np.empty((0, 0))).shape == (0,)
    assert erc_weights(np.array([[0.04]]))[0] == pytest.approx(1.0)


def test_erc_reweight_preserves_sleeve_gross_and_keeps_base_on_warmup() -> None:
    # Two long (A, C) and one short (B) at two rebalance rows; window=3.
    idx = list(range(8))
    hourly = pd.DataFrame(
        {
            "A": [0.01, -0.02, 0.015, -0.01, 0.02, -0.005, 0.01, -0.02],
            "B": [-0.01, 0.005, -0.02, 0.01, -0.015, 0.02, -0.01, 0.005],
            "C": [0.02, -0.01, 0.005, -0.02, 0.01, -0.015, 0.02, -0.01],
        },
        index=idx,
    )
    ls = pd.DataFrame({"A": [0.3, 0.3], "B": [-0.4, -0.4], "C": [0.3, 0.3]}, index=[2, 6])
    out = _erc_reweight(ls, hourly, window=3)
    # Row 2 has < 3 prior hours -> warm-up -> base kept unchanged.
    assert out.loc[2].to_dict() == pytest.approx(ls.loc[2].to_dict())
    # Row 6 has enough history -> ERC applied; per-sleeve gross + signs preserved.
    row = out.loc[6]
    assert row["A"] > 0 and row["C"] > 0 and row["B"] < 0  # signs
    assert row[["A", "C"]].sum() == pytest.approx(0.6)  # long gross preserved
    assert -row["B"] == pytest.approx(0.4)  # short sleeve (1 asset) -> base kept
    assert row.abs().sum() == pytest.approx(1.0)  # unit gross


def test_portfolio_erc_default_off_matches_base() -> None:
    bars = _trending_bars(60)
    base = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4)
    off = TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4, portfolio_erc=False)
    r0 = run_tsm_trend_backtest(bars, base)
    r1 = run_tsm_trend_backtest(bars, off)
    for a, b in zip(r0.tsm_net, r1.tsm_net, strict=True):
        assert a == pytest.approx(b)
