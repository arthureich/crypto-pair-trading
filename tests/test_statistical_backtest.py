from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import statistical_backtest  # noqa: E402
from src.backtest.statistical_backtest import (  # noqa: E402
    StatisticalBacktestConfig,
    StatisticalBacktestError,
    StatisticalTradeResult,
    TradeStatus,
    _pair_frame,
    _pair_symbols,
    resolve_trade_pnl,
    run_pair_statistical_backtest,
    summarize_statistical_backtest,
)
from src.research.triple_barrier import (  # noqa: E402
    BarrierOutcome,
    BarrierSide,
    TripleBarrierLabel,
)

HOUR_MS = 60 * 60 * 1000


def _label(
    *,
    side: BarrierSide,
    outcome: BarrierOutcome,
    exit_index: int | None,
    bars_held: int,
) -> TripleBarrierLabel:
    return TripleBarrierLabel(
        entry_index=0,
        entry_time=0,
        side=side,
        entry_zscore=2.5,
        outcome=outcome,
        exit_index=exit_index,
        exit_time=(exit_index * HOUR_MS) if exit_index is not None else None,
        exit_zscore=0.0,
        bars_held=bars_held,
    )


def test_resolve_trade_pnl_short_spread_matches_manual_formula() -> None:
    # SHORT_SPREAD profits when spread falls: gross = -(delta_a - beta*delta_b).
    log_price_a = np.array([0.10, 0.10, 0.08])
    log_price_b = np.array([0.00, 0.00, 0.02])
    label = _label(side=BarrierSide.SHORT_SPREAD, outcome=BarrierOutcome.PROFIT, exit_index=2, bars_held=2)
    config = StatisticalBacktestConfig(conservative_fee_slippage_bps_per_leg_roundtrip=6.0)

    trade = resolve_trade_pnl(
        pair="AAA/BBB",
        label=label,
        entry_position=0,
        log_price_a=log_price_a,
        log_price_b=log_price_b,
        beta=1.0,
        funding_carry_bps_per_day=12.0,
        config=config,
    )

    delta_a_bps = (0.08 - 0.10) * 10_000.0
    delta_b_bps = (0.02 - 0.00) * 10_000.0
    spread_change_bps = delta_a_bps - 1.0 * delta_b_bps  # -200 - 200 = -400
    expected_gross = -spread_change_bps  # SHORT_SPREAD: direction = -1
    expected_cost = abs(12.0) * (2 / 24.0) + 2.0 * 6.0
    expected_net = expected_gross - expected_cost

    assert trade.status is TradeStatus.RESOLVED
    assert trade.gross_pnl_bps == pytest.approx(expected_gross)
    assert trade.cost_bps == pytest.approx(expected_cost)
    assert trade.net_pnl_bps == pytest.approx(expected_net)
    assert trade.net_pnl_bps == pytest.approx(trade.gross_pnl_bps - trade.cost_bps)


def test_resolve_trade_pnl_scales_funding_cost_by_bar_duration_hours() -> None:
    # 2 bars held at 5-minute bars (bar_duration_hours=1/12) is 10 minutes of
    # real holding time, not 2 hours -- a prior bug assumed 1 bar == 1 hour
    # unconditionally, which would silently 12x-overstate funding cost here.
    label = _label(side=BarrierSide.SHORT_SPREAD, outcome=BarrierOutcome.PROFIT, exit_index=2, bars_held=2)
    five_minute_bars = StatisticalBacktestConfig(
        conservative_fee_slippage_bps_per_leg_roundtrip=0.0,
        bar_duration_hours=1.0 / 12.0,
    )
    one_hour_bars = StatisticalBacktestConfig(conservative_fee_slippage_bps_per_leg_roundtrip=0.0)

    five_minute_trade = resolve_trade_pnl(
        pair="AAA/BBB",
        label=label,
        entry_position=0,
        log_price_a=np.array([0.0, 0.0, 0.0]),
        log_price_b=np.array([0.0, 0.0, 0.0]),
        beta=1.0,
        funding_carry_bps_per_day=24.0,
        config=five_minute_bars,
    )
    one_hour_trade = resolve_trade_pnl(
        pair="AAA/BBB",
        label=label,
        entry_position=0,
        log_price_a=np.array([0.0, 0.0, 0.0]),
        log_price_b=np.array([0.0, 0.0, 0.0]),
        beta=1.0,
        funding_carry_bps_per_day=24.0,
        config=one_hour_bars,
    )

    # 2 bars * (1/12)h / 24h/day * 24 bps/day = 1/6 bps.
    assert five_minute_trade.cost_bps == pytest.approx(1.0 / 6.0)
    # 2 bars * 1h / 24h/day * 24 bps/day = 2 bps -- 12x the 5-minute cost,
    # exactly the ratio of the two bar durations.
    assert one_hour_trade.cost_bps == pytest.approx(2.0)
    assert one_hour_trade.cost_bps == pytest.approx(five_minute_trade.cost_bps * 12.0)


