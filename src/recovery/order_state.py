"""Pure recovery classification for durable order send uncertainty."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class OrderSendRecoveryStatus(StrEnum):
    """Recovery status for one client order send attempt."""

    NO_SEND = "NO_SEND"
    RESOLVED = "RESOLVED"
    UNRESOLVED_AFTER_SEND = "UNRESOLVED_AFTER_SEND"


class OrderResolutionEvent(StrEnum):
    """Ledger events that can prove an ORDER_SENT is no longer crash-uncertain."""

    ORDER_ACKED = "ORDER_ACKED"
    ORDER_ACK_UNKNOWN_RESOLVED = "ORDER_ACK_UNKNOWN_RESOLVED"
    ACK_UNKNOWN_RESOLVED = "ACK_UNKNOWN_RESOLVED"
    PARTIAL_FILL_RECONCILED = "PARTIAL_FILL_RECONCILED"
    FILL_RECONCILED = "FILL_RECONCILED"
    CANCEL_RECONCILED = "CANCEL_RECONCILED"
    ORDER_CANCELED_RECONCILED = "ORDER_CANCELED_RECONCILED"
    FLAT_RECONCILED = "FLAT_RECONCILED"


RESOLUTION_EVENT_TYPES = frozenset(item.value for item in OrderResolutionEvent)


@dataclass(frozen=True, slots=True)
class OrderSendState:
    """Recovery classification for one client order id."""

    client_order_id: str
    status: OrderSendRecoveryStatus
    trade_id: str | None = None
    venue: str | None = None
    account_id: str | None = None
    symbol: str | None = None
    leg: str | None = None
    phase: str | None = None
    sent_event_id: str | None = None
    sent_sequence: int | None = None
    resolved_by_event_type: str | None = None
    resolved_by_event_id: str | None = None
    resolution_sequence: int | None = None

    @property
    def recovery_required(self) -> bool:
        """Whether recovery must reconcile this order before normal trading."""
        return self.status is OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND


def classify_order_send_states(events: Iterable[object]) -> tuple[OrderSendState, ...]:
    """Classify ORDER_SENT histories by client order id.

    This helper is intentionally pure: it only inspects event-like objects or
    mappings and never queries exchanges, writes persistence, or relies on
    process memory.
    """
    states: dict[str, OrderSendState] = {}

    for event in sorted((_normalize_event(event) for event in events), key=_event_sort_key):
        event_type = event["event_type"]
        client_order_id = _optional_text(event["payload"].get("client_order_id"))

        if event_type == "ORDER_SENT":
            if client_order_id is None:
                raise ValueError("ORDER_SENT payload.client_order_id is required")
            states[client_order_id] = _sent_state(event, client_order_id)
            continue

        if event_type in RESOLUTION_EVENT_TYPES:
            _apply_resolution(states, event, client_order_id)

    return tuple(states[key] for key in sorted(states))


def unresolved_order_sends(events: Iterable[object]) -> tuple[OrderSendState, ...]:
    """Return only ORDER_SENT states that still require recovery."""
    return tuple(
        state
        for state in classify_order_send_states(events)
        if state.status is OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND
    )


def has_unresolved_order_sends(events: Iterable[object]) -> bool:
    """Return whether any durable ORDER_SENT remains unresolved."""
    return bool(unresolved_order_sends(events))


def _sent_state(event: Mapping[str, Any], client_order_id: str) -> OrderSendState:
    payload = event["payload"]
    return OrderSendState(
        client_order_id=client_order_id,
        status=OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND,
        trade_id=_optional_text(payload.get("trade_id")),
        venue=_optional_text(payload.get("venue")),
        account_id=_optional_text(payload.get("account_id")),
        symbol=_optional_text(payload.get("symbol")),
        leg=_optional_text(payload.get("leg")),
        phase=_optional_text(payload.get("phase")),
        sent_event_id=_optional_text(event.get("event_id")),
        sent_sequence=_optional_int(event.get("sequence")),
    )


def _apply_resolution(
    states: dict[str, OrderSendState],
    event: Mapping[str, Any],
    client_order_id: str | None,
) -> None:
    if event["event_type"] == OrderResolutionEvent.FLAT_RECONCILED:
        _apply_flat_resolution(states, event)
        return

    if client_order_id is None:
        return
    state = states.get(client_order_id)
    if state is None:
        return
    if not _same_order_scope(state, event["payload"]):
        return
    states[client_order_id] = _resolved_state(state, event)


def _apply_flat_resolution(
    states: dict[str, OrderSendState],
    event: Mapping[str, Any],
) -> None:
    payload = event["payload"]
    if _optional_int(payload.get("unresolved_orders_count")) not in (None, 0):
        return
    if _optional_int(payload.get("open_orders_count")) not in (None, 0):
        return

    for client_order_id, state in tuple(states.items()):
        if _same_lifecycle_scope(state, payload):
            states[client_order_id] = _resolved_state(state, event)


def _resolved_state(state: OrderSendState, event: Mapping[str, Any]) -> OrderSendState:
    return OrderSendState(
        client_order_id=state.client_order_id,
        status=OrderSendRecoveryStatus.RESOLVED,
        trade_id=state.trade_id,
        venue=state.venue,
        account_id=state.account_id,
        symbol=state.symbol,
        leg=state.leg,
        phase=state.phase,
        sent_event_id=state.sent_event_id,
        sent_sequence=state.sent_sequence,
        resolved_by_event_type=event["event_type"],
        resolved_by_event_id=_optional_text(event.get("event_id")),
        resolution_sequence=_optional_int(event.get("sequence")),
    )


def _same_order_scope(state: OrderSendState, payload: Mapping[str, Any]) -> bool:
    return _same_lifecycle_scope(state, payload) and _matches_optional(
        state.symbol, payload.get("symbol")
    )


def _same_lifecycle_scope(state: OrderSendState, payload: Mapping[str, Any]) -> bool:
    return all(
        _matches_optional(expected, payload.get(field_name))
        for field_name, expected in (
            ("trade_id", state.trade_id),
            ("venue", state.venue),
            ("account_id", state.account_id),
        )
    )


def _matches_optional(expected: str | None, observed: object) -> bool:
    observed_text = _optional_text(observed)
    return expected is None or observed_text is None or observed_text == expected


def _normalize_event(event: object) -> dict[str, Any]:
    payload = _event_value(event, "payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise TypeError("event payload must be a mapping")

    event_type = _required_text("event_type", _event_value(event, "event_type"))
    return {
        "event_id": _event_value(event, "event_id"),
        "event_type": event_type,
        "sequence": _event_value(event, "sequence"),
        "event_number": _event_value(event, "event_number"),
        "payload": payload,
    }


def _event_value(event: object, field_name: str) -> object:
    if isinstance(event, Mapping):
        return event.get(field_name)
    return getattr(event, field_name, None)


def _event_sort_key(event: Mapping[str, Any]) -> tuple[int, int, str]:
    sequence = _optional_int(event.get("sequence"))
    event_number = _optional_int(event.get("event_number"))
    event_id = _optional_text(event.get("event_id")) or ""
    return (
        event_number if event_number is not None else 0,
        sequence if sequence is not None else 0,
        event_id,
    )


def _required_text(field_name: str, value: object) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"{field_name} is required")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("integer value must not be bool")
    return int(value)


__all__ = [
    "OrderResolutionEvent",
    "OrderSendRecoveryStatus",
    "OrderSendState",
    "RESOLUTION_EVENT_TYPES",
    "classify_order_send_states",
    "has_unresolved_order_sends",
    "unresolved_order_sends",
]
