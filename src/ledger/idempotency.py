"""Pure idempotency helpers for Ledger event and exchange observations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class ObservationClassification(StrEnum):
    """How an exchange cumulative observation should affect Ledger state."""

    NEW_FILL = "NEW_FILL"
    DUPLICATE = "DUPLICATE"
    REGRESSION = "REGRESSION"


@dataclass(frozen=True, slots=True)
class ObservationDecision:
    """Classification and stable key for one exchange cumulative observation."""

    classification: ObservationClassification
    idempotency_key: str
    delta_fill: Decimal


def ledger_event_key(event_type: str, fields: Mapping[str, object]) -> str:
    """Build a deterministic idempotency key from persisted business fields.

    The mapping is sorted by field name so callers do not depend on insertion
    order. Prefer the event-specific helpers below when a contract defines a
    fixed field order.
    """
    event_name = _required_text("event_type", event_type)
    if not fields:
        raise ValueError("fields must not be empty")

    parts = [event_name]
    for field_name in sorted(fields):
        parts.append(f"{field_name}={_canonical_value(field_name, fields[field_name])}")
    return ":".join(parts)


def order_intent_created_key(
    *,
    venue: object,
    account_id: object,
    strategy_id: object,
    trade_id: object,
    leg: object,
    phase: object,
    symbol: object,
    attempt: object | None = None,
    slice_id: object | None = None,
) -> str:
    """Key for ORDER_INTENT_CREATED."""
    return _join_key(
        "ORDER_INTENT_CREATED",
        venue,
        account_id,
        strategy_id,
        trade_id,
        leg,
        phase,
        symbol,
        _attempt_or_slice(attempt=attempt, slice_id=slice_id),
    )


def order_sent_key(
    *,
    client_order_id: object,
    send_attempt: object,
    side_effect_type: object,
) -> str:
    """Key for ORDER_SENT."""
    return _join_key("ORDER_SENT", client_order_id, send_attempt, side_effect_type)


def order_acked_key(
    *,
    venue: object,
    account_id: object,
    client_order_id: object,
    exchange_order_id: object,
    ack_status: object,
) -> str:
    """Key for ORDER_ACKED."""
    return _join_key(
        "ORDER_ACKED",
        venue,
        account_id,
        client_order_id,
        exchange_order_id,
        ack_status,
    )


def order_ack_unknown_key(
    *,
    venue: object,
    account_id: object,
    client_order_id: object,
    unknown_reason: object,
) -> str:
    """Key for ORDER_ACK_UNKNOWN."""
    return _join_key("ORDER_ACK_UNKNOWN", venue, account_id, client_order_id, unknown_reason)


def partial_fill_reconciled_key(
    *,
    venue: object,
    account_id: object,
    client_order_id: object,
    exchange_order_id: object,
    exchange_cum_qty: object,
) -> str:
    """Key for PARTIAL_FILL_RECONCILED."""
    return _join_key(
        "PARTIAL_FILL_RECONCILED",
        venue,
        account_id,
        client_order_id,
        exchange_order_id,
        _canonical_decimal("exchange_cum_qty", exchange_cum_qty),
    )


def fill_reconciled_key(
    *,
    venue: object,
    account_id: object,
    client_order_id: object,
    exchange_order_id: object,
    exchange_cum_qty: object,
    terminal_order_status: object,
) -> str:
    """Key for FILL_RECONCILED."""
    return _join_key(
        "FILL_RECONCILED",
        venue,
        account_id,
        client_order_id,
        exchange_order_id,
        _canonical_decimal("exchange_cum_qty", exchange_cum_qty),
        terminal_order_status,
    )


def reconciliation_observation_key(
    *,
    venue: object,
    account_id: object,
    symbol: object,
    exchange_cum_qty: object,
    client_order_id: object | None = None,
    exchange_order_id: object | None = None,
    observation_status: object | None = None,
) -> str:
    """Key one exchange cumulative observation without exchange/router code.

    At least one of client_order_id or exchange_order_id is required. The key is
    based only on exchange/account/order identity, cumulative quantity, and an
    optional business status from the exchange snapshot.
    """
    if client_order_id is None and exchange_order_id is None:
        raise ValueError("client_order_id or exchange_order_id is required")

    fields: dict[str, object] = {
        "account_id": account_id,
        "exchange_cum_qty": _canonical_decimal("exchange_cum_qty", exchange_cum_qty),
        "symbol": symbol,
        "venue": venue,
    }
    if client_order_id is not None:
        fields["client_order_id"] = client_order_id
    if exchange_order_id is not None:
        fields["exchange_order_id"] = exchange_order_id
    if observation_status is not None:
        fields["observation_status"] = observation_status
    return ledger_event_key("EXCHANGE_RECONCILIATION_OBSERVATION", fields)


def classify_exchange_observation(
    *,
    venue: object,
    account_id: object,
    symbol: object,
    exchange_cum_qty: object,
    ledger_cum_qty: object,
    client_order_id: object | None = None,
    exchange_order_id: object | None = None,
    observation_status: object | None = None,
) -> ObservationDecision:
    """Classify a cumulative exchange observation against Ledger quantity."""
    exchange_qty = _decimal("exchange_cum_qty", exchange_cum_qty)
    ledger_qty = _decimal("ledger_cum_qty", ledger_cum_qty)
    key = reconciliation_observation_key(
        venue=venue,
        account_id=account_id,
        symbol=symbol,
        client_order_id=client_order_id,
        exchange_order_id=exchange_order_id,
        exchange_cum_qty=exchange_qty,
        observation_status=observation_status,
    )

    if exchange_qty > ledger_qty:
        return ObservationDecision(
            classification=ObservationClassification.NEW_FILL,
            idempotency_key=key,
            delta_fill=exchange_qty - ledger_qty,
        )
    if exchange_qty == ledger_qty:
        return ObservationDecision(
            classification=ObservationClassification.DUPLICATE,
            idempotency_key=key,
            delta_fill=Decimal("0"),
        )
    return ObservationDecision(
        classification=ObservationClassification.REGRESSION,
        idempotency_key=key,
        delta_fill=Decimal("0"),
    )


def _join_key(event_type: str, *values: object) -> str:
    return ":".join(
        [_required_text("event_type", event_type), *[_canonical_value("field", v) for v in values]]
    )


def _attempt_or_slice(*, attempt: object | None, slice_id: object | None) -> str:
    if attempt is None and slice_id is None:
        raise ValueError("attempt or slice_id is required")
    if attempt is not None and slice_id is not None:
        raise ValueError("attempt and slice_id are mutually exclusive")
    if attempt is not None:
        return f"attempt-{_canonical_value('attempt', attempt)}"
    return f"slice-{_canonical_value('slice_id', slice_id)}"


def _canonical_value(field_name: str, value: object) -> str:
    if isinstance(value, Decimal):
        return _canonical_decimal(field_name, value)
    return _required_text(field_name, value)


def _required_text(field_name: str, value: object) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _canonical_decimal(field_name: str, value: object) -> str:
    decimal_value = _decimal(field_name, value)
    text = format(decimal_value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _decimal(field_name: str, value: object) -> Decimal:
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a decimal value") from exc
    if not decimal_value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    if decimal_value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return decimal_value


__all__ = [
    "ObservationClassification",
    "ObservationDecision",
    "classify_exchange_observation",
    "fill_reconciled_key",
    "ledger_event_key",
    "order_ack_unknown_key",
    "order_acked_key",
    "order_intent_created_key",
    "order_sent_key",
    "partial_fill_reconciled_key",
    "reconciliation_observation_key",
]
