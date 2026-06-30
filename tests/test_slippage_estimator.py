from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution import (
    SlippageFailureReason,
    SlippageRequest,
    SlippageSide,
    estimate_slippage,
)
from src.features import BookLevel


def _bids() -> tuple[BookLevel, ...]:
    return (
        BookLevel("99", "1"),
        BookLevel("98", "2"),
    )


def _asks() -> tuple[BookLevel, ...]:
    return (
        BookLevel("101", "1"),
        BookLevel("102", "2"),
    )


def test_buy_slippage_consumes_asks() -> None:
    estimate = estimate_slippage(
        SlippageRequest(side=SlippageSide.BUY, quantity="2", reference_price="100"),
        bids=_bids(),
        asks=_asks(),
    )

    assert estimate.success is True
    assert estimate.filled_quantity == Decimal("2")
    assert estimate.spent_notional == Decimal("203")
    assert estimate.average_price == Decimal("101.5")
    assert estimate.slippage_bps == Decimal("150.0")
    assert estimate.failure_reason is SlippageFailureReason.NONE


def test_sell_slippage_consumes_bids() -> None:
    estimate = estimate_slippage(
        SlippageRequest(side=SlippageSide.SELL, quantity="2", reference_price="100"),
        bids=_bids(),
        asks=_asks(),
    )

    assert estimate.success is True
    assert estimate.filled_quantity == Decimal("2")
    assert estimate.spent_notional == Decimal("197")
    assert estimate.average_price == Decimal("98.5")
    assert estimate.slippage_bps == Decimal("150.0")


def test_notional_request_consumes_partial_level() -> None:
    estimate = estimate_slippage(
        SlippageRequest(side=SlippageSide.BUY, notional="151.5", reference_price="100"),
        bids=_bids(),
        asks=_asks(),
    )

    assert estimate.success is True
    assert estimate.requested_notional == Decimal("151.5")
    assert estimate.filled_quantity == Decimal("1.495098039215686274509803922")
    assert estimate.spent_notional == Decimal("151.5")
    assert estimate.average_price > Decimal("101")


def test_insufficient_liquidity_returns_explicit_failure_reason() -> None:
    estimate = estimate_slippage(
        SlippageRequest(side=SlippageSide.SELL, quantity="4", reference_price="100"),
        bids=_bids(),
        asks=_asks(),
    )

    assert estimate.failed is True
    assert estimate.failure_reason is SlippageFailureReason.INSUFFICIENT_LIQUIDITY
    assert estimate.filled_quantity == Decimal("3")
    assert estimate.average_price is None
    assert estimate.slippage_bps is None


def test_request_requires_exactly_one_quantity_or_notional() -> None:
    both = estimate_slippage(
        SlippageRequest(side=SlippageSide.BUY, quantity="1", notional="100"),
        bids=_bids(),
        asks=_asks(),
    )
    neither = estimate_slippage(
        SlippageRequest(side=SlippageSide.BUY),
        bids=_bids(),
        asks=_asks(),
    )

    assert both.failure_reason is SlippageFailureReason.INVALID_REQUEST
    assert neither.failure_reason is SlippageFailureReason.INVALID_REQUEST


def test_invalid_side_or_non_positive_request_returns_invalid_request() -> None:
    invalid_side = estimate_slippage(
        SlippageRequest(side="HOLD", quantity="1"),
        bids=_bids(),
        asks=_asks(),
    )
    zero_quantity = estimate_slippage(
        SlippageRequest(side=SlippageSide.BUY, quantity="0"),
        bids=_bids(),
        asks=_asks(),
    )
    negative_notional = estimate_slippage(
        SlippageRequest(side=SlippageSide.SELL, notional="-1"),
        bids=_bids(),
        asks=_asks(),
    )

    assert invalid_side.failed is True
    assert invalid_side.failure_reason is SlippageFailureReason.INVALID_REQUEST
    assert zero_quantity.failed is True
    assert zero_quantity.failure_reason is SlippageFailureReason.INVALID_REQUEST
    assert negative_notional.failed is True
    assert negative_notional.failure_reason is SlippageFailureReason.INVALID_REQUEST


def test_invalid_reference_price_or_book_level_returns_invalid_request() -> None:
    invalid_reference = estimate_slippage(
        SlippageRequest(side=SlippageSide.BUY, quantity="1", reference_price="0"),
        bids=_bids(),
        asks=_asks(),
    )
    invalid_level = estimate_slippage(
        SlippageRequest(side=SlippageSide.BUY, quantity="1", reference_price="100"),
        bids=_bids(),
        asks=(BookLevel("-101", "1"),),
    )

    assert invalid_reference.failed is True
    assert invalid_reference.failure_reason is SlippageFailureReason.INVALID_REQUEST
    assert invalid_level.failed is True
    assert invalid_level.failure_reason is SlippageFailureReason.INVALID_REQUEST
