from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.recovery import (
    OrderSendRecoveryStatus,
    OrderSendState,
    RecoveryBootDecisionType,
    RecoveryBootReason,
    build_recovery_boot_snapshot,
    classify_order_send_states,
    classify_recovery_boot,
)


def _order_state(
    status: OrderSendRecoveryStatus = OrderSendRecoveryStatus.RESOLVED,
) -> OrderSendState:
    return OrderSendState(
        client_order_id="client-1",
        status=status,
        trade_id="trade-1",
        venue="BINANCE",
        account_id="paper-main",
    )


def test_recovery_boot_blocks_entries_before_boot_started() -> None:
    decision = classify_recovery_boot(build_recovery_boot_snapshot(recovery_boot_started=False))

    assert decision.decision is RecoveryBootDecisionType.BLOCK_NORMAL_ENTRIES
    assert decision.normal_entries_blocked is True
    assert decision.reason is RecoveryBootReason.RECOVERY_BOOT_NOT_STARTED


def test_unresolved_order_send_blocks_normal_resume() -> None:
    decision = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=[_order_state(OrderSendRecoveryStatus.UNRESOLVED_AFTER_SEND)],
            exchange_evidence_complete=True,
            reconciliation_completed=True,
            flat_reconciled=True,
        )
    )

    assert decision.normal_entries_blocked is True
    assert decision.reason is RecoveryBootReason.UNRESOLVED_ORDER_SENDS
    assert decision.unresolved_orders_count == 1


def test_unresolved_positions_block_resume_even_when_orders_are_clear() -> None:
    decision = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=[_order_state()],
            unresolved_positions_count=1,
            exchange_evidence_complete=True,
            reconciliation_completed=True,
        )
    )

    assert decision.normal_entries_blocked is True
    assert decision.reason is RecoveryBootReason.UNRESOLVED_POSITIONS


def test_incomplete_exchange_evidence_blocks_resume() -> None:
    decision = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=[_order_state()],
            exchange_evidence_complete=False,
            reconciliation_completed=True,
            flat_reconciled=True,
        )
    )

    assert decision.normal_entries_blocked is True
    assert decision.reason is RecoveryBootReason.INCOMPLETE_EXCHANGE_EVIDENCE


def test_reconciliation_completed_is_required_before_resume() -> None:
    decision = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=[_order_state()],
            exchange_evidence_complete=True,
            reconciliation_completed=False,
            flat_reconciled=True,
        )
    )

    assert decision.normal_entries_blocked is True
    assert decision.reason is RecoveryBootReason.RECONCILIATION_NOT_COMPLETED


def test_flat_reconciled_truth_permits_normal_resume() -> None:
    decision = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=[_order_state()],
            exchange_evidence_complete=True,
            reconciliation_completed=True,
            flat_reconciled=True,
        )
    )

    assert decision.resume_allowed is True
    assert decision.normal_entries_blocked is False
    assert decision.reason is RecoveryBootReason.FLAT_RECONCILED


def test_open_position_requires_intentional_reconciled_position_to_resume() -> None:
    blocked = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=[_order_state()],
            open_positions_count=1,
            exchange_evidence_complete=True,
            reconciliation_completed=True,
        )
    )
    allowed = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=[_order_state()],
            open_positions_count=1,
            exchange_evidence_complete=True,
            reconciliation_completed=True,
            intentional_reconciled_position=True,
        )
    )

    assert blocked.reason is RecoveryBootReason.OPEN_POSITIONS_NOT_RECONCILED
    assert blocked.normal_entries_blocked is True
    assert allowed.resume_allowed is True
    assert allowed.reason is RecoveryBootReason.INTENTIONAL_RECONCILED_POSITION


def test_invalid_snapshot_counts_fail_closed() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        classify_recovery_boot(
            build_recovery_boot_snapshot(
                recovery_boot_started=True,
                open_positions_count=-1,
            )
        )

    with pytest.raises(ValueError, match="flat_reconciled"):
        classify_recovery_boot(
            build_recovery_boot_snapshot(
                recovery_boot_started=True,
                open_positions_count=1,
                flat_reconciled=True,
            )
        )


def test_sprint4_crash_after_order_sent_blocks_recovery_resume() -> None:
    order_states = classify_order_send_states(
        [
            {
                "event_id": "order-sent-1",
                "event_type": "ORDER_SENT",
                "sequence": 2,
                "payload": {
                    "trade_id": "trade-1",
                    "venue": "BINANCE",
                    "account_id": "paper-main",
                    "symbol": "BTCUSDT",
                    "leg": "A",
                    "phase": "ENTRY",
                    "client_order_id": "client-1",
                },
            }
        ]
    )

    decision = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=order_states,
            exchange_evidence_complete=True,
            reconciliation_completed=True,
            flat_reconciled=True,
        )
    )

    assert decision.normal_entries_blocked is True
    assert decision.reason is RecoveryBootReason.UNRESOLVED_ORDER_SENDS
    assert decision.unresolved_orders_count == 1


def test_sprint4_resolved_order_sent_and_flat_truth_permits_resume() -> None:
    order_states = classify_order_send_states(
        [
            {
                "event_id": "order-sent-1",
                "event_type": "ORDER_SENT",
                "sequence": 2,
                "payload": {
                    "trade_id": "trade-1",
                    "venue": "BINANCE",
                    "account_id": "paper-main",
                    "symbol": "BTCUSDT",
                    "leg": "A",
                    "phase": "ENTRY",
                    "client_order_id": "client-1",
                },
            },
            {
                "event_id": "flat-1",
                "event_type": "FLAT_RECONCILED",
                "sequence": 3,
                "payload": {
                    "trade_id": "trade-1",
                    "venue": "BINANCE",
                    "account_id": "paper-main",
                    "open_orders_count": 0,
                    "unresolved_orders_count": 0,
                },
            },
        ]
    )

    decision = classify_recovery_boot(
        build_recovery_boot_snapshot(
            recovery_boot_started=True,
            order_states=order_states,
            exchange_evidence_complete=True,
            reconciliation_completed=True,
            flat_reconciled=True,
        )
    )

    assert decision.resume_allowed is True
    assert decision.reason is RecoveryBootReason.FLAT_RECONCILED
