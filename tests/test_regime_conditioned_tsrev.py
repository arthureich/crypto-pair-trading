"""Tests for scripts/run_regime_conditioned_tsrev.py (TASK-ALT-004)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_regime_conditioned_tsrev import (  # noqa: E402
    HOUR_MS,
    RegimeConditioningError,
    build_high_vol_regime_filter,
    filter_trades_by_regime,
    renormalize_tsrev_trade_weights,
)
from src.research.tsrev import TradeSide, TradeStatus, TSREVTrade  # noqa: E402


def _bars_from_returns(returns: list[float], symbol: str = "A") -> pd.DataFrame:
    prices = [0.0]
    for value in returns:
        prices.append(prices[-1] + value)
    return pd.DataFrame(
        {
            "symbol": [symbol] * len(prices),
            "open_time": [i * HOUR_MS for i in range(len(prices))],
            "log_price": prices,
        }
    )


def _trade(symbol: str, entry_hour: int, sigma: float, status: TradeStatus) -> TSREVTrade:
    return TSREVTrade(
        symbol=symbol,
        side=TradeSide.LONG,
        status=status,
        entry_time=entry_hour * HOUR_MS,
        exit_time=(entry_hour + 1) * HOUR_MS if status is TradeStatus.RESOLVED else None,
        entry_log_price=0.0,
        exit_log_price=0.01 if status is TradeStatus.RESOLVED else None,
        entry_sigma_h=sigma,
        gross_return=0.01 if status is TradeStatus.RESOLVED else None,
        net_return=0.0094 if status is TradeStatus.RESOLVED else None,
        weight=99.0,
    )


def test_missing_regime_history_fails_closed() -> None:
    bars = _bars_from_returns([0.01] * 10)

    allow_entry, _, _ = build_high_vol_regime_filter(
        bars, realized_vol_window_hours=3, quantile_lookback_hours=5
    )

    assert not allow_entry.iloc[:7].any().any()


def test_high_volatility_above_prior_quantile_blocks_entry() -> None:
    returns = [0.01, -0.01] * 8 + [0.20, -0.20, 0.20, -0.20]
    bars = _bars_from_returns(returns)

    allow_entry, realized_vol, threshold = build_high_vol_regime_filter(
        bars,
        realized_vol_window_hours=3,
        quantile_lookback_hours=5,
        high_vol_quantile=0.67,
    )

    blocked_time = 19 * HOUR_MS
    assert realized_vol.at[blocked_time, "A"] > threshold.at[blocked_time, "A"]
    assert bool(allow_entry.at[blocked_time, "A"]) is False


def test_future_price_mutation_does_not_change_current_regime_filter() -> None:
    returns = [0.01, -0.01, 0.02, -0.02] * 20
    baseline = _bars_from_returns(returns)
    mutated = baseline.copy()
    check_time = 40 * HOUR_MS
    mutated.loc[mutated["open_time"] > check_time, "log_price"] += 100.0

    baseline_allow, _, _ = build_high_vol_regime_filter(
        baseline, realized_vol_window_hours=4, quantile_lookback_hours=8
    )
    mutated_allow, _, _ = build_high_vol_regime_filter(
        mutated, realized_vol_window_hours=4, quantile_lookback_hours=8
    )

    assert bool(baseline_allow.at[check_time, "A"]) == bool(mutated_allow.at[check_time, "A"])


def test_filter_trades_by_regime_keeps_only_explicit_true_entries() -> None:
    allow_entry = pd.DataFrame(
        {"A": [True, False], "B": [False, True]},
        index=[10 * HOUR_MS, 20 * HOUR_MS],
    )
    trades = (
        _trade("A", 10, 1.0, TradeStatus.RESOLVED),
        _trade("A", 20, 1.0, TradeStatus.RESOLVED),
        _trade("B", 20, 1.0, TradeStatus.RESOLVED),
        _trade("C", 10, 1.0, TradeStatus.RESOLVED),
    )

    kept = filter_trades_by_regime(trades, allow_entry)

    assert [(trade.symbol, trade.entry_time) for trade in kept] == [
        ("A", 10 * HOUR_MS),
        ("B", 20 * HOUR_MS),
    ]


def test_renormalize_weights_after_filtering_uses_inverse_sigma() -> None:
    trades = (
        _trade("A", 1, 1.0, TradeStatus.RESOLVED),
        _trade("B", 1, 2.0, TradeStatus.RESOLVED),
        _trade("C", 1, 1.0, TradeStatus.OPEN_AT_END),
    )

    normalized = renormalize_tsrev_trade_weights(trades)
    by_symbol = {trade.symbol: trade for trade in normalized}

    assert by_symbol["A"].weight == pytest.approx(1.0 / 0.75)
    assert by_symbol["B"].weight == pytest.approx(0.5 / 0.75)
    assert by_symbol["C"].weight == 0.0
    assert math.isclose((by_symbol["A"].weight + by_symbol["B"].weight) / 2.0, 1.0)


def test_invalid_filter_inputs_fail_closed() -> None:
    bars = _bars_from_returns([0.01] * 10)
    with pytest.raises(RegimeConditioningError, match="missing required columns"):
        build_high_vol_regime_filter(bars.drop(columns=["log_price"]))
    duplicated = pd.concat([bars, bars.iloc[[0]]], ignore_index=True)
    with pytest.raises(RegimeConditioningError, match="duplicate"):
        build_high_vol_regime_filter(duplicated)
    with pytest.raises(RegimeConditioningError, match="high_vol_quantile"):
        build_high_vol_regime_filter(bars, high_vol_quantile=1.0)
