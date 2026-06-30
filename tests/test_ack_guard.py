from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution.ack_guard import (
    AckGuardAction,
    AckGuardDecisionType,
    AckGuardOrderStatus,
    AckGuardReason,
    AckGuardRequest,
    GuardedOrderState,
    evaluate_ack_guard,
)
from src.execution.client_order_id import generate_client_order_id
from src.ledger.idempotency import (
    order_ack_unknown_key,
    order_intent_created_key,
    order_sent_key,
)


def _request(**overrides: object) -> AckGuardRequest:
    fields = {
        "action": AckGuardAction.RETRY_ORDER,
        "venue": "BINANCE",
        "account_id": "paper-main",
        "trade_id": "trade-1",
        "leg": "A",
        "client_order_id": "client-A-1",
    }
    fields.update(overrides)
    return AckGuardRequest(**fields)


def _state(**overrides: object) -> GuardedOrderState:
    fields = {
        "venue": "BINANCE",
        "account_id": "paper-main",
        "trade_id": "trade-1",
        "leg": "A",
        "client_order_id": "client-A-1",
        "status": AckGuardOrderStatus.ACK_UNKNOWN_UNRESOLVED,
        "phase": "ENTRY",
        "symbol": "BTCUSDT",
        "slice_id": "slice-1",
    }
    fields.update(overrides)
    return GuardedOrderState(**fields)


def test_unresolved_ack_unknown_blocks_blind_retry() -> None:
    decision = evaluate_ack_guard(_request(), [_state()])

    assert decision.decision is AckGuardDecisionType.BLOCK
    assert decision.blocked is True
    assert decision.reason is AckGuardReason.BLIND_RETRY_BLOCKED
    assert decision.blocking_client_order_id == "client-A-1"
    assert decision.blocking_status is AckGuardOrderStatus.ACK_UNKNOWN_UNRESOLVED


def test_same_leg_uncertain_slice_blocks_new_slice() -> None:
    decision = evaluate_ack_guard(
        _request(
            action=AckGuardAction.CREATE_NEW_SLICE,
            client_order_id="client-A-2",
            slice_id="slice-2",
        ),
        [_state()],
    )

    assert decision.blocked is True
    assert decision.reason is AckGuardReason.SAME_LEG_UNCERTAIN_SLICE_BLOCKED
    assert decision.blocking_client_order_id == "client-A-1"


def test_sprint3_unresolved_send_and_ack_unknown_fail_closed() -> None:
    first_slice_id = generate_client_order_id(
        venue="BINANCE",
        account_id="paper-main",
        strategy_id="pairs-v1",
        trade_id="trade-1",
        leg="A",
        phase="ENTRY",
        symbol="BTCUSDT",
        slice_id="slice-1",
    )
    second_slice_id = generate_client_order_id(
        venue="BINANCE",
        account_id="paper-main",
        strategy_id="pairs-v1",
        trade_id="trade-1",
        leg="A",
        phase="ENTRY",
        symbol="BTCUSDT",
        slice_id="slice-2",
    )

    assert (
        order_intent_created_key(
            venue="BINANCE",
            account_id="paper-main",
            strategy_id="pairs-v1",
            trade_id="trade-1",
            leg="A",
            phase="ENTRY",
            symbol="BTCUSDT",
            slice_id="slice-1",
        )
        == "ORDER_INTENT_CREATED:BINANCE:paper-main:pairs-v1:trade-1:A:ENTRY:BTCUSDT:slice-slice-1"
    )
    assert first_slice_id in order_sent_key(
        client_order_id=first_slice_id,
        send_attempt=1,
        side_effect_type="PLACE",
    )
    assert first_slice_id in order_ack_unknown_key(
        venue="BINANCE",
        account_id="paper-main",
        client_order_id=first_slice_id,
        unknown_reason="REST_TIMEOUT",
    )

    unresolved_send_state = _state(
        client_order_id=first_slice_id,
        status=AckGuardOrderStatus.ORDER_SENT_UNRESOLVED,
        slice_id="slice-1",
    )
    ack_unknown_state = _state(
        client_order_id=first_slice_id,
        status=AckGuardOrderStatus.ACK_UNKNOWN_UNRESOLVED,
        slice_id="slice-1",
    )

    for state in (unresolved_send_state, ack_unknown_state):
        retry_decision = evaluate_ack_guard(
            _request(client_order_id=first_slice_id),
            [state],
        )
        slice_decision = evaluate_ack_guard(
            _request(
                action=AckGuardAction.CREATE_NEW_SLICE,
                client_order_id=second_slice_id,
                slice_id="slice-2",
            ),
            [state],
        )

        assert retry_decision.blocked is True
        assert retry_decision.reason is AckGuardReason.BLIND_RETRY_BLOCKED
        assert retry_decision.blocking_client_order_id == first_slice_id
        assert slice_decision.blocked is True
        assert slice_decision.reason is AckGuardReason.SAME_LEG_UNCERTAIN_SLICE_BLOCKED
        assert slice_decision.blocking_client_order_id == first_slice_id


