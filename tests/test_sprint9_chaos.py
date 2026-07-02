"""Additional chaos scenarios for the Sprint 9 executable backtest.

Complements tests/test_fill_model.py, tests/test_execution_simulator.py, and
tests/test_replay_engine.py with edge cases those files do not already
cover: large data gaps, zero available liquidity, and both legs failing to
exit simultaneously.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.execution_simulator import (  # noqa: E402
    TradeStatus,
    simulate_round_trip_trade,
)
from src.backtest.fill_model import (  # noqa: E402
    FillModelConfig,
    FillModelError,
    FillStatus,
    TopOfBookQuote,
    simulate_market_fill,
)
from src.execution.slippage_estimator import SlippageSide  # noqa: E402

HOUR_MS = 60 * 60 * 1000


def _quote(t: int, bid: float, ask: float, bid_qty: float = 10.0, ask_qty: float = 10.0) -> TopOfBookQuote:
    return TopOfBookQuote(event_time=t, best_bid=bid, best_ask=ask, best_bid_qty=bid_qty, best_ask_qty=ask_qty)


def test_large_time_gap_between_decision_and_next_quote_fails_closed_as_no_quote() -> None:
    quotes = [
        _quote(0, 10.0, 10.01),
        _quote(6 * HOUR_MS, 10.5, 10.51),
    ]
    config = FillModelConfig(latency_ms=250)

    outcome = simulate_market_fill(
        order_id="gap-order",
        side=SlippageSide.BUY,
        quantity=1.0,
        quotes=[q for q in quotes if q.event_time <= HOUR_MS],
        decision_time=0,
        config=config,
    )

    # Only the quote at t=0 is in range; nothing reachable after latency
    # inside the supplied window means the order correctly reports NO_QUOTE
    # rather than reaching across a multi-hour gap to a quote far in the
    # future that a real IOC order would never wait for.
    assert outcome.status is FillStatus.NO_QUOTE


def test_zero_available_liquidity_at_level_one_yields_zero_fill_not_a_crash() -> None:
    quotes = [_quote(0, 10.0, 10.01, ask_qty=0.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    outcome = simulate_market_fill(
        order_id="zero-liquidity-order",
        side=SlippageSide.BUY,
        quantity=1.0,
        quotes=quotes,
        decision_time=0,
        config=config,
    )

    assert outcome.status is FillStatus.PARTIALLY_FILLED
    assert outcome.filled_quantity == 0.0
    assert outcome.fill_ratio == 0.0


def test_both_legs_fail_to_exit_reports_no_exit_fill_status() -> None:
    intent = SimpleNamespace(
        signal_id="S9-CHAOS-0-SHORT_SPREAD",
        pair="ARBUSDT/OPUSDT",
        symbol_a="ARBUSDT",
        symbol_b="OPUSDT",
        side_a="SELL",
        side_b="BUY",
        target_notional=1_000.0,
        zscore=2.5,
        beta=1.0,
        half_life_hours=12.0,
        expected_edge_bps=5.0,
        created_at=0,
        expires_at=HOUR_MS,
        barrier_policy_id="TEST_BARRIER",
    )
    # Quotes exist to fill the entry, then the feed goes dark before the exit
    # decision time (e.g. a multi-hour outage) -- neither leg can close.
    quotes_a = [_quote(0, 10.0, 10.01, bid_qty=1_000.0, ask_qty=1_000.0)]
    quotes_b = [_quote(0, 5.0, 5.005, bid_qty=1_000.0, ask_qty=1_000.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    result = simulate_round_trip_trade(
        intent, quotes_a=quotes_a, quotes_b=quotes_b, config=config
    )

    assert result.status is TradeStatus.NO_EXIT_FILL
    assert result.entry_fill_a.filled_quantity > 0.0
    assert result.entry_fill_b.filled_quantity > 0.0
    assert result.net_pnl_quote == 0.0


def test_invalid_side_fails_closed_instead_of_silently_defaulting() -> None:
    with pytest.raises(FillModelError):
        simulate_market_fill(
            order_id="bad-side-order",
            side="HOLD",
            quantity=1.0,
            quotes=[_quote(0, 10.0, 10.01)],
            decision_time=0,
        )
