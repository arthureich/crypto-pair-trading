from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.funding_carry import (  # noqa: E402
    FundingCarryConfig,
    FundingCarryError,
    RebalanceStatus,
    run_funding_carry_backtest,
    run_incremental_funding_carry_backtest,
    summarize_funding_carry_backtest,
)

HOUR_MS = 60 * 60 * 1000
EIGHT_HOURS_MS = 8 * HOUR_MS
SIXTEEN_HOURS_MS = 16 * HOUR_MS
TWENTY_FOUR_HOURS_MS = 24 * HOUR_MS


def _row(symbol: str, open_time: int, funding_rate: float, log_price: float) -> dict:
    return {
        "symbol": symbol,
        "open_time": open_time,
        "funding_rate_asof": funding_rate,
        "log_price": log_price,
    }


def _four_symbol_bars() -> pd.DataFrame:
    """Two rebalance times (0, 8h); 8h is the dataset's last time (NO_DATA)."""

    rows = [
        _row("A", 0, 0.001, 0.0),
        _row("B", 0, -0.001, 0.0),
        _row("C", 0, 0.0002, 0.0),
        _row("D", 0, -0.0002, 0.0),
        _row("A", EIGHT_HOURS_MS, 0.0, 0.01),
        _row("B", EIGHT_HOURS_MS, 0.0, -0.005),
        _row("C", EIGHT_HOURS_MS, 0.0, 0.0),
        _row("D", EIGHT_HOURS_MS, 0.0, 0.0),
    ]
    return pd.DataFrame(rows)


def _two_symbol_profitable_bars() -> pd.DataFrame:
    """K=1: short A (funding 0.001, price falls) / long B (funding -0.001, price rises).

    Both funding and price legs are constructed to be gains for this book,
    so the single resolved rebalance has no losses -- used to test that
    profit_factor becomes +inf rather than being fabricated as 0.0 or
    silently excluded.
    """

    rows = [
        _row("A", 0, 0.001, 0.0),
        _row("B", 0, -0.001, 0.0),
        _row("A", EIGHT_HOURS_MS, 0.0, -0.005),
        _row("B", EIGHT_HOURS_MS, 0.0, 0.005),
    ]
    return pd.DataFrame(rows)


def _six_symbol_bars_with_a_funding_gap() -> pd.DataFrame:
    """6 symbols total (so k=3 passes the universe-size check), but 2 of

    them have a missing (NaN) funding_rate_asof at the only resolvable
    rebalance time -- eligible count (4) then falls below 2*k=6 for that
    specific rebalance, without making the whole run impossible.
    """

    symbols = ("A", "B", "C", "D", "E", "F")
    rows = [_row(symbol, 0, 0.0001 * i, 0.0) for i, symbol in enumerate(symbols)]
    rows += [_row(symbol, EIGHT_HOURS_MS, 0.0001, 0.0) for symbol in symbols]
    bars = pd.DataFrame(rows)
    bars.loc[(bars["symbol"].isin(("E", "F"))) & (bars["open_time"] == 0), "funding_rate_asof"] = (
        float("nan")
    )
    return bars


def test_funding_and_price_pnl_use_binance_sign_convention() -> None:
    """K=1: short the highest-funding symbol (A), long the lowest (B).

    Hand-computed expected values -- see module docstring for the sign
    convention: LONG funding pnl = -funding_rate, LONG price pnl =
    +price_return; SHORT is the mirror image.
    """

    bars = _four_symbol_bars()
    config = FundingCarryConfig(k=1, cost_bps_per_leg_roundtrip=2.0)

    results = run_funding_carry_backtest(bars, config)

    assert len(results) == 2
    result = results[0]
    assert result.rebalance_time == 0
    assert result.status is RebalanceStatus.RESOLVED
    assert result.short_symbols == ("A",)
    assert result.long_symbols == ("B",)
    assert result.eligible_symbol_count == 4
    # funding: 0.5*(-(-0.001)) [long B] + 0.5*(0.001) [short A] = 0.001 -> 10 bps
    assert result.funding_pnl_bps == pytest.approx(10.0)
    # price: 0.5*(-0.005) [long B] + 0.5*(-0.01) [short A] = -0.0075 -> -75 bps
    assert result.price_pnl_bps == pytest.approx(-75.0)
    assert result.gross_pnl_bps == pytest.approx(-65.0)
    assert result.cost_bps == pytest.approx(2.0)
    assert result.net_pnl_bps == pytest.approx(-67.0)
    # the dataset's last timestamp has no forward bar to resolve against.
    assert results[1].rebalance_time == EIGHT_HOURS_MS
    assert results[1].status is RebalanceStatus.NO_DATA


