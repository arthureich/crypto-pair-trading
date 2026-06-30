"""Pure book-consumption slippage estimator."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from src.features.execution_features import BPS_DENOMINATOR, BookLevel


class SlippageSide(StrEnum):
    """Order side for simulated liquidity consumption."""

    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class SlippageFailureReason(StrEnum):
    """Explicit fail-closed slippage failure reasons."""

    NONE = "NONE"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"
    INVALID_REQUEST = "INVALID_REQUEST"


@dataclass(frozen=True, slots=True)
class SlippageRequest:
    """Inputs for estimating slippage from supplied book levels."""

    side: SlippageSide | str
    quantity: Decimal | str | int | None = None
    notional: Decimal | str | int | None = None
    reference_price: Decimal | str | int | None = None


@dataclass(frozen=True, slots=True)
class SlippageEstimate:
    """Result of deterministic book consumption."""

    success: bool
    side: SlippageSide
    requested_quantity: Decimal | None
    requested_notional: Decimal | None
    filled_quantity: Decimal
    spent_notional: Decimal
    average_price: Decimal | None
    slippage_bps: Decimal | None
    failure_reason: SlippageFailureReason

    @property
    def failed(self) -> bool:
        return not self.success


def estimate_slippage(
    request: SlippageRequest,
    *,
    bids: Iterable[BookLevel],
    asks: Iterable[BookLevel],
) -> SlippageEstimate:
    """Consume asks for buys and bids for sells without exchange side effects."""

    side = _coerce_side(request.side)
    try:
        quantity = _optional_positive_decimal("quantity", request.quantity)
        notional = _optional_positive_decimal("notional", request.notional)
    except (TypeError, ValueError):
        return _failed(side, None, None, SlippageFailureReason.INVALID_REQUEST)
    if side is SlippageSide.UNKNOWN or (quantity is None) == (notional is None):
        return _failed(side, quantity, notional, SlippageFailureReason.INVALID_REQUEST)

    try:
        levels = _normalize_levels(asks if side is SlippageSide.BUY else bids, side=side)
    except (TypeError, ValueError):
        return _failed(side, quantity, notional, SlippageFailureReason.INVALID_REQUEST)
    if quantity is not None:
        filled_qty, spent = _consume_quantity(levels, quantity)
        requested_qty = quantity
        requested_notional = None
        success = filled_qty == quantity
    else:
        filled_qty, spent = _consume_notional(levels, notional or Decimal("0"))
        requested_qty = None
        requested_notional = notional
        success = spent == notional

    if not success:
        return SlippageEstimate(
            success=False,
            side=side,
            requested_quantity=requested_qty,
            requested_notional=requested_notional,
            filled_quantity=filled_qty,
            spent_notional=spent,
            average_price=None,
            slippage_bps=None,
            failure_reason=SlippageFailureReason.INSUFFICIENT_LIQUIDITY,
        )

    average = spent / filled_qty
    try:
        reference = _optional_positive_decimal("reference_price", request.reference_price)
    except (TypeError, ValueError):
        return _failed(side, quantity, notional, SlippageFailureReason.INVALID_REQUEST)
    slippage = _slippage_bps(side=side, average_price=average, reference_price=reference)
    return SlippageEstimate(
        success=True,
        side=side,
        requested_quantity=requested_qty,
        requested_notional=requested_notional,
        filled_quantity=filled_qty,
        spent_notional=spent,
        average_price=average,
        slippage_bps=slippage,
        failure_reason=SlippageFailureReason.NONE,
    )


def _consume_quantity(
    levels: tuple[BookLevel, ...],
    target_quantity: Decimal,
) -> tuple[Decimal, Decimal]:
    remaining = target_quantity
    filled = Decimal("0")
    spent = Decimal("0")
    for level in levels:
        take = min(remaining, level.quantity)
        filled += take
        spent += take * level.price
        remaining -= take
        if remaining == 0:
            break
    return filled, spent


def _consume_notional(
    levels: tuple[BookLevel, ...],
    target_notional: Decimal,
) -> tuple[Decimal, Decimal]:
    remaining = target_notional
    filled = Decimal("0")
    spent = Decimal("0")
    for level in levels:
        level_notional = level.price * level.quantity
        take_notional = min(remaining, level_notional)
        take_quantity = take_notional / level.price
        filled += take_quantity
        spent += take_notional
        remaining -= take_notional
        if remaining == 0:
            break
    return filled, spent


def _slippage_bps(
    *,
    side: SlippageSide,
    average_price: Decimal,
    reference_price: Decimal | None,
) -> Decimal | None:
    if reference_price is None:
        return None
    if side is SlippageSide.BUY:
        return ((average_price - reference_price) / reference_price) * BPS_DENOMINATOR
    return ((reference_price - average_price) / reference_price) * BPS_DENOMINATOR


def _failed(
    side: SlippageSide,
    quantity: Decimal | None,
    notional: Decimal | None,
    reason: SlippageFailureReason,
) -> SlippageEstimate:
    return SlippageEstimate(
        success=False,
        side=side,
        requested_quantity=quantity,
        requested_notional=notional,
        filled_quantity=Decimal("0"),
        spent_notional=Decimal("0"),
        average_price=None,
        slippage_bps=None,
        failure_reason=reason,
    )


def _normalize_levels(levels: Iterable[BookLevel], *, side: SlippageSide) -> tuple[BookLevel, ...]:
    normalized = tuple(
        BookLevel(
            price=_positive_decimal("price", level.price),
            quantity=_non_negative_decimal("quantity", level.quantity),
        )
        for level in levels
    )
    return tuple(
        sorted(normalized, key=lambda level: level.price, reverse=side is SlippageSide.SELL)
    )


def _coerce_side(side: SlippageSide | str) -> SlippageSide:
    try:
        return SlippageSide(side)
    except ValueError:
        return SlippageSide.UNKNOWN


def _optional_positive_decimal(
    field_name: str,
    value: Decimal | str | int | None,
) -> Decimal | None:
    if value is None:
        return None
    decimal = _positive_decimal(field_name, value)
    return decimal


def _positive_decimal(field_name: str, value: Decimal | str | int) -> Decimal:
    decimal = _decimal(field_name, value)
    if decimal <= 0:
        raise ValueError(f"{field_name} must be positive")
    return decimal


def _non_negative_decimal(field_name: str, value: Decimal | str | int) -> Decimal:
    decimal = _decimal(field_name, value)
    if decimal < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return decimal


def _decimal(field_name: str, value: Decimal | str | int) -> Decimal:
    if isinstance(value, bool | float):
        raise TypeError(f"{field_name} must be Decimal, str, or int")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be decimal-compatible") from exc


__all__ = [
    "SlippageEstimate",
    "SlippageFailureReason",
    "SlippageRequest",
    "SlippageSide",
    "estimate_slippage",
]
