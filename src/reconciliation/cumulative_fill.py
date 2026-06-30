"""Cumulative fill reconciliation helpers.

The exchange quantity is cumulative truth for one order. The only quantity
that may increase Ledger position is the positive difference from the Ledger's
already-applied cumulative quantity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

type QuantityInput = Decimal | int | str

ZERO = Decimal("0")


class CumulativeFillStatus(StrEnum):
    """Classification for one cumulative exchange observation."""

    NEW_FILL = "NEW_FILL"
    DUPLICATE = "DUPLICATE"
    LOWER_THAN_LEDGER = "LOWER_THAN_LEDGER"
    EXACT_ZERO = "EXACT_ZERO"


@dataclass(frozen=True, slots=True)
class CumulativeFillObservation:
    """Exchange and Ledger cumulative quantities for one order."""

    exchange_cum_qty: Decimal
    ledger_cum_qty: Decimal


@dataclass(frozen=True, slots=True)
class CumulativeFillResult:
    """Reconciliation result for one cumulative fill observation."""

    exchange_cum_qty: Decimal
    ledger_cum_qty: Decimal
    delta_fill: Decimal
    status: CumulativeFillStatus

    @property
    def ledger_cum_qty_after(self) -> Decimal:
        """Ledger cumulative quantity after applying this safe delta."""
        return self.ledger_cum_qty + self.delta_fill

    @property
    def increases_position(self) -> bool:
        """Whether this observation may increase Ledger position."""
        return self.delta_fill > ZERO

    @property
    def is_duplicate_observation(self) -> bool:
        """Whether this observation repeats Ledger's current cumulative qty."""
        return self.status in {
            CumulativeFillStatus.DUPLICATE,
            CumulativeFillStatus.EXACT_ZERO,
        }

    @property
    def is_inconsistent_regression(self) -> bool:
        """Whether exchange cumulative qty is lower than Ledger cumulative qty."""
        return self.status is CumulativeFillStatus.LOWER_THAN_LEDGER


def reconcile_cumulative_fill(
    *,
    exchange_cum_qty: QuantityInput,
    ledger_cum_qty: QuantityInput,
) -> CumulativeFillResult:
    """Compute ``delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)``.

    Float inputs are rejected so callers cannot accidentally introduce binary
    floating-point drift into Ledger quantity math.
    """
    observation = CumulativeFillObservation(
        exchange_cum_qty=_to_decimal_quantity(exchange_cum_qty, "exchange_cum_qty"),
        ledger_cum_qty=_to_decimal_quantity(ledger_cum_qty, "ledger_cum_qty"),
    )

    raw_delta = observation.exchange_cum_qty - observation.ledger_cum_qty
    delta_fill = raw_delta if raw_delta > ZERO else ZERO

    return CumulativeFillResult(
        exchange_cum_qty=observation.exchange_cum_qty,
        ledger_cum_qty=observation.ledger_cum_qty,
        delta_fill=delta_fill,
        status=_classify(observation),
    )


def _classify(observation: CumulativeFillObservation) -> CumulativeFillStatus:
    if observation.exchange_cum_qty == ZERO and observation.ledger_cum_qty == ZERO:
        return CumulativeFillStatus.EXACT_ZERO
    if observation.exchange_cum_qty > observation.ledger_cum_qty:
        return CumulativeFillStatus.NEW_FILL
    if observation.exchange_cum_qty == observation.ledger_cum_qty:
        return CumulativeFillStatus.DUPLICATE
    return CumulativeFillStatus.LOWER_THAN_LEDGER


def _to_decimal_quantity(value: QuantityInput, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be Decimal, int, or str, not bool")
    if isinstance(value, float):
        raise TypeError(f"{field_name} must not be float; use Decimal or a string")
    if not isinstance(value, Decimal | int | str):
        raise TypeError(f"{field_name} must be Decimal, int, or str")

    try:
        quantity = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid Decimal quantity") from exc

    if not quantity.is_finite():
        raise ValueError(f"{field_name} must be finite")
    if quantity < ZERO:
        raise ValueError(f"{field_name} must be non-negative")
    return quantity


__all__ = [
    "CumulativeFillObservation",
    "CumulativeFillResult",
    "CumulativeFillStatus",
    "QuantityInput",
    "reconcile_cumulative_fill",
]