def test_resolve_trade_pnl_long_spread_matches_manual_formula() -> None:
    # LONG_SPREAD profits when spread rises: gross = +(delta_a - beta*delta_b).
    log_price_a = np.array([0.00, 0.00, 0.05])
    log_price_b = np.array([0.00, 0.00, -0.01])
    label = _label(side=BarrierSide.LONG_SPREAD, outcome=BarrierOutcome.VERTICAL, exit_index=2, bars_held=2)
    config = StatisticalBacktestConfig(conservative_fee_slippage_bps_per_leg_roundtrip=4.0)

    trade = resolve_trade_pnl(
        pair="AAA/BBB",
        label=label,
        entry_position=0,
        log_price_a=log_price_a,
        log_price_b=log_price_b,
        beta=2.0,
        funding_carry_bps_per_day=-6.0,
        config=config,
    )

    delta_a_bps = (0.05 - 0.00) * 10_000.0
    delta_b_bps = (-0.01 - 0.00) * 10_000.0
    spread_change_bps = delta_a_bps - 2.0 * delta_b_bps  # 500 - (-200) = 700
    expected_gross = spread_change_bps  # LONG_SPREAD: direction = +1
    expected_cost = abs(-6.0) * (2 / 24.0) + 2.0 * 4.0
    expected_net = expected_gross - expected_cost

    assert trade.gross_pnl_bps == pytest.approx(expected_gross)
    assert trade.cost_bps == pytest.approx(expected_cost)
    assert trade.net_pnl_bps == pytest.approx(expected_net)


def test_resolve_trade_pnl_no_data_outcome_is_unresolved_and_zeroed() -> None:
    label = _label(side=BarrierSide.SHORT_SPREAD, outcome=BarrierOutcome.NO_DATA, exit_index=None, bars_held=0)

    trade = resolve_trade_pnl(
        pair="AAA/BBB",
        label=label,
        entry_position=0,
        log_price_a=np.array([0.0]),
        log_price_b=np.array([0.0]),
        beta=1.0,
        funding_carry_bps_per_day=5.0,
        config=StatisticalBacktestConfig(),
    )

    assert trade.status is TradeStatus.UNRESOLVED_NO_DATA
    assert trade.gross_pnl_bps == 0.0
    assert trade.cost_bps == 0.0
    assert trade.net_pnl_bps == 0.0


def _trade(net_pnl_bps: float, entry_index: int, bars_held: int = 5) -> StatisticalTradeResult:
    return StatisticalTradeResult(
        pair="AAA/BBB",
        status=TradeStatus.RESOLVED,
        side=BarrierSide.SHORT_SPREAD,
        entry_time=entry_index * HOUR_MS,
        entry_zscore=2.5,
        exit_time=(entry_index + bars_held) * HOUR_MS,
        outcome=BarrierOutcome.PROFIT,
        bars_held=bars_held,
        gross_pnl_bps=net_pnl_bps,
        cost_bps=0.0,
        net_pnl_bps=net_pnl_bps,
    )


def test_summarize_statistical_backtest_matches_hand_computed_metrics() -> None:
    trades = tuple(
        _trade(value, index) for index, value in enumerate([10.0, 20.0, 5.0, -8.0, -2.0])
    )

    metrics = summarize_statistical_backtest(trades, target_notional=1_000.0)

    assert metrics.trade_count == 5
    assert metrics.hit_rate == pytest.approx(0.6)
    assert metrics.profit_factor == pytest.approx(3.5)
    assert metrics.sharpe == pytest.approx(5.0 / math.sqrt(117.0))
    assert metrics.sortino == pytest.approx(5.0 / math.sqrt(18.0))
    assert metrics.max_drawdown_bps == pytest.approx(10.0)
    assert metrics.avg_win_bps == pytest.approx(35.0 / 3.0)
    assert metrics.avg_loss_bps == pytest.approx(-5.0)
    assert metrics.turnover_notional == pytest.approx(5_000.0)
    assert metrics.net_pnl_bps == pytest.approx(25.0)