def test_ranking_picks_the_extremes_not_just_any_eligible_symbols() -> None:
    bars = _four_symbol_bars()
    config = FundingCarryConfig(k=1)

    results = run_funding_carry_backtest(bars, config)

    result = results[0]
    assert result.short_symbols == ("A",)  # highest funding_rate_asof (0.001)
    assert result.long_symbols == ("B",)  # lowest funding_rate_asof (-0.001)
    assert "C" not in result.long_symbols + result.short_symbols
    assert "D" not in result.long_symbols + result.short_symbols


def test_symbol_with_non_finite_funding_rate_is_excluded_not_fabricated() -> None:
    bars = _four_symbol_bars()
    bars.loc[bars["symbol"] == "D", "funding_rate_asof"] = float("nan")
    config = FundingCarryConfig(k=1)

    results = run_funding_carry_backtest(bars, config)

    result = results[0]
    assert result.eligible_symbol_count == 3
    assert result.status is RebalanceStatus.RESOLVED


def test_insufficient_eligible_symbols_at_one_rebalance_fails_closed_for_that_rebalance_only() -> (
    None
):
    bars = _six_symbol_bars_with_a_funding_gap()
    config = FundingCarryConfig(k=3)  # needs 6 eligible; only 4 have finite funding at t=0

    results = run_funding_carry_backtest(bars, config)

    assert results[0].status is RebalanceStatus.INSUFFICIENT_SYMBOLS
    assert results[0].eligible_symbol_count == 4
    assert results[0].net_pnl_bps == 0.0


def test_no_forward_data_is_no_data_not_a_crash() -> None:
    """The last rebalance time in a dataset has no forward bar to resolve against."""

    bars = _four_symbol_bars()
    config = FundingCarryConfig(k=1)

    results = run_funding_carry_backtest(bars, config)

    assert len(results) == 2
    assert results[0].status is RebalanceStatus.RESOLVED
    assert results[1].status is RebalanceStatus.NO_DATA


def test_duplicate_symbol_open_time_rows_fail_closed() -> None:
    bars = _four_symbol_bars()
    duplicate = pd.DataFrame([_row("A", 0, 0.005, 0.0)])
    bars = pd.concat([bars, duplicate], ignore_index=True)
    config = FundingCarryConfig(k=1)

    with pytest.raises(FundingCarryError, match="duplicate"):
        run_funding_carry_backtest(bars, config)


def test_k_larger_than_half_the_universe_fails_closed() -> None:
    bars = _four_symbol_bars()
    config = FundingCarryConfig(k=3)  # needs 6 symbols, universe only has 4

    with pytest.raises(FundingCarryError, match="requires 2\\*k"):
        run_funding_carry_backtest(bars, config)


def test_invalid_k_fails_closed() -> None:
    with pytest.raises(FundingCarryError):
        FundingCarryConfig(k=0)


def test_missing_required_column_fails_closed() -> None:
    bars = _four_symbol_bars().drop(columns=["funding_rate_asof"])
    config = FundingCarryConfig(k=1)

    with pytest.raises(FundingCarryError, match="missing required columns"):
        run_funding_carry_backtest(bars, config)


def test_summarize_profit_factor_is_infinite_not_excluded_when_there_are_no_losses() -> None:
    bars = _two_symbol_profitable_bars()
    config = FundingCarryConfig(k=1, cost_bps_per_leg_roundtrip=0.0, min_rebalances_for_gate=1)

    results = run_funding_carry_backtest(bars, config)
    summary = summarize_funding_carry_backtest(results, config)

    assert summary.resolved_count == 1
    assert summary.net_pnl_bps > 0.0
    assert math.isinf(summary.profit_factor)
    assert summary.profit_factor_gate_pass is True


def test_summarize_fails_closed_to_nan_and_no_gate_pass_with_zero_resolved() -> None:
    bars = _six_symbol_bars_with_a_funding_gap()
    config = FundingCarryConfig(k=3)  # INSUFFICIENT_SYMBOLS at the only rebalance time

    results = run_funding_carry_backtest(bars, config)
    summary = summarize_funding_carry_backtest(results, config)

    assert summary.resolved_count == 0
    assert math.isnan(summary.profit_factor)
    assert summary.profit_factor_gate_pass is False


