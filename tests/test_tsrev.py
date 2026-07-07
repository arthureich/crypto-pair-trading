from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsrev import (  # noqa: E402
    CrossSectionalReversalConfig,
    TimeSeriesReversalConfig,
    TradeSide,
    TradeStatus,
    TSREVError,
    TSREVTrade,
    buy_and_hold_max_drawdown_bps,
    run_cross_sectional_reversal_backtest,
    run_time_series_reversal_backtest,
    split_out_of_sample,
    summarize_time_series_reversal,
)

HOUR_MS = 60 * 60 * 1000


def _row(symbol: str, t: int, log_price: float) -> dict:
    return {"symbol": symbol, "open_time": t * HOUR_MS, "log_price": log_price}


def _hand_computed_bars() -> pd.DataFrame:
    """Hand-computed fixture: LONG entry at t=4 (sigma_h=0.03 exactly),

    exit at t=6 (gross_return=0.05). See conversation/derivation for the
    exact arithmetic: hourly returns [.,.01,.01,-.02,-.10,.02,.03] give
    sigma_hourly[4]=sqrt(0.00045), sigma_h[4]=sigma_hourly[4]*sqrt(2)=0.03
    exactly, z[4]=-0.12/0.03=-4.0.
    """

    log_prices = [0.00, 0.01, 0.02, 0.00, -0.10, -0.08, -0.05]
    return pd.DataFrame([_row("A", t, p) for t, p in enumerate(log_prices)])


def _small_ts_config(**overrides) -> TimeSeriesReversalConfig:
    base = {
        "horizon_hours": 2,
        "vol_lookback_hours": 2,
        "zscore_threshold": 1.0,
        "cost_bps_roundtrip": 6.0,
    }
    base.update(overrides)
    return TimeSeriesReversalConfig(**base)


def test_entry_and_exit_match_hand_computed_values() -> None:
    bars = _hand_computed_bars()
    config = _small_ts_config()

    trades = run_time_series_reversal_backtest(bars, config)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.status is TradeStatus.RESOLVED
    assert trade.side is TradeSide.LONG
    assert trade.entry_time == 4 * HOUR_MS
    assert trade.entry_log_price == pytest.approx(-0.10)
    assert trade.entry_sigma_h == pytest.approx(0.03, rel=1e-6)
    assert trade.exit_time == 6 * HOUR_MS
    assert trade.exit_log_price == pytest.approx(-0.05)
    assert trade.gross_return == pytest.approx(0.05)
    assert trade.net_return == pytest.approx(0.05 - 6.0 / 10_000.0)


def test_sigma_excludes_the_current_bars_own_hourly_return() -> None:
    """sigma_h[3] is exactly zero here (two identical prior returns), and

    the module must treat a zero sigma as "no signal" (NaN), not a
    division-by-zero crash or a fabricated infinite z-score.
    """

    bars = _hand_computed_bars()
    config = _small_ts_config()

    # no exception, and no trade entered at t=3 (the zero-sigma bar)
    trades = run_time_series_reversal_backtest(bars, config)
    assert all(t.entry_time != 3 * HOUR_MS for t in trades)


def test_open_position_at_end_is_not_fabricated_as_closed() -> None:
    bars = _hand_computed_bars().iloc[:-1]  # drop the exit bar (t=6)
    config = _small_ts_config()

    trades = run_time_series_reversal_backtest(bars, config)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.status is TradeStatus.OPEN_AT_END
    assert trade.exit_log_price is None
    assert trade.gross_return is None

    summary = summarize_time_series_reversal(trades, config)
    assert summary.resolved_count == 0
    assert summary.open_at_end_count == 1
    assert math.isnan(summary.profit_factor)


def test_weighting_is_inverse_to_entry_sigma() -> None:
    bars_a = _hand_computed_bars()
    bars_b = bars_a.copy()
    bars_b["symbol"] = "B"
    # scale symbol B's moves down so its entry sigma is smaller than A's
    bars_b["log_price"] = bars_b["log_price"] * 0.5
    bars = pd.concat([bars_a, bars_b], ignore_index=True)
    config = _small_ts_config()

    trades = run_time_series_reversal_backtest(bars, config)
    resolved = {t.symbol: t for t in trades if t.status is TradeStatus.RESOLVED}
    assert set(resolved) == {"A", "B"}
    assert resolved["B"].entry_sigma_h < resolved["A"].entry_sigma_h
    assert resolved["B"].weight > resolved["A"].weight


def test_duplicate_symbol_open_time_rows_fail_closed() -> None:
    bars = _hand_computed_bars()
    duplicate = pd.DataFrame([_row("A", 0, 0.0)])
    bars = pd.concat([bars, duplicate], ignore_index=True)

    with pytest.raises(TSREVError, match="duplicate"):
        run_time_series_reversal_backtest(bars, _small_ts_config())


def test_missing_required_column_fails_closed() -> None:
    bars = _hand_computed_bars().drop(columns=["log_price"])

    with pytest.raises(TSREVError, match="missing required columns"):
        run_time_series_reversal_backtest(bars, _small_ts_config())


def test_invalid_config_fails_closed() -> None:
    with pytest.raises(TSREVError):
        TimeSeriesReversalConfig(horizon_hours=24, zscore_threshold=0.0)
    with pytest.raises(TSREVError):
        TimeSeriesReversalConfig(horizon_hours=0)


