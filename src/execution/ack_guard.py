"""Pure guard semantics for ACK_UNKNOWN retry and slice safety."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class AckGuardAction(StrEnum):
    """Execution action being checked before router integration exists."""

    RETRY_ORDER = "RETRY_ORDER"
    CREATE_NEW_SLICE = "CREATE_NEW_SLICE"


class AckGuardOrderStatus(StrEnum):
    """Ledger/reconciliation-derived order certainty states."""

    ORDER_SENT_UNRESOLVED = "ORDER_SENT_UNRESOLVED"
    ACK_UNKNOWN_UNRESOLVED = "ACK_UNKNOWN_UNRESOLVED"
    ACKED = "ACKED"
    ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL = "ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL"
    PARTIAL_FILL_RECONCILED = "PARTIAL_FILL_RECONCILED"
    FILL_RECONCILED = "FILL_RECONCILED"
    CANCELED_ZERO_FILL_RECONCILED = "CANCELED_ZERO_FILL_RECONCILED"
    FLAT_RECONCILED = "FLAT_RECONCILED"


class AckGuardDecisionType(StrEnum):
    """Allow/block result for a proposed execution action."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class AckGuardReason(StrEnum):
    """Stable reason codes for downstream risk gate/router integration."""

    CLEAR = "CLEAR"
    RETRY_AFTER_RESOLUTION = "RETRY_AFTER_RESOLUTION"
    BLIND_RETRY_BLOCKED = "BLIND_RETRY_BLOCKED"
    SAME_LEG_UNCERTAIN_SLICE_BLOCKED = "SAME_LEG_UNCERTAIN_SLICE_BLOCKED"


UNCERTAIN_ORDER_STATUSES = frozenset(
    {
        AckGuardOrderStatus.ORDER_SENT_UNRESOLVED,
        AckGuardOrderStatus.ACK_UNKNOWN_UNRESOLVED,
    }
)

SLICE_CLEAR_ORDER_STATUSES = frozenset(
    {
        AckGuardOrderStatus.ACKED,
        AckGuardOrderStatus.ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL,
        AckGuardOrderStatus.PARTIAL_FILL_RECONCILED,
        AckGuardOrderStatus.FILL_RECONCILED,
        AckGuardOrderStatus.CANCELED_ZERO_FILL_RECONCILED,
        AckGuardOrderStatus.FLAT_RECONCILED,
    }
)

RETRY_CLEAR_ORDER_STATUSES = frozenset(
    {
        AckGuardOrderStatus.ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL,
        AckGuardOrderStatus.CANCELED_ZERO_FILL_RECONCILED,
        AckGuardOrderStatus.FLAT_RECONCILED,
    }
)


@dataclass(frozen=True, slots=True)
class GuardedOrderState:
    """Current durable/reconciled state for one order or slice."""

    venue: str
    account_id: str
    trade_id: str
    leg: str
    client_order_id: str
    status: AckGuardOrderStatus | str
    phase: str | None = None
    symbol: str | None = None
    slice_id: str | None = None


@dataclass(frozen=True, slots=True)
class AckGuardRequest:
    """Proposed action that must be checked before any side effect."""

    action: AckGuardAction | str
    venue: str
    account_id: str
    trade_id: str
    leg: str
    client_order_id: str | None = None
    phase: str | None = None
    symbol: str | None = None
    slice_id: str | None = None


@dataclass(frozen=True, slots=True)
class AckGuardDecision:
    """Pure decision result with optional blocking order identity."""

    decision: AckGuardDecisionType
    reason: AckGuardReason
    blocking_client_order_id: str | None = None
    blocking_status: AckGuardOrderStatus | str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision is AckGuardDecisionType.ALLOW

    @property
    def blocked(self) -> bool:
        return self.decision is AckGuardDecisionType.BLOCK


def evaluate_ack_guard(
    request: AckGuardRequest,
    order_states: Iterable[GuardedOrderState] | None,
) -> AckGuardDecision:
    """Return whether ``request`` is safe under ACK_UNKNOWN guard rules.

    The function is deterministic and side-effect free. It does not call an
    exchange, read or write persistence, or infer resolution from missing
    state. A retry for a known client order id requires an explicit state for
    that id; unresolved ACK_UNKNOWN blocks it.
    """

    action = _coerce_action(request.action)
    _validate_request(request, action)
    if order_states is None:
        raise ValueError("order_states is required")
    states = tuple(_validate_state(state) for state in order_states)

    if action is AckGuardAction.RETRY_ORDER:
        return _evaluate_retry(request, states)
    if action is AckGuardAction.CREATE_NEW_SLICE:
        return _evaluate_new_slice(request, states)
    raise ValueError(f"unsupported ack guard action: {request.action}")


