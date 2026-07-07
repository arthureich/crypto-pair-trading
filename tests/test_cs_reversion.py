"""Tests for src/research/cs_reversion.py (TASK-CS-002)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.research.cs_momentum import (
    CrossSectionalMomentumConfig,
    run_cross_sectional_momentum_backtest,
)
from src.research.cs_reversion import (
    CrossSectionalReversionConfig,
    CrossSectionalReversionError,
    ReversionLegTrade,
    TradeSide,
    TradeStatus,
    run_cross_sectional_reversion_backtest,
    summarize_cross_sectional_reversion,
)

HOUR_MS = 3_600_000


def _hand_computed_bars() -> pd.DataFrame:
    # Same fixture as test_cs_momentum.py: 4 symbols, 6 hourly bars,
    # formation_hours=2, quintile_k=1. A stood out as the winner and D as
    # the loser by raw formation return at t=2 and t=4.
    log_prices = {
        "A": [0.00, 0.01, 0.05, 0.06, 0.09, 0.10],
        "B": [0.00, -0.01, -0.03, -0.02, -0.01, 0.00],
        "C": [0.00, 0.02, 0.02, 0.03, 0.03, 0.04],
        "D": [0.00, -0.02, -0.06, -0.07, -0.10, -0.11],
    }
    rows = []
    for symbol, prices in log_prices.items():
        for t, price in enumerate(prices):
            rows.append({"symbol": symbol, "open_time": t * HOUR_MS, "log_price": price})
    return pd.DataFrame(rows)


def _config(**overrides) -> CrossSectionalReversionConfig:
    params = {"formation_hours": 2, "quintile_k": 1, "cost_bps_roundtrip": 6.0}
    params.update(overrides)
    return CrossSectionalReversionConfig(**params)


def test_losers_go_long_and_winners_go_short():
    bars = _hand_computed_bars()
    trades = run_cross_sectional_reversion_backtest(bars, _config())

    resolved = [t for t in trades if t.status is TradeStatus.RESOLVED]
    assert len(resolved) == 2
    by_symbol = {t.symbol: t for t in resolved}
    assert set(by_symbol) == {"A", "D"}
    # Mirror of CS-001: A (highest formation return, winner) is SHORT here;
    # D (lowest formation return, loser) is LONG here.
    assert by_symbol["A"].side is TradeSide.SHORT
    assert by_symbol["D"].side is TradeSide.LONG


def test_hand_computed_gross_return_and_weight():
    bars = _hand_computed_bars()
    trades = run_cross_sectional_reversion_backtest(bars, _config())
    resolved = {t.symbol: t for t in trades if t.status is TradeStatus.RESOLVED}

    # A: SHORT, entry 0.05 -> exit 0.09, gross = entry - exit = -0.04.
    # D: LONG, entry -0.06 -> exit -0.10, gross = exit - entry = -0.04.
    assert resolved["A"].gross_return == pytest.approx(-0.04)
    assert resolved["D"].gross_return == pytest.approx(-0.04)
    assert resolved["A"].weight == pytest.approx(0.5)
    assert resolved["D"].weight == pytest.approx(0.5)
    expected_net = -0.04 - 6.0 / 10_000.0
    assert resolved["A"].net_return == pytest.approx(expected_net)
    assert resolved["D"].net_return == pytest.approx(expected_net)


def test_mirrors_cs_momentum_gross_pnl_exactly():
    """Sanity check for the ADR-0018 mirror-image identity: at the SAME
    horizon/ranking, reversion's gross return is the exact negative of
    momentum's, because only the LONG/SHORT side assignment differs.
    """

    bars = _hand_computed_bars()
    momentum_config = CrossSectionalMomentumConfig(
        formation_hours=2, quintile_k=1, cost_bps_roundtrip=6.0
    )
    momentum_trades = run_cross_sectional_momentum_backtest(bars, momentum_config)
    reversion_trades = run_cross_sectional_reversion_backtest(bars, _config())

    momentum_gross = sum(
        t.weight * t.gross_return for t in momentum_trades if t.status is TradeStatus.RESOLVED
    )
    reversion_gross = sum(
        t.weight * t.gross_return for t in reversion_trades if t.status is TradeStatus.RESOLVED
    )
    assert reversion_gross == pytest.approx(-momentum_gross)


def test_open_at_end_not_fabricated():
    bars = _hand_computed_bars()
    trades = run_cross_sectional_reversion_backtest(bars, _config())
    open_at_end = [t for t in trades if t.status is TradeStatus.OPEN_AT_END]

    assert len(open_at_end) == 2
    for trade in open_at_end:
        assert trade.exit_time is None
        assert trade.exit_log_price is None
        assert trade.gross_return is None
        assert trade.net_return is None
        assert trade.weight == 0.0


def test_no_lookahead_future_bars_do_not_affect_earlier_ranking():
    baseline = _hand_computed_bars()
    mutated = baseline.copy()
    future_mask = mutated["open_time"] > 2 * HOUR_MS
    mutated.loc[future_mask, "log_price"] = mutated.loc[future_mask, "log_price"] + 999.0

    baseline_trades = run_cross_sectional_reversion_backtest(baseline, _config())
    mutated_trades = run_cross_sectional_reversion_backtest(mutated, _config())

    baseline_at_2 = {t.symbol: t.side for t in baseline_trades if t.entry_time == 2 * HOUR_MS}
    mutated_at_2 = {t.symbol: t.side for t in mutated_trades if t.entry_time == 2 * HOUR_MS}
    assert baseline_at_2 == mutated_at_2 == {"A": TradeSide.SHORT, "D": TradeSide.LONG}


def test_duplicate_rows_fail_closed():
    bars = _hand_computed_bars()
    duplicated = pd.concat([bars, bars.iloc[[0]]], ignore_index=True)
    with pytest.raises(CrossSectionalReversionError, match="duplicate"):
        run_cross_sectional_reversion_backtest(duplicated, _config())


def test_missing_column_fail_closed():
    bars = _hand_computed_bars().drop(columns=["log_price"])
    with pytest.raises(CrossSectionalReversionError, match="missing required columns"):
        run_cross_sectional_reversion_backtest(bars, _config())


def test_insufficient_symbols_for_quintile_k_fail_closed():
    bars = _hand_computed_bars()
    with pytest.raises(CrossSectionalReversionError, match="quintile_k"):
        run_cross_sectional_reversion_backtest(bars, _config(quintile_k=3))


@pytest.mark.parametrize(
    "overrides",
    [
        {"formation_hours": 0},
        {"quintile_k": 0},
        {"cost_bps_roundtrip": -1.0},
        {"profit_factor_gate": 0.0},
        {"min_trades_for_gate": 0},
    ],
)
def test_invalid_config_fail_closed(overrides):
    with pytest.raises(CrossSectionalReversionError):
        _config(**overrides)


def _synthetic_trade(net_bps: float, exit_time: int) -> ReversionLegTrade:
    net_return = net_bps / 10_000.0
    return ReversionLegTrade(
        symbol="X",
        side=TradeSide.LONG,
        status=TradeStatus.RESOLVED,
        entry_time=exit_time - HOUR_MS,
        exit_time=exit_time,
        entry_log_price=0.0,
        exit_log_price=net_return,
        formation_return=0.0,
        gross_return=net_return,
        net_return=net_return,
        weight=1.0,
    )


def test_gate_requires_all_four_criteria_simultaneously():
    config = _config(profit_factor_gate=1.10, min_trades_for_gate=2)
    net_bps_sequence = (100.0, 100.0, -50.0, 100.0, 100.0)
    winning_trades = tuple(
        _synthetic_trade(bps, (i + 1) * HOUR_MS) for i, bps in enumerate(net_bps_sequence)
    )

    passing = summarize_cross_sectional_reversion(
        winning_trades, config, baseline_max_drawdown_bps=1000.0
    )
    assert passing.gate_pass is True
    assert passing.max_drawdown_bps == pytest.approx(50.0)

    too_few_trades = winning_trades[:1]
    summary = summarize_cross_sectional_reversion(
        too_few_trades, config, baseline_max_drawdown_bps=1000.0
    )
    assert summary.gate_pass is False

    drawdown_exceeds_baseline = summarize_cross_sectional_reversion(
        winning_trades, config, baseline_max_drawdown_bps=10.0
    )
    assert drawdown_exceeds_baseline.gate_pass is False

    weak_pf_trades = (
        _synthetic_trade(100.0, HOUR_MS),
        _synthetic_trade(-95.0, 2 * HOUR_MS),
    )
    weak_pf = summarize_cross_sectional_reversion(
        weak_pf_trades, config, baseline_max_drawdown_bps=1000.0
    )
    assert weak_pf.gate_pass is False


def test_summarize_empty_trades_does_not_pass_gate():
    config = _config()
    summary = summarize_cross_sectional_reversion((), config)
    assert summary.resolved_count == 0
    assert summary.gate_pass is False
    assert math.isnan(summary.profit_factor)
