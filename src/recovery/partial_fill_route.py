"""Pure partial-fill route decisions for recovery and execution safety."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

type QuantityInput = Decimal | int | str
ZERO = Decimal("0")


class PartialFillRouteDecisionType(StrEnum):
    """Safe route for partial-fill uncertainty."""

    HEDGING_REQUIRED = "HEDGING_REQUIRED"
    EXIT_LOCKDOWN = "EXIT_LOCKDOWN"


class PartialFillRouteReason(StrEnum):
    """Stable reason for the partial-fill route."""

    HEDGE_PROVEN_RISK_REDUCING = "HEDGE_PROVEN_RISK_REDUCING"
    RESIDUAL_ORDER_UNCERTAIN = "RESIDUAL_ORDER_UNCERTAIN"
    HEDGE_PROOF_MISSING = "HEDGE_PROOF_MISSING"
    HEDGE_NOT_RISK_REDUCING = "HEDGE_NOT_RISK_REDUCING"
    NO_UNPAIRED_EXPOSURE_PROOF = "NO_UNPAIRED_EXPOSURE_PROOF"


@dataclass(frozen=True, slots=True)
class PartialFillRouteInput:
    """Evidence available after a partial fill is reconciled."""

    trade_id: str
    venue: str
    account_id: str
    filled_leg: str
    symbol: str
    known_position_qty: QuantityInput
    target_position_qty: QuantityInput
    residual_order_uncertain: bool
    paired_leg_reconciled: bool
    hedge_reduces_exposure: bool
    risk_reducing_proof: bool


@dataclass(frozen=True, slots=True)
class PartialFillRouteDecision:
    """Deterministic route result for partial-fill uncertainty."""

    decision: PartialFillRouteDecisionType
    reason: PartialFillRouteReason
    trade_id: str
    filled_leg: str
    symbol: str
    imbalance_qty: Decimal
    normal_entry_continuation_allowed: bool = False

    @property
    def hedge_required(self) -> bool:
        return self.decision is PartialFillRouteDecisionType.HEDGING_REQUIRED

    @property
    def exit_lockdown(self) -> bool:
        return self.decision is PartialFillRouteDecisionType.EXIT_LOCKDOWN


def decide_partial_fill_route(route_input: PartialFillRouteInput) -> PartialFillRouteDecision:
    """Route partial-fill uncertainty without silently continuing entry."""
    trade_id = _required_text("trade_id", route_input.trade_id)
    _required_text("venue", route_input.venue)
    _required_text("account_id", route_input.account_id)
    filled_leg = _required_text("filled_leg", route_input.filled_leg)
    symbol = _required_text("symbol", route_input.symbol)
    known_position_qty = _to_decimal_quantity(route_input.known_position_qty, "known_position_qty")
    target_position_qty = _to_decimal_quantity(
        route_input.target_position_qty, "target_position_qty"
    )
    imbalance_qty = abs(known_position_qty - target_position_qty)

    if imbalance_qty == ZERO or route_input.paired_leg_reconciled:
        return _lockdown(
            route_input,
            reason=PartialFillRouteReason.NO_UNPAIRED_EXPOSURE_PROOF,
            trade_id=trade_id,
            filled_leg=filled_leg,
            symbol=symbol,
            imbalance_qty=imbalance_qty,
        )
    if route_input.residual_order_uncertain:
        return _lockdown(
            route_input,
            reason=PartialFillRouteReason.RESIDUAL_ORDER_UNCERTAIN,
            trade_id=trade_id,
            filled_leg=filled_leg,
            symbol=symbol,
            imbalance_qty=imbalance_qty,
        )
    if not route_input.risk_reducing_proof:
        return _lockdown(
            route_input,
            reason=PartialFillRouteReason.HEDGE_PROOF_MISSING,
            trade_id=trade_id,
            filled_leg=filled_leg,
            symbol=symbol,
            imbalance_qty=imbalance_qty,
        )
    if not route_input.hedge_reduces_exposure:
        return _lockdown(
            route_input,
            reason=PartialFillRouteReason.HEDGE_NOT_RISK_REDUCING,
            trade_id=trade_id,
            filled_leg=filled_leg,
            symbol=symbol,
            imbalance_qty=imbalance_qty,
        )

    return PartialFillRouteDecision(
        decision=PartialFillRouteDecisionType.HEDGING_REQUIRED,
        reason=PartialFillRouteReason.HEDGE_PROVEN_RISK_REDUCING,
        trade_id=trade_id,
        filled_leg=filled_leg,
        symbol=symbol,
        imbalance_qty=imbalance_qty,
    )


def _lockdown(
    route_input: PartialFillRouteInput,
    *,
    reason: PartialFillRouteReason,
    trade_id: str,
    filled_leg: str,
    symbol: str,
    imbalance_qty: Decimal,
) -> PartialFillRouteDecision:
    return PartialFillRouteDecision(
        decision=PartialFillRouteDecisionType.EXIT_LOCKDOWN,
        reason=reason,
        trade_id=trade_id,
        filled_leg=filled_leg,
        symbol=symbol,
        imbalance_qty=imbalance_qty,
    )


def _required_text(field_name: str, value: object) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


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
    "PartialFillRouteDecision",
    "PartialFillRouteDecisionType",
    "PartialFillRouteInput",
    "PartialFillRouteReason",
    "QuantityInput",
    "decide_partial_fill_route",
]