def _evaluate_retry(
    request: AckGuardRequest,
    states: tuple[GuardedOrderState, ...],
) -> AckGuardDecision:
    matching_states = [
        state
        for state in states
        if state.client_order_id == request.client_order_id and _same_leg_scope(request, state)
    ]
    if not matching_states:
        raise ValueError("current state for client_order_id is required")

    for state in matching_states:
        if state.status not in RETRY_CLEAR_ORDER_STATUSES:
            return AckGuardDecision(
                decision=AckGuardDecisionType.BLOCK,
                reason=AckGuardReason.BLIND_RETRY_BLOCKED,
                blocking_client_order_id=state.client_order_id,
                blocking_status=state.status,
            )

    return AckGuardDecision(
        decision=AckGuardDecisionType.ALLOW,
        reason=AckGuardReason.RETRY_AFTER_RESOLUTION,
    )


def _evaluate_new_slice(
    request: AckGuardRequest,
    states: tuple[GuardedOrderState, ...],
) -> AckGuardDecision:
    for state in states:
        if not _same_leg_scope(request, state):
            continue
        if state.status in UNCERTAIN_ORDER_STATUSES:
            return AckGuardDecision(
                decision=AckGuardDecisionType.BLOCK,
                reason=AckGuardReason.SAME_LEG_UNCERTAIN_SLICE_BLOCKED,
                blocking_client_order_id=state.client_order_id,
                blocking_status=state.status,
            )

    return AckGuardDecision(
        decision=AckGuardDecisionType.ALLOW,
        reason=AckGuardReason.CLEAR,
    )


def _same_leg_scope(request: AckGuardRequest, state: GuardedOrderState) -> bool:
    return (
        state.venue == request.venue
        and state.account_id == request.account_id
        and state.trade_id == request.trade_id
        and state.leg == request.leg
    )


def _validate_request(
    request: AckGuardRequest,
    action: AckGuardAction,
) -> None:
    _required_text("venue", request.venue)
    _required_text("account_id", request.account_id)
    _required_text("trade_id", request.trade_id)
    _required_text("leg", request.leg)

    if action is AckGuardAction.RETRY_ORDER:
        _required_text("client_order_id", request.client_order_id)
    if action is AckGuardAction.CREATE_NEW_SLICE:
        _required_text("slice_id", request.slice_id)


def _validate_state(state: GuardedOrderState) -> GuardedOrderState:
    _required_text("venue", state.venue)
    _required_text("account_id", state.account_id)
    _required_text("trade_id", state.trade_id)
    _required_text("leg", state.leg)
    _required_text("client_order_id", state.client_order_id)
    status = _coerce_status(state.status)
    return GuardedOrderState(
        venue=state.venue,
        account_id=state.account_id,
        trade_id=state.trade_id,
        leg=state.leg,
        client_order_id=state.client_order_id,
        status=status,
        phase=state.phase,
        symbol=state.symbol,
        slice_id=state.slice_id,
    )


def _coerce_action(action: AckGuardAction | str) -> AckGuardAction:
    try:
        return AckGuardAction(action)
    except ValueError as exc:
        raise ValueError(f"unsupported ack guard action: {action}") from exc


def _coerce_status(status: AckGuardOrderStatus | str) -> AckGuardOrderStatus:
    try:
        return AckGuardOrderStatus(status)
    except ValueError as exc:
        raise ValueError(f"unsupported order status: {status}") from exc


def _required_text(field_name: str, value: object) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


__all__ = [
    "AckGuardAction",
    "AckGuardDecision",
    "AckGuardDecisionType",
    "AckGuardOrderStatus",
    "AckGuardReason",
    "AckGuardRequest",
    "GuardedOrderState",
    "RETRY_CLEAR_ORDER_STATUSES",
    "SLICE_CLEAR_ORDER_STATUSES",
    "UNCERTAIN_ORDER_STATUSES",
    "evaluate_ack_guard",
]
