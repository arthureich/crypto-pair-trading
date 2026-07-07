from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsmom_breakout import (  # noqa: E402
    TradeSide,
    TradeStatus,
    TSMOMConfig,
    TSMOMError,
    TSMOMTrade,
    run_tsmom_backtest,
    summarize_tsmom_backtest,
)

HOUR_MS = 60 * 60 * 1000


def _bar(symbol: str, t: int, high: float, low: float, close: float) -> dict:
    return {"symbol": symbol, "open_time": t * HOUR_MS, "high": high, "low": low, "close": close}


def _long_entry_then_stop_out_bars() -> pd.DataFrame:
    """Hand-computed fixture: LONG entry at t=3 (price 104), stop-out at t=5 (price 92).

    donchian_window_hours=2, atr_period_hours=2 (config used by the tests
    below) -- see the module docstring/task file for the exact causal
    formula this reproduces by hand.
    """

    rows = [
        _bar("A", 0, 101.0, 99.0, 100.0),
        _bar("A", 1, 101.0, 99.0, 100.0),
        _bar("A", 2, 101.0, 99.0, 100.0),
        _bar("A", 3, 105.0, 103.0, 104.0),  # breakout: close > donchian_high(=101)
        _bar("A", 4, 110.0, 108.0, 109.0),  # still long, no stop hit
        _bar("A", 5, 95.0, 90.0, 92.0),  # crash: stop-out
    ]
    return pd.DataFrame(rows)


def _small_config(**overrides) -> TSMOMConfig:
    base = {
        "donchian_window_hours": 2,
        "atr_period_hours": 2,
        "atr_stop_multiplier": 3.0,
        "cost_bps_roundtrip": 0.0,
    }
    base.update(overrides)
    return TSMOMConfig(**base)


def test_breakout_entry_and_trailing_stop_exit_match_hand_computed_values() -> None:
    bars = _long_entry_then_stop_out_bars()
    config = _small_config()

    trades = run_tsmom_backtest(bars, config)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.status is TradeStatus.RESOLVED
    assert trade.side is TradeSide.LONG
    assert trade.entry_time == 3 * HOUR_MS
    assert trade.entry_price == pytest.approx(104.0)
    assert trade.entry_atr == pytest.approx(2.0)
    assert trade.exit_time == 5 * HOUR_MS
    assert trade.exit_price == pytest.approx(92.0)
    assert trade.gross_return == pytest.approx((92.0 - 104.0) / 104.0)


def test_donchian_channel_never_includes_the_current_bars_own_extreme() -> None:
    """A single, isolated spike at t=2 must not let bar 2 itself "break out"

    against a channel that already contains bar 2's own high.
    """

    rows = [
        _bar("A", 0, 101.0, 99.0, 100.0),
        _bar("A", 1, 101.0, 99.0, 100.0),
        _bar("A", 2, 500.0, 100.0, 500.0),  # extreme bar -- would break out against
        # a channel that (incorrectly) included its own high, but not one
        # correctly built from bars 0-1 only (donchian_high=101 < close=500,
        # so it DOES legitimately break out here -- the real causal check is
        # bar 3, which must not use bar 2's 500 high via a same-bar leak).
        _bar("A", 3, 100.0, 98.0, 99.0),
    ]
    bars = pd.DataFrame(rows)
    config = _small_config()

    trades = run_tsmom_backtest(bars, config)

    # Entry fires at t=2 (close=500 > donchian_high built from bars 0-1 = 101):
    # this is a legitimate breakout using only PRIOR bars, not a same-bar leak.
    assert len(trades) == 1
    assert trades[0].entry_time == 2 * HOUR_MS
    assert trades[0].entry_price == pytest.approx(500.0)


def test_open_position_at_end_is_not_fabricated_as_closed() -> None:
    bars = _long_entry_then_stop_out_bars().iloc[:-1]  # drop the stop-out bar
    config = _small_config()

    trades = run_tsmom_backtest(bars, config)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.status is TradeStatus.OPEN_AT_END
    assert trade.exit_price is None
    assert trade.exit_time is None
    assert trade.gross_return is None
    assert trade.net_return is None

    summary = summarize_tsmom_backtest(trades, config)
    assert summary.resolved_count == 0
    assert summary.open_at_end_count == 1
    assert math.isnan(summary.profit_factor)


def test_cost_is_deducted_only_from_resolved_trades() -> None:
    bars = _long_entry_then_stop_out_bars()
    config = _small_config(cost_bps_roundtrip=12.0)

    trades = run_tsmom_backtest(bars, config)

    trade = trades[0]
    assert trade.net_return == pytest.approx(trade.gross_return - 12.0 / 10_000.0)


def test_duplicate_symbol_open_time_rows_fail_closed() -> None:
    bars = _long_entry_then_stop_out_bars()
    duplicate = pd.DataFrame([_bar("A", 0, 101.0, 99.0, 100.0)])
    bars = pd.concat([bars, duplicate], ignore_index=True)

    with pytest.raises(TSMOMError, match="duplicate"):
        run_tsmom_backtest(bars, _small_config())


def test_missing_required_column_fails_closed() -> None:
    bars = _long_entry_then_stop_out_bars().drop(columns=["low"])

    with pytest.raises(TSMOMError, match="missing required columns"):
        run_tsmom_backtest(bars, _small_config())


def test_invalid_config_fails_closed() -> None:
    with pytest.raises(TSMOMError):
        TSMOMConfig(atr_stop_multiplier=0.0)
    with pytest.raises(TSMOMError):
        TSMOMConfig(min_win_rate=1.5)