def test_profit_factor_gate_rejects_pairs_below_threshold_without_hiding_them() -> None:
    losing_trades = (_trade(5.0, 0), _trade(-10.0, 1))
    metrics = summarize_statistical_backtest(losing_trades)

    assert metrics.trade_count == 2
    assert metrics.profit_factor < 1.10
    assert metrics.profit_factor_gate_pass is False

    winning_trades = (_trade(20.0, 0), _trade(-5.0, 1))
    winning_metrics = summarize_statistical_backtest(winning_trades)

    assert winning_metrics.profit_factor >= 1.10
    assert winning_metrics.profit_factor_gate_pass is True


def test_empty_trades_summary_reports_nan_gate_failure_not_a_hidden_pass() -> None:
    metrics = summarize_statistical_backtest(())

    assert metrics.trade_count == 0
    assert math.isnan(metrics.profit_factor)
    assert metrics.profit_factor_gate_pass is False


def test_all_winning_trades_pass_the_gate_instead_of_being_vetoed_by_inf() -> None:
    # Zero losers -> profit_factor is +inf (maximally profitable), not NaN.
    # A prior bug used math.isfinite() here, which rejects +inf and silently
    # marks the best possible outcome as gate-failed.
    all_wins = (_trade(10.0, 0), _trade(20.0, 1), _trade(5.0, 2))

    metrics = summarize_statistical_backtest(all_wins)

    assert math.isinf(metrics.profit_factor)
    assert metrics.profit_factor_gate_pass is True


def test_resolve_trade_pnl_rejects_non_finite_funding_carry() -> None:
    label = _label(side=BarrierSide.SHORT_SPREAD, outcome=BarrierOutcome.PROFIT, exit_index=1, bars_held=1)

    with pytest.raises(StatisticalBacktestError):
        resolve_trade_pnl(
            pair="AAA/BBB",
            label=label,
            entry_position=0,
            log_price_a=np.array([0.0, 0.01]),
            log_price_b=np.array([0.0, 0.0]),
            beta=1.0,
            funding_carry_bps_per_day=math.nan,
            config=StatisticalBacktestConfig(),
        )


def test_pair_symbols_strips_whitespace_around_separator() -> None:
    assert _pair_symbols("  aaa / bbb  ") == ("AAA", "BBB")


def test_pair_frame_rejects_duplicate_open_time_rows_per_symbol() -> None:
    bars = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA", "BBB"],
            "open_time": [0, 0, 0],
            "log_price": [0.1, 0.2, 0.1],
        }
    )

    with pytest.raises(StatisticalBacktestError):
        _pair_frame(bars, "AAA", "BBB")


def test_config_rejects_invalid_fields() -> None:
    with pytest.raises(StatisticalBacktestError):
        StatisticalBacktestConfig(zscore_window=0)
    with pytest.raises(StatisticalBacktestError):
        StatisticalBacktestConfig(entry_zscore=-1.0)
    with pytest.raises(StatisticalBacktestError):
        StatisticalBacktestConfig(conservative_fee_slippage_bps_per_leg_roundtrip=-1.0)
    with pytest.raises(StatisticalBacktestError):
        StatisticalBacktestConfig(max_vertical_bars=1.5)