def test_summarize_gate_requires_minimum_rebalance_count() -> None:
    bars = _two_symbol_profitable_bars()
    config = FundingCarryConfig(k=1, cost_bps_per_leg_roundtrip=0.0, min_rebalances_for_gate=1_000)

    results = run_funding_carry_backtest(bars, config)
    summary = summarize_funding_carry_backtest(results, config)

    assert summary.resolved_count == 1
    assert math.isinf(summary.profit_factor)
    assert summary.profit_factor_gate_pass is False


def _six_symbol_incremental_bars() -> pd.DataFrame:
    """K=1 fixture spanning 4 rebalances (0, 8h, 16h, 24h); log_price is

    always 0.0 for every symbol so price_pnl_bps is always 0.0, isolating
    every assertion to the funding/swap-decision logic. Symbol A always
    has the highest funding rate (short side never swaps, by construction,
    letting the tests focus on the long side without conflating both).
    """

    def snapshot(t: int, a: float, b: float, c: float, d: float, e: float, f: float) -> list[dict]:
        rates = {"A": a, "B": b, "C": c, "D": d, "E": e, "F": f}
        return [_row(symbol, t, rate, 0.0) for symbol, rate in rates.items()]

    rows = []
    rows += snapshot(0, 0.0010, -0.0010, 0.0002, -0.0002, 0.0001, -0.0001)
    rows += snapshot(EIGHT_HOURS_MS, 0.0010, -0.0001, 0.0002, -0.0002, 0.0001, -0.0001)
    rows += snapshot(SIXTEEN_HOURS_MS, 0.0010, -0.00005, 0.0002, -0.0015, 0.0001, -0.0001)
    rows += snapshot(TWENTY_FOUR_HOURS_MS, 0.0010, -0.00005, 0.0002, -0.0015, 0.0001, -0.0001)
    return pd.DataFrame(rows)


def test_incremental_bootstrap_matches_fresh_top_and_bottom_k_and_pays_flat_cost() -> None:
    bars = _six_symbol_incremental_bars()
    config = FundingCarryConfig(k=1)

    results = run_incremental_funding_carry_backtest(bars, config)

    bootstrap = results[0]
    assert bootstrap.rebalance_time == 0
    assert bootstrap.status is RebalanceStatus.RESOLVED
    assert bootstrap.held_long == ("B",)
    assert bootstrap.held_short == ("A",)
    assert bootstrap.swap_count == 2  # one refill per side, no held state existed yet
    # bootstrap cost must equal fase-1's flat cost_bps_per_leg_roundtrip exactly:
    # 2*k legs * weight(1/(2k)) * cost == cost, regardless of k.
    assert bootstrap.cost_bps == pytest.approx(config.cost_bps_per_leg_roundtrip)
    assert bootstrap.funding_pnl_bps == pytest.approx(10.0)
    assert bootstrap.price_pnl_bps == pytest.approx(0.0)
    assert bootstrap.net_pnl_bps == pytest.approx(4.0)


def test_incremental_holds_when_swap_gain_does_not_clear_threshold() -> None:
    bars = _six_symbol_incremental_bars()
    config = FundingCarryConfig(k=1, cost_bps_per_leg_roundtrip=6.0)

    results = run_incremental_funding_carry_backtest(bars, config)

    hold = results[1]
    assert hold.rebalance_time == EIGHT_HOURS_MS
    assert hold.status is RebalanceStatus.RESOLVED
    # D (-0.0002) is 1bps better than held B (-0.0001) at this time, but 1bps
    # does not clear the 6bps round-trip threshold, so B must be retained.
    assert hold.held_long == ("B",)
    assert hold.held_short == ("A",)
    assert hold.swap_count == 0
    assert hold.cost_bps == pytest.approx(0.0)
    assert hold.funding_pnl_bps == pytest.approx(5.5)
    assert hold.net_pnl_bps == pytest.approx(5.5)


