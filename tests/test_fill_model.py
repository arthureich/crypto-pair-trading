from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.fill_model import (  # noqa: E402
    FillModelConfig,
    FillModelError,
    FillStatus,
    TopOfBookQuote,
    simulate_limit_fill,
    simulate_market_fill,
)
from src.execution.ack_guard import AckGuardOrderStatus  # noqa: E402
from src.execution.slippage_estimator import SlippageSide  # noqa: E402


def _quote(event_time: int, bid: float, ask: float, bid_qty: float, ask_qty: float) -> TopOfBookQuote:
    return TopOfBookQuote(
        event_time=event_time,
        best_bid=bid,
        best_ask=ask,
        best_bid_qty=bid_qty,
        best_ask_qty=ask_qty,
    )


def test_market_fill_completes_when_quantity_fits_level_one() -> None:
    quotes = [_quote(1_000, 100.0, 100.1, 5.0, 5.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    outcome = simulate_market_fill(
        order_id="order-1",
        side=SlippageSide.BUY,
        quantity=2.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.status is FillStatus.FILLED
    assert outcome.filled_quantity == 2.0
    assert outcome.average_price == pytest.approx(100.1)
    assert outcome.ack_status is AckGuardOrderStatus.ACKED


def test_market_ioc_partially_fills_when_quantity_exceeds_level_one() -> None:
    quotes = [_quote(1_000, 100.0, 100.1, 5.0, 3.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    outcome = simulate_market_fill(
        order_id="order-2",
        side=SlippageSide.BUY,
        quantity=10.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.status is FillStatus.PARTIALLY_FILLED
    assert outcome.filled_quantity == pytest.approx(3.0)
    assert outcome.fill_ratio == pytest.approx(0.3)


def test_partial_fill_still_reports_a_real_average_price_and_slippage() -> None:
    """Regression: a partial fill has a real executed price, not None.

    ``estimate_slippage`` (Sprint 6) nulls its own average_price/slippage_bps
    whenever the full requested quantity does not fill, even though it still
    filled something at a real price. A caller (e.g. execution_simulator)
    that uses ``average_price is None`` to detect "nothing happened" would
    silently drop a partially-filled leg's real PnL to zero instead of
    computing it from what actually filled.
    """

    quotes = [_quote(1_000, 100.0, 100.1, 5.0, 3.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    outcome = simulate_market_fill(
        order_id="order-2b",
        side=SlippageSide.BUY,
        quantity=10.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
        reference_price=100.05,
    )

    assert outcome.status is FillStatus.PARTIALLY_FILLED
    assert outcome.average_price is not None
    assert outcome.average_price == pytest.approx(100.1)
    assert outcome.slippage_bps is not None


def test_market_fill_fails_closed_without_reachable_quote() -> None:
    quotes = [_quote(500, 100.0, 100.1, 5.0, 5.0)]
    config = FillModelConfig(latency_ms=1_000, ack_unknown_rate=0.0)

    outcome = simulate_market_fill(
        order_id="order-3",
        side=SlippageSide.BUY,
        quantity=1.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.status is FillStatus.NO_QUOTE
    assert outcome.filled_quantity == 0.0


def test_latency_never_selects_a_quote_before_decision_plus_latency() -> None:
    quotes = [
        _quote(1_000, 100.0, 100.1, 5.0, 5.0),
        _quote(1_100, 101.0, 101.1, 5.0, 5.0),
        _quote(1_300, 102.0, 102.1, 5.0, 5.0),
    ]
    config = FillModelConfig(latency_ms=250, ack_unknown_rate=0.0)

    outcome = simulate_market_fill(
        order_id="order-4",
        side=SlippageSide.BUY,
        quantity=1.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.execution_time == 1_300
    assert outcome.average_price == pytest.approx(102.1)


def test_limit_order_fills_when_a_later_quote_crosses_the_price() -> None:
    quotes = [
        _quote(1_000, 100.0, 100.2, 5.0, 5.0),
        _quote(2_000, 99.8, 100.0, 5.0, 5.0),
        _quote(3_000, 99.7, 99.9, 5.0, 5.0),
    ]
    config = FillModelConfig(latency_ms=0, limit_ttl_ms=5_000, ack_unknown_rate=0.0)

    outcome = simulate_limit_fill(
        order_id="order-5",
        side=SlippageSide.BUY,
        quantity=2.0,
        limit_price=99.9,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.status is FillStatus.FILLED
    assert outcome.execution_time == 3_000
    assert outcome.average_price == pytest.approx(99.9)


def test_limit_order_expires_when_no_quote_crosses_within_ttl() -> None:
    quotes = [
        _quote(1_000, 100.0, 100.2, 5.0, 5.0),
        _quote(2_000, 100.1, 100.3, 5.0, 5.0),
    ]
    config = FillModelConfig(latency_ms=0, limit_ttl_ms=3_000, ack_unknown_rate=0.0)

    outcome = simulate_limit_fill(
        order_id="order-6",
        side=SlippageSide.BUY,
        quantity=1.0,
        limit_price=90.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.status is FillStatus.EXPIRED
    assert outcome.filled_quantity == 0.0


def test_limit_order_partially_fills_and_expires_with_residual() -> None:
    quotes = [_quote(1_000, 99.8, 99.9, 5.0, 1.0)]
    config = FillModelConfig(latency_ms=0, limit_ttl_ms=3_000, ack_unknown_rate=0.0)

    outcome = simulate_limit_fill(
        order_id="order-7",
        side=SlippageSide.BUY,
        quantity=4.0,
        limit_price=99.9,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.status is FillStatus.PARTIALLY_FILLED
    assert outcome.filled_quantity == pytest.approx(1.0)


def test_ack_unknown_decision_is_deterministic_for_same_order_id() -> None:
    quotes = [_quote(1_000, 100.0, 100.1, 5.0, 5.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=1.0)

    first = simulate_market_fill(
        order_id="deterministic-order",
        side=SlippageSide.BUY,
        quantity=1.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )
    second = simulate_market_fill(
        order_id="deterministic-order",
        side=SlippageSide.BUY,
        quantity=1.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert first.ack_status is AckGuardOrderStatus.ACK_UNKNOWN_UNRESOLVED
    assert second.ack_status is AckGuardOrderStatus.ACK_UNKNOWN_UNRESOLVED
    assert first.reconciliation_available_time == second.reconciliation_available_time
    assert first.reconciliation_available_time == 1_000 + config.reconciliation_latency_ms


def test_ack_unknown_rate_zero_never_triggers() -> None:
    quotes = [_quote(1_000, 100.0, 100.1, 5.0, 5.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    outcome = simulate_market_fill(
        order_id="any-order-id",
        side=SlippageSide.SELL,
        quantity=1.0,
        quotes=quotes,
        decision_time=1_000,
        config=config,
    )

    assert outcome.ack_status is AckGuardOrderStatus.ACKED
    assert outcome.reconciliation_available_time == outcome.execution_time


def test_invalid_quantity_fails_closed() -> None:
    with pytest.raises(FillModelError):
        simulate_market_fill(
            order_id="bad-order",
            side=SlippageSide.BUY,
            quantity=-1.0,
            quotes=[_quote(1_000, 100.0, 100.1, 5.0, 5.0)],
            decision_time=1_000,
        )


def test_crossed_quote_is_rejected_fail_closed() -> None:
    with pytest.raises(FillModelError):
        TopOfBookQuote(event_time=1, best_bid=101.0, best_ask=100.0, best_bid_qty=1.0, best_ask_qty=1.0)
