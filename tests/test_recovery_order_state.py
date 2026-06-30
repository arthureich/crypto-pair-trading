from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.recovery import (
    OrderSendRecoveryStatus,
    classify_order_send_states,
    has_unresolved_order_sends,
    unresolved_order_sends,
)


def _event(
    event_type: str,
    *,
    event_id: str | None = None,
    sequence: int = 1,
    **payload: object,
) -> dict[str, object]:
    return {
        "event_id": event_id or f"event-{sequence}",
        "event_type": event_type,
        "sequence": sequence,
        "payload": {
            "trade_id": "trade-1",
            "venue": "BINANCE",
            "account_id": "paper-main",
            "symbol": "BTCUSDT",
            "leg": "A",
            "phase": "ENTRY",
            "client_order_id": "client-1",
            **payload,
        },
    }


def test_crash_after_order_sent_is_unresolved_and_recovery_required() -> None:
    states = classify_order_send_states([_event("ORDER_SENT", sequence=2)])

    assert len(states) == 1
    assert states[0].client_order_id == "client-1"
    assert states[0].status is OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND
    assert states[0].recovery_required is True
    assert has_unresolved_order_sends([_event("ORDER_SENT", sequence=2)]) is True


def test_history_without_order_sent_creates_no_false_unresolved_order() -> None:
    events = [_event("ORDER_INTENT_CREATED", sequence=1), _event("ORDER_ACKED", sequence=3)]

    assert classify_order_send_states(events) == ()
    assert unresolved_order_sends(events) == ()


def test_later_ack_clears_unresolved_order_sent_for_same_order() -> None:
    states = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2),
            _event("ORDER_ACKED", sequence=3, exchange_order_id="ex-1"),
        ]
    )

    assert states[0].status is OrderSendRecoveryStatus.RESOLVED
    assert states[0].recovery_required is False
    assert states[0].resolved_by_event_type == "ORDER_ACKED"


def test_partial_and_full_fill_reconciliation_clear_unresolved_send() -> None:
    partial = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2),
            _event("PARTIAL_FILL_RECONCILED", sequence=3, exchange_cum_qty="0.5"),
        ]
    )
    full = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2),
            _event("FILL_RECONCILED", sequence=3, exchange_cum_qty="1"),
        ]
    )

    assert partial[0].status is OrderSendRecoveryStatus.RESOLVED
    assert partial[0].resolved_by_event_type == "PARTIAL_FILL_RECONCILED"
    assert full[0].status is OrderSendRecoveryStatus.RESOLVED
    assert full[0].resolved_by_event_type == "FILL_RECONCILED"


def test_wrong_order_resolution_does_not_clear_unresolved_send() -> None:
    states = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2, client_order_id="client-1"),
            _event("ORDER_ACKED", sequence=3, client_order_id="client-2"),
        ]
    )

    assert states[0].client_order_id == "client-1"
    assert states[0].status is OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND


def test_wrong_lifecycle_scope_resolution_does_not_clear_unresolved_send() -> None:
    states = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2, client_order_id="client-1"),
            _event("ORDER_ACKED", sequence=3, trade_id="trade-2", client_order_id="client-1"),
        ]
    )

    assert states[0].status is OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND


def test_flat_reconciled_clears_matching_lifecycle_when_no_orders_remain() -> None:
    states = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2),
            _event(
                "FLAT_RECONCILED",
                sequence=4,
                client_order_id=None,
                open_orders_count=0,
                unresolved_orders_count=0,
            ),
        ]
    )

    assert states[0].status is OrderSendRecoveryStatus.RESOLVED
    assert states[0].resolved_by_event_type == "FLAT_RECONCILED"


def test_flat_reconciled_with_remaining_uncertainty_does_not_clear_send() -> None:
    states = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2),
            _event(
                "FLAT_RECONCILED",
                sequence=4,
                client_order_id=None,
                open_orders_count=0,
                unresolved_orders_count=1,
            ),
        ]
    )

    assert states[0].status is OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND


def test_multiple_orders_are_classified_independently() -> None:
    states = classify_order_send_states(
        [
            _event("ORDER_SENT", sequence=2, client_order_id="client-1", symbol="BTCUSDT"),
            _event("ORDER_SENT", sequence=3, client_order_id="client-2", symbol="ETHUSDT"),
            _event("ORDER_ACKED", sequence=4, client_order_id="client-2", symbol="ETHUSDT"),
        ]
    )

    by_client_id = {state.client_order_id: state for state in states}
    assert by_client_id["client-1"].status is OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND
    assert by_client_id["client-2"].status is OrderSendRecoveryStatus.RESOLVED
    assert [state.client_order_id for state in unresolved_order_sends(_state_to_events())] == [
        "client-1"
    ]


def _state_to_events() -> list[dict[str, object]]:
    return [
        _event("ORDER_SENT", sequence=2, client_order_id="client-1", symbol="BTCUSDT"),
        _event("ORDER_SENT", sequence=3, client_order_id="client-2", symbol="ETHUSDT"),
        _event("ORDER_ACKED", sequence=4, client_order_id="client-2", symbol="ETHUSDT"),
    ]