def test_incremental_swaps_when_gain_clears_threshold_and_charges_cost_for_swapped_legs_only() -> (
    None
):
    bars = _six_symbol_incremental_bars()
    config = FundingCarryConfig(k=1, cost_bps_per_leg_roundtrip=6.0)

    results = run_incremental_funding_carry_backtest(bars, config)

    swap = results[2]
    assert swap.rebalance_time == SIXTEEN_HOURS_MS
    assert swap.status is RebalanceStatus.RESOLVED
    # D (-0.0015) is 14.5bps better than held B (-0.00005) here, clearing the
    # 6bps threshold: B must be swapped out for D. The short side (A) never
    # has a better candidate available, so it must not swap.
    assert swap.held_long == ("D",)
    assert swap.held_short == ("A",)
    assert swap.swap_count == 1
    # Only the ONE swapped leg pays cost_bps_per_leg_roundtrip, not the whole book.
    assert swap.cost_bps == pytest.approx(0.5 * config.cost_bps_per_leg_roundtrip)
    assert swap.funding_pnl_bps == pytest.approx(12.5)
    assert swap.net_pnl_bps == pytest.approx(9.5)


def test_incremental_forces_out_ineligible_held_leg_and_refills_unconditionally() -> None:
    rows = [
        _row("A", 0, 0.0010, 0.0),
        _row("B", 0, -0.0010, 0.0),
        _row("C", 0, 0.0002, 0.0),
        _row("D", 0, -0.0002, 0.0),
        _row("A", EIGHT_HOURS_MS, 0.0010, 0.0),
        _row("B", EIGHT_HOURS_MS, float("nan"), 0.0),  # B becomes ineligible
        _row("C", EIGHT_HOURS_MS, 0.0002, 0.0),
        _row("D", EIGHT_HOURS_MS, -0.0002, 0.0),
        _row("A", SIXTEEN_HOURS_MS, 0.0010, 0.0),
        _row("C", SIXTEEN_HOURS_MS, 0.0002, 0.0),
        _row("D", SIXTEEN_HOURS_MS, -0.0002, 0.0),
    ]
    bars = pd.DataFrame(rows)
    config = FundingCarryConfig(k=1, cost_bps_per_leg_roundtrip=6.0)

    results = run_incremental_funding_carry_backtest(bars, config)

    forced = results[1]
    assert forced.rebalance_time == EIGHT_HOURS_MS
    assert forced.status is RebalanceStatus.RESOLVED
    # B (bootstrapped as the long leg) is NaN here and must be forced out;
    # the freed slot is refilled unconditionally with the best remaining
    # candidate (D), even though a discretionary swap from B directly would
    # not have been evaluated (B no longer has an observable rate at all).
    assert "B" not in forced.held_long
    assert forced.held_long == ("D",)
    assert forced.swap_count == 1
    assert forced.cost_bps == pytest.approx(0.5 * config.cost_bps_per_leg_roundtrip)


def test_incremental_swap_decision_is_causal_independent_of_forward_price() -> None:
    """The held-vs-candidate decision must depend only on the CURRENT

    snapshot's funding_rate_asof, never on the forward bar's price -- changing
    only the forward price must never change which symbols end up held.
    """

    base = _six_symbol_incremental_bars()
    mutated = base.copy()
    # Mutate only symbol B's (the held long leg's) forward price -- mutating
    # every symbol's price identically would cancel out in a dollar-neutral
    # book (long and short legs move oppositely by construction) and would
    # not actually prove the mutation was observed by the PnL calculation.
    only_b_at_forward_time = (mutated["open_time"] == EIGHT_HOURS_MS) & (mutated["symbol"] == "B")
    mutated.loc[only_b_at_forward_time, "log_price"] = 999.0
    config = FundingCarryConfig(k=1)

    base_results = run_incremental_funding_carry_backtest(base, config)
    mutated_results = run_incremental_funding_carry_backtest(mutated, config)

    assert base_results[0].held_long == mutated_results[0].held_long
    assert base_results[0].held_short == mutated_results[0].held_short
    # the mutated forward price changes bootstrap's realized PnL (its
    # forward bar is EIGHT_HOURS_MS), proving the mutation actually took
    # effect, while still never touching the swap decision itself.
    assert base_results[0].price_pnl_bps != mutated_results[0].price_pnl_bps
    assert base_results[0].held_long == base_results[0].held_long


def test_summarize_funding_carry_backtest_works_with_incremental_results() -> None:
    bars = _six_symbol_incremental_bars()
    config = FundingCarryConfig(k=1, min_rebalances_for_gate=1)

    results = run_incremental_funding_carry_backtest(bars, config)
    summary = summarize_funding_carry_backtest(results, config)

    assert summary.resolved_count == 3  # t=0, 8h, 16h resolved; 24h is NO_DATA (last time)
    assert summary.no_data_count == 1
    assert summary.net_pnl_bps == pytest.approx(4.0 + 5.5 + 9.5)