def test_different_leg_uncertainty_does_not_block_new_slice() -> None:
    decision = evaluate_ack_guard(
        _request(
            action=AckGuardAction.CREATE_NEW_SLICE,
            leg="B",
            client_order_id="client-B-1",
            slice_id="slice-1",
        ),
        [_state(leg="A")],
    )

    assert decision.allowed is True
    assert decision.reason is AckGuardReason.CLEAR


@pytest.mark.parametrize(
    "resolved_status",
    (
        AckGuardOrderStatus.ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL,
        AckGuardOrderStatus.CANCELED_ZERO_FILL_RECONCILED,
        AckGuardOrderStatus.FLAT_RECONCILED,
    ),
)
def test_explicit_clear_state_permits_retry(
    resolved_status: AckGuardOrderStatus,
) -> None:
    decision = evaluate_ack_guard(_request(), [_state(status=resolved_status)])

    assert decision.allowed is True
    assert decision.reason is AckGuardReason.RETRY_AFTER_RESOLUTION


@pytest.mark.parametrize(
    "not_clear_status",
    (
        AckGuardOrderStatus.ACKED,
        AckGuardOrderStatus.PARTIAL_FILL_RECONCILED,
        AckGuardOrderStatus.FILL_RECONCILED,
    ),
)
def test_retry_stays_blocked_when_resolution_proves_side_effect_exists(
    not_clear_status: AckGuardOrderStatus,
) -> None:
    decision = evaluate_ack_guard(_request(), [_state(status=not_clear_status)])

    assert decision.blocked is True
    assert decision.reason is AckGuardReason.BLIND_RETRY_BLOCKED
    assert decision.blocking_status is not_clear_status


def test_retry_requires_resolved_state_in_same_order_scope() -> None:
    with pytest.raises(ValueError, match="current state for client_order_id is required"):
        evaluate_ack_guard(
            _request(),
            [
                _state(
                    venue="KRAKEN",
                    status=AckGuardOrderStatus.ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL,
                )
            ],
        )


def test_sprint3_resolved_no_order_no_fill_retry_requires_same_scope_state() -> None:
    client_order_id = generate_client_order_id(
        venue="BINANCE",
        account_id="paper-main",
        strategy_id="pairs-v1",
        trade_id="trade-1",
        leg="A",
        phase="ENTRY",
        symbol="BTCUSDT",
        attempt=1,
    )
    resolved_state = _state(
        client_order_id=client_order_id,
        status=AckGuardOrderStatus.ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL,
    )

    allowed = evaluate_ack_guard(_request(client_order_id=client_order_id), [resolved_state])

    assert allowed.allowed is True
    assert allowed.reason is AckGuardReason.RETRY_AFTER_RESOLUTION

    with pytest.raises(ValueError, match="current state for client_order_id is required"):
        evaluate_ack_guard(_request(client_order_id=client_order_id), [])

    with pytest.raises(ValueError, match="current state for client_order_id is required"):
        evaluate_ack_guard(
            _request(client_order_id=client_order_id),
            [
                _state(
                    trade_id="trade-2",
                    client_order_id=client_order_id,
                    status=AckGuardOrderStatus.ACK_UNKNOWN_RESOLVED_NO_ORDER_NO_FILL,
                )
            ],
        )


def test_resolved_same_leg_state_permits_new_slice() -> None:
    decision = evaluate_ack_guard(
        _request(
            action=AckGuardAction.CREATE_NEW_SLICE,
            client_order_id="client-A-2",
            slice_id="slice-2",
        ),
        [_state(status=AckGuardOrderStatus.FLAT_RECONCILED)],
    )

    assert decision.allowed is True
    assert decision.reason is AckGuardReason.CLEAR


@pytest.mark.parametrize(
    "guard_request,states,match",
    (
        (
            _request(client_order_id=""),
            [_state(status=AckGuardOrderStatus.ACKED)],
            "client_order_id is required",
        ),
        (
            _request(action=AckGuardAction.CREATE_NEW_SLICE, slice_id=None),
            [_state()],
            "slice_id is required",
        ),
        (
            _request(action="SEND_ANYWAY"),
            [_state()],
            "unsupported ack guard action",
        ),
        (
            _request(),
            [_state(status="MAYBE")],
            "unsupported order status",
        ),
        (
            _request(client_order_id="missing-client"),
            [_state(status=AckGuardOrderStatus.ACKED)],
            "current state for client_order_id is required",
        ),
        (
            _request(),
            None,
            "order_states is required",
        ),
    ),
)
def test_invalid_or_missing_inputs_raise_value_error(
    guard_request: AckGuardRequest,
    states: list[GuardedOrderState] | None,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        evaluate_ack_guard(guard_request, states)