def _synthetic_trade(net_return: float, gross_return: float, exit_time: int) -> TSREVTrade:
    return TSREVTrade(
        symbol="A",
        side=TradeSide.LONG,
        status=TradeStatus.RESOLVED,
        entry_time=exit_time - HOUR_MS,
        exit_time=exit_time,
        entry_log_price=0.0,
        exit_log_price=gross_return,
        entry_sigma_h=1.0,
        gross_return=gross_return,
        net_return=net_return,
        weight=1.0,
    )


def test_gate_requires_all_four_conditions_simultaneously() -> None:
    # a loss (-100bps) followed by a bigger win (+300bps): real drawdown of
    # 100bps exists before the win recovers it.
    trades = (
        _synthetic_trade(net_return=-0.01, gross_return=-0.01, exit_time=1 * HOUR_MS),
        _synthetic_trade(net_return=0.03, gross_return=0.03, exit_time=2 * HOUR_MS),
    )
    config = _small_ts_config(profit_factor_gate=1.05, min_trades_for_gate=1)

    # baseline stricter than the actual 100bps drawdown -> must fail.
    summary_fails_on_drawdown = summarize_time_series_reversal(
        trades, config, baseline_max_drawdown_bps=50.0
    )
    assert summary_fails_on_drawdown.max_drawdown_bps == pytest.approx(100.0)
    assert summary_fails_on_drawdown.gate_pass is False

    # baseline looser than the actual drawdown, and PF (300/100=3.0) and
    # net_pnl (+200bps) both clear their bars -> gate passes.
    summary_passes = summarize_time_series_reversal(
        trades, config, baseline_max_drawdown_bps=1_000.0
    )
    assert summary_passes.gate_pass is True

    strict_count_config = _small_ts_config(profit_factor_gate=1.05, min_trades_for_gate=3)
    summary_fails_on_count = summarize_time_series_reversal(
        trades, strict_count_config, baseline_max_drawdown_bps=1_000.0
    )
    assert summary_fails_on_count.gate_pass is False


def test_split_out_of_sample_partitions_by_open_time() -> None:
    bars = _hand_computed_bars()
    in_sample, out_of_sample = split_out_of_sample(bars, oos_start_ms=4 * HOUR_MS)

    assert set(in_sample["open_time"]) == {0, HOUR_MS, 2 * HOUR_MS, 3 * HOUR_MS}
    assert set(out_of_sample["open_time"]) == {4 * HOUR_MS, 5 * HOUR_MS, 6 * HOUR_MS}


def test_buy_and_hold_max_drawdown_hand_computed() -> None:
    # equal-weight book of A and B; mean hourly return path: +0.02,-0.03,+0.01
    wide = pd.DataFrame(
        {"A": [0.0, 0.03, 0.00, 0.02], "B": [0.0, 0.01, -0.06, 0.00]},
        index=[0, 1, 2, 3],
    )
    # mean per step: t0->t1: (0.03+0.01)/2=0.02; t1->t2: (-0.03-0.07)/2=-0.05;
    # t2->t3: (0.02+0.06)/2=0.04
    # cumulative: 0, 0.02, -0.03, 0.01 -> peak 0.02, trough -0.03 -> dd=0.05 -> 500bps
    dd = buy_and_hold_max_drawdown_bps(wide)
    assert dd == pytest.approx(500.0, rel=1e-6)


def _cross_sectional_bars() -> pd.DataFrame:
    """4 symbols, decile_k=1, 9 bars -- enough warm-up (sigma needs >=3

    prior bars with horizon=2/lookback=2) plus room for a forward exit.
    E and F are flat for the entire series (zero variance -> sigma
    replaced by NaN -> permanently ineligible), isolating the ranking
    test to C and D.
    """

    data = {
        "C": [0.0, -0.02, -0.01, 0.05, 0.06, 0.02, 0.02, 0.02, 0.02],
        "D": [0.0, 0.02, 0.01, -0.01, -0.02, 0.00, 0.00, 0.00, 0.00],
        "E": [0.0] * 9,
        "F": [0.0] * 9,
    }
    rows = [_row(symbol, t, p) for symbol, prices in data.items() for t, p in enumerate(prices)]
    return pd.DataFrame(rows)


def test_cross_sectional_reversal_ranks_and_trades_dollar_neutral() -> None:
    bars = _cross_sectional_bars()
    config = CrossSectionalReversalConfig(
        horizon_hours=2, vol_lookback_hours=2, decile_k=1, cost_bps_roundtrip=0.0
    )

    results = run_cross_sectional_reversal_backtest(bars, config)

    resolved = [r for r in results if r.status is TradeStatus.RESOLVED]
    assert len(resolved) >= 1
    # E and F have zero variance throughout -> sigma is always NaN -> must
    # never be eligible for ranking in any resolved rebalance.
    for r in resolved:
        assert "E" not in r.long_symbols + r.short_symbols
        assert "F" not in r.long_symbols + r.short_symbols

    first = resolved[0]
    # At the first well-defined rebalance (position 4): D fell relative to
    # its own history (z=-3.0) -> LONG; C rose (z=+1.4) -> SHORT.
    assert first.long_symbols == ("D",)
    assert first.short_symbols == ("C",)


def test_cross_sectional_k_larger_than_half_universe_fails_closed() -> None:
    bars = _cross_sectional_bars()
    config = CrossSectionalReversalConfig(horizon_hours=2, decile_k=3)

    with pytest.raises(TSREVError, match="requires 2\\*decile_k"):
        run_cross_sectional_reversal_backtest(bars, config)
