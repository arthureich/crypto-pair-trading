"""Pure recovery boot gate and normal-resume classification."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from .order_state import OrderSendState


class RecoveryBootDecisionType(StrEnum):
    """Top-level recovery boot decision."""

    BLOCK_NORMAL_ENTRIES = "BLOCK_NORMAL_ENTRIES"
    ALLOW_NORMAL_RESUME = "ALLOW_NORMAL_RESUME"


class RecoveryBootReason(StrEnum):
    """Stable reason code for recovery boot decisions."""

    RECOVERY_BOOT_NOT_STARTED = "RECOVERY_BOOT_NOT_STARTED"
    UNRESOLVED_ORDER_SENDS = "UNRESOLVED_ORDER_SENDS"
    UNRESOLVED_POSITIONS = "UNRESOLVED_POSITIONS"
    OPEN_POSITIONS_NOT_RECONCILED = "OPEN_POSITIONS_NOT_RECONCILED"
    INCOMPLETE_EXCHANGE_EVIDENCE = "INCOMPLETE_EXCHANGE_EVIDENCE"
    RECONCILIATION_NOT_COMPLETED = "RECONCILIATION_NOT_COMPLETED"
    FLAT_RECONCILED = "FLAT_RECONCILED"
    INTENTIONAL_RECONCILED_POSITION = "INTENTIONAL_RECONCILED_POSITION"


@dataclass(frozen=True, slots=True)
class RecoveryBootSnapshot:
    """Ledger/reconciliation evidence available at recovery boot."""

    recovery_boot_started: bool
    order_states: tuple[OrderSendState, ...] = ()
    open_positions_count: int = 0
    unresolved_positions_count: int = 0
    exchange_evidence_complete: bool = False
    reconciliation_completed: bool = False
    flat_reconciled: bool = False
    intentional_reconciled_position: bool = False


@dataclass(frozen=True, slots=True)
class RecoveryBootDecision:
    """Pure decision for whether normal trading may resume."""

    decision: RecoveryBootDecisionType
    reason: RecoveryBootReason
    normal_entries_blocked: bool
    unresolved_orders_count: int
    unresolved_positions_count: int
    open_positions_count: int

    @property
    def resume_allowed(self) -> bool:
        """Whether normal trading may resume."""
        return self.decision is RecoveryBootDecisionType.ALLOW_NORMAL_RESUME


def classify_recovery_boot(snapshot: RecoveryBootSnapshot) -> RecoveryBootDecision:
    """Classify recovery boot state from explicit Ledger/reconciliation truth."""
    _validate_snapshot(snapshot)
    unresolved_orders_count = sum(1 for state in snapshot.order_states if state.recovery_required)

    if not snapshot.recovery_boot_started:
        block_reason = RecoveryBootReason.RECOVERY_BOOT_NOT_STARTED
    elif unresolved_orders_count:
        block_reason = RecoveryBootReason.UNRESOLVED_ORDER_SENDS
    elif snapshot.unresolved_positions_count:
        block_reason = RecoveryBootReason.UNRESOLVED_POSITIONS
    elif not snapshot.exchange_evidence_complete:
        block_reason = RecoveryBootReason.INCOMPLETE_EXCHANGE_EVIDENCE
    elif not snapshot.reconciliation_completed:
        block_reason = RecoveryBootReason.RECONCILIATION_NOT_COMPLETED
    elif snapshot.open_positions_count and not snapshot.intentional_reconciled_position:
        block_reason = RecoveryBootReason.OPEN_POSITIONS_NOT_RECONCILED
    else:
        block_reason = None

    if block_reason is not None:
        return _block(
            block_reason,
            unresolved_orders_count=unresolved_orders_count,
            snapshot=snapshot,
        )
    if snapshot.flat_reconciled and snapshot.open_positions_count == 0:
        return _allow(RecoveryBootReason.FLAT_RECONCILED, snapshot)
    if snapshot.intentional_reconciled_position and snapshot.open_positions_count > 0:
        return _allow(RecoveryBootReason.INTENTIONAL_RECONCILED_POSITION, snapshot)

    return _block(
        RecoveryBootReason.RECONCILIATION_NOT_COMPLETED,
        unresolved_orders_count=unresolved_orders_count,
        snapshot=snapshot,
    )


def build_recovery_boot_snapshot(
    *,
    recovery_boot_started: bool,
    order_states: Iterable[OrderSendState] = (),
    open_positions_count: int = 0,
    unresolved_positions_count: int = 0,
    exchange_evidence_complete: bool = False,
    reconciliation_completed: bool = False,
    flat_reconciled: bool = False,
    intentional_reconciled_position: bool = False,
) -> RecoveryBootSnapshot:
    """Build a normalized immutable recovery boot snapshot."""
    return RecoveryBootSnapshot(
        recovery_boot_started=recovery_boot_started,
        order_states=tuple(order_states),
        open_positions_count=open_positions_count,
        unresolved_positions_count=unresolved_positions_count,
        exchange_evidence_complete=exchange_evidence_complete,
        reconciliation_completed=reconciliation_completed,
        flat_reconciled=flat_reconciled,
        intentional_reconciled_position=intentional_reconciled_position,
    )


def _allow(reason: RecoveryBootReason, snapshot: RecoveryBootSnapshot) -> RecoveryBootDecision:
    return RecoveryBootDecision(
        decision=RecoveryBootDecisionType.ALLOW_NORMAL_RESUME,
        reason=reason,
        normal_entries_blocked=False,
        unresolved_orders_count=0,
        unresolved_positions_count=snapshot.unresolved_positions_count,
        open_positions_count=snapshot.open_positions_count,
    )


def _block(
    reason: RecoveryBootReason,
    *,
    unresolved_orders_count: int,
    snapshot: RecoveryBootSnapshot,
) -> RecoveryBootDecision:
    return RecoveryBootDecision(
        decision=RecoveryBootDecisionType.BLOCK_NORMAL_ENTRIES,
        reason=reason,
        normal_entries_blocked=True,
        unresolved_orders_count=unresolved_orders_count,
        unresolved_positions_count=snapshot.unresolved_positions_count,
        open_positions_count=snapshot.open_positions_count,
    )


def _validate_snapshot(snapshot: RecoveryBootSnapshot) -> None:
    for field_name, value in (
        ("open_positions_count", snapshot.open_positions_count),
        ("unresolved_positions_count", snapshot.unresolved_positions_count),
    ):
        if isinstance(value, bool):
            raise TypeError(f"{field_name} must not be bool")
        if value < 0:
            raise ValueError(f"{field_name} must be non-negative")
    if snapshot.flat_reconciled and snapshot.open_positions_count:
        raise ValueError("flat_reconciled requires open_positions_count == 0")


__all__ = [
    "RecoveryBootDecision",
    "RecoveryBootDecisionType",
    "RecoveryBootReason",
    "RecoveryBootSnapshot",
    "build_recovery_boot_snapshot",
    "classify_recovery_boot",
]