def _build_synthetic_bars(n_bars: int, *, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    log_price_b = np.cumsum(rng.normal(0.0, 0.01, size=n_bars))
    phi = 0.9
    innovations = rng.normal(0.0, 0.05, size=n_bars)
    ar_noise = np.zeros(n_bars)
    for index in range(1, n_bars):
        ar_noise[index] = phi * ar_noise[index - 1] + innovations[index]
    log_price_a = 1.0 * log_price_b + ar_noise
    open_time = (np.arange(n_bars, dtype=np.int64)) * HOUR_MS
    frame_a = pd.DataFrame({"symbol": "AAA", "open_time": open_time, "log_price": log_price_a})
    frame_b = pd.DataFrame({"symbol": "BBB", "open_time": open_time, "log_price": log_price_b})
    return pd.concat([frame_a, frame_b], ignore_index=True)


def test_run_pair_statistical_backtest_is_causal_across_appended_future_bars() -> None:
    """Extending the series with future bars must not change trades already
    fully resolved within the earlier, truncated window -- signal generation
    (Kalman/rolling z-score/OU) and barrier resolution are both causal."""

    full_bars = _build_synthetic_bars(260)
    cutoff_bar = 200
    truncated_bars = full_bars[full_bars["open_time"] < cutoff_bar * HOUR_MS]

    config = StatisticalBacktestConfig(
        zscore_window=40,
        ou_window=40,
        entry_zscore=1.5,
        max_half_life_hours=50.0,
        max_vertical_bars=30,
    )

    full_trades = run_pair_statistical_backtest(
        full_bars, "AAA/BBB", funding_carry_bps_per_day=10.0, config=config
    )
    truncated_trades = run_pair_statistical_backtest(
        truncated_bars, "AAA/BBB", funding_carry_bps_per_day=10.0, config=config
    )

    safe_cutoff_ms = (cutoff_bar - config.max_vertical_bars - 5) * HOUR_MS
    full_safe = [t for t in full_trades if t.entry_time < safe_cutoff_ms]
    truncated_safe = [t for t in truncated_trades if t.entry_time < safe_cutoff_ms]

    assert full_safe  # sanity: the synthetic series actually produces trades
    assert full_safe == truncated_safe


def test_run_pair_statistical_backtest_passes_bar_duration_hours_as_ou_dt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The OU half-life is only meaningful in hours if `dt` reflects the real
    bar duration -- for 5-minute bars, dt=1.0 (the estimate_ou default) would
    silently compute half-life in units of "per 5-min-bar" while still being
    compared against an hours-denominated max_half_life_hours threshold."""

    captured_dt = []

    def fake_fit_kalman_filter(*, y, x, config):  # noqa: ARG001
        length = len(y)
        return SimpleNamespace(
            beta=np.ones(length),
            spread=np.arange(length, dtype=float),
            unstable_points=np.zeros(length, dtype=bool),
        )

    def fake_rolling_zscore(spread, *, window: int, min_periods: int) -> pd.Series:  # noqa: ARG001
        return pd.Series([math.nan, math.nan, 2.5, 1.0, 1.0, 1.0, 1.0, 1.0])

    def fake_estimate_ou(spread, *, dt: float, min_observations: int):  # noqa: ARG001
        captured_dt.append(dt)
        return SimpleNamespace(mean_reverting=True, half_life=100.0)

    monkeypatch.setattr(statistical_backtest, "fit_kalman_filter", fake_fit_kalman_filter)
    monkeypatch.setattr(statistical_backtest, "rolling_zscore", fake_rolling_zscore)
    monkeypatch.setattr(statistical_backtest, "estimate_ou", fake_estimate_ou)

    open_time = np.arange(8, dtype=np.int64) * (5 * 60 * 1000)
    bars = pd.concat(
        [
            pd.DataFrame({"symbol": "AAA", "open_time": open_time, "log_price": np.arange(8)}),
            pd.DataFrame({"symbol": "BBB", "open_time": open_time, "log_price": np.zeros(8)}),
        ],
        ignore_index=True,
    )
    config = StatisticalBacktestConfig(
        zscore_window=2, ou_window=2, max_vertical_bars=4, bar_duration_hours=1.0 / 12.0
    )

    run_pair_statistical_backtest(bars, "AAA/BBB", funding_carry_bps_per_day=0.0, config=config)

    assert captured_dt
    assert all(dt == pytest.approx(1.0 / 12.0) for dt in captured_dt)


def test_run_pair_statistical_backtest_supplies_confirming_bar_for_vertical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_window_lengths = []

    def fake_fit_kalman_filter(*, y, x, config):  # noqa: ARG001
        length = len(y)
        return SimpleNamespace(
            beta=np.ones(length),
            spread=np.arange(length, dtype=float),
            unstable_points=np.zeros(length, dtype=bool),
        )

    def fake_rolling_zscore(spread, *, window: int, min_periods: int) -> pd.Series:  # noqa: ARG001
        return pd.Series([math.nan, math.nan, 2.5, 1.0, 1.0, 1.0, 1.0, 1.0])

    def fake_estimate_ou(spread, *, dt: float, min_observations: int):  # noqa: ARG001
        return SimpleNamespace(mean_reverting=True, half_life=100.0)

    def fake_label_directional_triple_barrier(zscores, open_time, config):
        captured_window_lengths.append(len(zscores))
        return (
            TripleBarrierLabel(
                entry_index=0,
                entry_time=int(open_time.iloc[0]),
                side=BarrierSide.SHORT_SPREAD,
                entry_zscore=2.5,
                outcome=BarrierOutcome.VERTICAL,
                exit_index=4,
                exit_time=int(open_time.iloc[4]),
                exit_zscore=1.0,
                bars_held=4,
            ),
        )

    monkeypatch.setattr(statistical_backtest, "fit_kalman_filter", fake_fit_kalman_filter)
    monkeypatch.setattr(statistical_backtest, "rolling_zscore", fake_rolling_zscore)
    monkeypatch.setattr(statistical_backtest, "estimate_ou", fake_estimate_ou)
    monkeypatch.setattr(
        statistical_backtest,
        "label_directional_triple_barrier",
        fake_label_directional_triple_barrier,
    )
    open_time = np.arange(8, dtype=np.int64) * HOUR_MS
    bars = pd.concat(
        [
            pd.DataFrame({"symbol": "AAA", "open_time": open_time, "log_price": np.arange(8)}),
            pd.DataFrame({"symbol": "BBB", "open_time": open_time, "log_price": np.zeros(8)}),
        ],
        ignore_index=True,
    )
    config = StatisticalBacktestConfig(zscore_window=2, ou_window=2, max_vertical_bars=4)

    trades = run_pair_statistical_backtest(
        bars,
        "AAA/BBB",
        funding_carry_bps_per_day=0.0,
        config=config,
    )

    assert captured_window_lengths == [config.max_vertical_bars + 2]
    assert len(trades) == 1
    assert trades[0].outcome is BarrierOutcome.VERTICAL


def test_run_pair_statistical_backtest_passes_bar_duration_to_triple_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The statistical backtest owns the bar duration and passes it through to
    the real triple-barrier config. `max_vertical_bars` remains a bar-count cap;
    callers that change granularity must scale that cap when they want to keep
    the same real-time maximum duration."""

    captured_window_lengths = []
    captured_bar_duration_hours = []
    captured_max_vertical_bars = []

    def fake_fit_kalman_filter(*, y, x, config):  # noqa: ARG001
        length = len(y)
        return SimpleNamespace(
            beta=np.ones(length),
            spread=np.arange(length, dtype=float),
            unstable_points=np.zeros(length, dtype=bool),
        )

    def fake_rolling_zscore(spread, *, window: int, min_periods: int) -> pd.Series:  # noqa: ARG001
        values = [math.nan, math.nan, 2.5] + [1.0] * 60
        return pd.Series(values)

    def fake_estimate_ou(spread, *, dt: float, min_observations: int):  # noqa: ARG001
        return SimpleNamespace(mean_reverting=True, half_life=100.0)

    def fake_label_directional_triple_barrier(zscores, open_time, config):
        captured_window_lengths.append(len(zscores))
        captured_bar_duration_hours.append(config.bar_duration_hours)
        captured_max_vertical_bars.append(config.max_vertical_bars)
        exit_index = len(zscores) - 1
        return (
            TripleBarrierLabel(
                entry_index=0,
                entry_time=int(open_time.iloc[0]),
                side=BarrierSide.SHORT_SPREAD,
                entry_zscore=2.5,
                outcome=BarrierOutcome.VERTICAL,
                exit_index=exit_index,
                exit_time=int(open_time.iloc[exit_index]),
                exit_zscore=1.0,
                bars_held=exit_index,
            ),
        )

    monkeypatch.setattr(statistical_backtest, "fit_kalman_filter", fake_fit_kalman_filter)
    monkeypatch.setattr(statistical_backtest, "rolling_zscore", fake_rolling_zscore)
    monkeypatch.setattr(statistical_backtest, "estimate_ou", fake_estimate_ou)
    monkeypatch.setattr(
        statistical_backtest,
        "label_directional_triple_barrier",
        fake_label_directional_triple_barrier,
    )
    five_minute_ms = 5 * 60 * 1000
    open_time = np.arange(63, dtype=np.int64) * five_minute_ms
    bars = pd.concat(
        [
            pd.DataFrame({"symbol": "AAA", "open_time": open_time, "log_price": np.arange(63)}),
            pd.DataFrame({"symbol": "BBB", "open_time": open_time, "log_price": np.zeros(63)}),
        ],
        ignore_index=True,
    )
    config = StatisticalBacktestConfig(
        zscore_window=2,
        ou_window=2,
        max_vertical_bars=4,
        bar_duration_hours=1.0 / 12.0,
    )

    run_pair_statistical_backtest(bars, "AAA/BBB", funding_carry_bps_per_day=0.0, config=config)

    assert captured_window_lengths[0] == config.max_vertical_bars + 2
    assert captured_bar_duration_hours == [pytest.approx(1.0 / 12.0)]
    assert captured_max_vertical_bars == [config.max_vertical_bars]


def test_run_pair_statistical_backtest_confirming_bar_resolves_vertical_with_real_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end with the REAL triple-barrier resolver: an entry that never
    touches PROFIT/STOP within a 4h budget must resolve as VERTICAL, not be
    silently downgraded to NO_DATA. The real resolver only confirms VERTICAL
    once it sees a bar strictly beyond the elapsed-time budget, so the window
    the backtest passes it (`max_vertical_bars + 2`) must include that
    confirming bar. If the window were `+1`, this same case would fail-close
    to NO_DATA -- so this test would catch a regression of the fix even
    against a change in the resolver's own semantics."""

    def fake_fit_kalman_filter(*, y, x, config):  # noqa: ARG001
        length = len(y)
        return SimpleNamespace(
            beta=np.ones(length),
            spread=np.arange(length, dtype=float),
            unstable_points=np.zeros(length, dtype=bool),
        )

    # Entry at index 2 (z=2.5, SHORT_SPREAD). z stays strictly between the
    # profit barrier (0.0) and the stop barrier (2.5 + 1.0 = 3.5) for the whole
    # budget, so neither fires -> VERTICAL is the only correct outcome.
    def fake_rolling_zscore(spread, *, window: int, min_periods: int) -> pd.Series:  # noqa: ARG001
        return pd.Series([math.nan, math.nan, 2.5, 2.4, 2.3, 2.2, 2.1, 2.0])

    def fake_estimate_ou(spread, *, dt: float, min_observations: int):  # noqa: ARG001
        # half_life * multiplier is huge, so vertical_barrier_bars is capped at
        # max_vertical_bars (4).
        return SimpleNamespace(mean_reverting=True, half_life=100.0)

    monkeypatch.setattr(statistical_backtest, "fit_kalman_filter", fake_fit_kalman_filter)
    monkeypatch.setattr(statistical_backtest, "rolling_zscore", fake_rolling_zscore)
    monkeypatch.setattr(statistical_backtest, "estimate_ou", fake_estimate_ou)
    # NOTE: label_directional_triple_barrier is deliberately NOT mocked here.

    open_time = np.arange(8, dtype=np.int64) * HOUR_MS
    bars = pd.concat(
        [
            pd.DataFrame({"symbol": "AAA", "open_time": open_time, "log_price": np.arange(8)}),
            pd.DataFrame({"symbol": "BBB", "open_time": open_time, "log_price": np.zeros(8)}),
        ],
        ignore_index=True,
    )
    config = StatisticalBacktestConfig(zscore_window=2, ou_window=2, max_vertical_bars=4)

    trades = run_pair_statistical_backtest(
        bars,
        "AAA/BBB",
        funding_carry_bps_per_day=0.0,
        config=config,
    )

    # Every bar at/after index 2 crosses the entry threshold, so each opens its
    # own entry (matching the module's documented per-bar behavior). Only the
    # first entry (index 2) has the full budget + confirming bar available; the
    # later ones legitimately run out of data and fail-close to NO_DATA. The
    # point of this test is the first entry: with the confirming bar present it
    # resolves VERTICAL, not NO_DATA.
    assert trades  # sanity
    first = trades[0]
    assert first.status is TradeStatus.RESOLVED
    assert first.outcome is BarrierOutcome.VERTICAL
    assert first.bars_held == config.max_vertical_bars


def test_run_pair_statistical_backtest_returns_empty_for_insufficient_bars() -> None:
    bars = _build_synthetic_bars(10)

    trades = run_pair_statistical_backtest(bars, "AAA/BBB", funding_carry_bps_per_day=1.0)

    assert trades == ()