def _synthetic_trade(
    net_return: float, gross_return: float, exit_time: int, weight: float = 1.0
) -> TSMOMTrade:
    return TSMOMTrade(
        symbol="A",
        side=TradeSide.LONG,
        status=TradeStatus.RESOLVED,
        entry_time=exit_time - HOUR_MS,
        exit_time=exit_time,
        entry_price=100.0,
        exit_price=100.0 * (1 + gross_return),
        entry_atr=1.0,
        gross_return=gross_return,
        net_return=net_return,
        weight=weight,
    )


def test_summarize_profit_factor_infinite_when_no_losses() -> None:
    trades = (
        _synthetic_trade(net_return=0.01, gross_return=0.01, exit_time=1 * HOUR_MS),
        _synthetic_trade(net_return=0.02, gross_return=0.02, exit_time=2 * HOUR_MS),
    )
    config = _small_config(profit_factor_gate=1.20, min_win_rate=0.30)

    summary = summarize_tsmom_backtest(trades, config)

    assert summary.win_rate == pytest.approx(1.0)
    assert math.isinf(summary.profit_factor)
    assert summary.gate_pass is True


def test_summarize_gate_requires_both_profit_factor_and_win_rate() -> None:
    # 1 big win, 4 small losses: profit factor can be high while win_rate is low.
    trades = (
        _synthetic_trade(net_return=0.50, gross_return=0.50, exit_time=1 * HOUR_MS),
        _synthetic_trade(net_return=-0.01, gross_return=-0.01, exit_time=2 * HOUR_MS),
        _synthetic_trade(net_return=-0.01, gross_return=-0.01, exit_time=3 * HOUR_MS),
        _synthetic_trade(net_return=-0.01, gross_return=-0.01, exit_time=4 * HOUR_MS),
        _synthetic_trade(net_return=-0.01, gross_return=-0.01, exit_time=5 * HOUR_MS),
    )
    config = _small_config(profit_factor_gate=1.20, min_win_rate=0.30)

    summary = summarize_tsmom_backtest(trades, config)

    assert summary.win_rate == pytest.approx(0.20)  # below the 0.30 floor
    assert summary.profit_factor > 1.20  # 0.50 / 0.04 = 12.5, clears the PF bar alone
    assert summary.gate_pass is False  # win_rate floor is the binding constraint


def test_summarize_max_drawdown_tracks_the_cumulative_equity_curve() -> None:
    trades = (
        _synthetic_trade(net_return=0.02, gross_return=0.02, exit_time=1 * HOUR_MS),  # +200bps
        _synthetic_trade(net_return=-0.03, gross_return=-0.03, exit_time=2 * HOUR_MS),  # -300bps
        _synthetic_trade(net_return=0.01, gross_return=0.01, exit_time=3 * HOUR_MS),  # +100bps
    )
    config = _small_config()

    summary = summarize_tsmom_backtest(trades, config)

    # cumulative: 200 -> peak 200 -> -100 (drawdown 300) -> 0 (drawdown 200)
    assert summary.max_drawdown_bps == pytest.approx(300.0)


def test_weighting_is_inverse_to_entry_atr_percentage() -> None:
    """Symbol A is far more volatile (in %) at entry than symbol B and must

    receive a correspondingly smaller portfolio weight.
    """

    rows = [
        _bar("A", 0, 101.0, 99.0, 100.0),
        _bar("A", 1, 101.0, 99.0, 100.0),
        _bar("A", 2, 105.0, 103.0, 104.0),
        _bar("A", 3, 110.0, 108.0, 109.0),
        _bar("A", 4, 95.0, 90.0, 92.0),
        _bar("B", 0, 1001.0, 999.0, 1000.0),
        _bar("B", 1, 1001.0, 999.0, 1000.0),
        _bar("B", 2, 1005.0, 1003.0, 1004.0),
        _bar("B", 3, 1010.0, 1008.0, 1009.0),
        _bar("B", 4, 995.0, 990.0, 992.0),
    ]
    bars = pd.DataFrame(rows)
    config = _small_config()

    trades = run_tsmom_backtest(bars, config)
    resolved = [t for t in trades if t.status is TradeStatus.RESOLVED]
    assert len(resolved) == 2
    by_symbol = {t.symbol: t for t in resolved}
    atr_pct_a = by_symbol["A"].entry_atr / by_symbol["A"].entry_price
    atr_pct_b = by_symbol["B"].entry_atr / by_symbol["B"].entry_price
    assert atr_pct_a > atr_pct_b  # A is the more volatile symbol in this fixture
    assert by_symbol["A"].weight < by_symbol["B"].weight  # so it must get less weight
    # weights should be inversely proportional to atr_pct, normalized to mean 1.0
    ratio = by_symbol["A"].weight / by_symbol["B"].weight
    expected_ratio = atr_pct_b / atr_pct_a
    assert ratio == pytest.approx(expected_ratio, rel=1e-6)


def test_trade_is_frozen_and_replace_preserves_other_fields() -> None:
    trade = _synthetic_trade(net_return=0.01, gross_return=0.01, exit_time=1 * HOUR_MS, weight=1.0)
    updated = replace(trade, weight=2.0)
    assert updated.weight == 2.0
    assert updated.net_return == trade.net_return
    with pytest.raises(AttributeError):  # frozen dataclass
        trade.weight = 5.0  # type: ignore[misc]
