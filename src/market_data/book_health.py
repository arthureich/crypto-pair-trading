"""Pure L2 book health helpers for sequence, staleness, and resync decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BookHealthStatus(StrEnum):
    """Book health status derived only from supplied evidence."""

    HEALTHY = "HEALTHY"
    INVALID = "INVALID"


class BookHealthReason(StrEnum):
    """Stable reason codes for book health and resync decisions."""

    INITIAL_UPDATE = "INITIAL_UPDATE"
    IN_SEQUENCE = "IN_SEQUENCE"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    STALE_BOOK = "STALE_BOOK"
    SNAPSHOT_MISMATCH = "SNAPSHOT_MISMATCH"
    INCOMPLETE_SNAPSHOT = "INCOMPLETE_SNAPSHOT"


class SnapshotResyncDecisionType(StrEnum):
    """Whether local L2 state requires a fresh snapshot."""

    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"


@dataclass(frozen=True, slots=True)
class L2BookUpdate:
    """One normalized L2 update supplied by future market-data ingestion."""

    venue: str
    symbol: str
    sequence: int
    received_at_ms: int


@dataclass(frozen=True, slots=True)
class BookHealthDecision:
    """Pure classification for current local book usability."""

    status: BookHealthStatus
    reason: BookHealthReason
    venue: str
    symbol: str
    last_sequence: int | None
    entry_eligible: bool
    expected_sequence: int | None = None
    actual_sequence: int | None = None
    age_ms: int | None = None

    @property
    def healthy(self) -> bool:
        return self.status is BookHealthStatus.HEALTHY

    @property
    def valid(self) -> bool:
        return self.healthy

    @property
    def invalid(self) -> bool:
        return self.status is BookHealthStatus.INVALID


@dataclass(frozen=True, slots=True)
class BookHealthState:
    """Latest known local book state supplied to health checks."""

    venue: str
    symbol: str
    last_sequence: int
    last_update_received_at_ms: int
    status: BookHealthStatus | str = BookHealthStatus.HEALTHY
    reason: BookHealthReason | str = BookHealthReason.IN_SEQUENCE


@dataclass(frozen=True, slots=True)
class SnapshotEvidence:
    """Evidence comparing a local book with a snapshot boundary."""

    venue: str
    symbol: str
    snapshot_complete: bool
    local_last_sequence: int | None
    snapshot_last_sequence: int | None
    book_status: BookHealthStatus | str = BookHealthStatus.HEALTHY
    book_reason: BookHealthReason | str = BookHealthReason.IN_SEQUENCE


@dataclass(frozen=True, slots=True)
class SnapshotResyncDecision:
    """Pure decision for whether a book snapshot must be refreshed."""

    decision: SnapshotResyncDecisionType
    reason: BookHealthReason
    venue: str
    symbol: str
    local_last_sequence: int | None
    snapshot_last_sequence: int | None

    @property
    def resync_required(self) -> bool:
        return self.decision is SnapshotResyncDecisionType.REQUIRED


def classify_l2_update(
    update: L2BookUpdate,
    *,
    previous_last_sequence: int | None,
) -> BookHealthDecision:
    """Classify a supplied L2 update against the previous local sequence."""

    venue = _required_text("venue", update.venue)
    symbol = _required_text("symbol", update.symbol)
    sequence = _non_negative_int("sequence", update.sequence)
    _non_negative_int("received_at_ms", update.received_at_ms)

    if previous_last_sequence is None:
        return BookHealthDecision(
            status=BookHealthStatus.HEALTHY,
            reason=BookHealthReason.INITIAL_UPDATE,
            venue=venue,
            symbol=symbol,
            last_sequence=sequence,
            entry_eligible=True,
            actual_sequence=sequence,
        )

    previous_sequence = _non_negative_int("previous_last_sequence", previous_last_sequence)
    expected_sequence = previous_sequence + 1
    if sequence != expected_sequence:
        return BookHealthDecision(
            status=BookHealthStatus.INVALID,
            reason=BookHealthReason.SEQUENCE_GAP,
            venue=venue,
            symbol=symbol,
            last_sequence=previous_sequence,
            entry_eligible=False,
            expected_sequence=expected_sequence,
            actual_sequence=sequence,
        )

    return BookHealthDecision(
        status=BookHealthStatus.HEALTHY,
        reason=BookHealthReason.IN_SEQUENCE,
        venue=venue,
        symbol=symbol,
        last_sequence=sequence,
        entry_eligible=True,
        expected_sequence=expected_sequence,
        actual_sequence=sequence,
    )


def classify_book_staleness(
    state: BookHealthState,
    *,
    now_ms: int,
    stale_after_ms: int,
) -> BookHealthDecision:
    """Invalidate entry eligibility when latest local book evidence is stale."""

    venue = _required_text("venue", state.venue)
    symbol = _required_text("symbol", state.symbol)
    last_sequence = _non_negative_int("last_sequence", state.last_sequence)
    last_update_received_at_ms = _non_negative_int(
        "last_update_received_at_ms", state.last_update_received_at_ms
    )
    status = _coerce_status(state.status)
    reason = _coerce_reason(state.reason)
    now = _non_negative_int("now_ms", now_ms)
    stale_after = _positive_int("stale_after_ms", stale_after_ms)
    if now < last_update_received_at_ms:
        raise ValueError("now_ms must be greater than or equal to last_update_received_at_ms")

    age_ms = now - last_update_received_at_ms
    if status is BookHealthStatus.INVALID:
        return BookHealthDecision(
            status=BookHealthStatus.INVALID,
            reason=reason,
            venue=venue,
            symbol=symbol,
            last_sequence=last_sequence,
            entry_eligible=False,
            age_ms=age_ms,
        )
    if age_ms > stale_after:
        return BookHealthDecision(
            status=BookHealthStatus.INVALID,
            reason=BookHealthReason.STALE_BOOK,
            venue=venue,
            symbol=symbol,
            last_sequence=last_sequence,
            entry_eligible=False,
            age_ms=age_ms,
        )

    return BookHealthDecision(
        status=BookHealthStatus.HEALTHY,
        reason=reason,
        venue=venue,
        symbol=symbol,
        last_sequence=last_sequence,
        entry_eligible=True,
        age_ms=age_ms,
    )


def decide_snapshot_resync(evidence: SnapshotEvidence) -> SnapshotResyncDecision:
    """Require snapshot resync for incomplete, mismatched, or invalid book evidence."""

    venue = _required_text("venue", evidence.venue)
    symbol = _required_text("symbol", evidence.symbol)
    book_status = _coerce_status(evidence.book_status)
    book_reason = _coerce_reason(evidence.book_reason)
    local_last_sequence = _optional_non_negative_int(
        "local_last_sequence", evidence.local_last_sequence
    )
    snapshot_last_sequence = _optional_non_negative_int(
        "snapshot_last_sequence", evidence.snapshot_last_sequence
    )

    if not evidence.snapshot_complete or snapshot_last_sequence is None:
        return _resync_required(
            reason=BookHealthReason.INCOMPLETE_SNAPSHOT,
            venue=venue,
            symbol=symbol,
            local_last_sequence=local_last_sequence,
            snapshot_last_sequence=snapshot_last_sequence,
        )
    if book_status is BookHealthStatus.INVALID:
        return _resync_required(
            reason=book_reason,
            venue=venue,
            symbol=symbol,
            local_last_sequence=local_last_sequence,
            snapshot_last_sequence=snapshot_last_sequence,
        )
    if local_last_sequence != snapshot_last_sequence:
        return _resync_required(
            reason=BookHealthReason.SNAPSHOT_MISMATCH,
            venue=venue,
            symbol=symbol,
            local_last_sequence=local_last_sequence,
            snapshot_last_sequence=snapshot_last_sequence,
        )

    return SnapshotResyncDecision(
        decision=SnapshotResyncDecisionType.NOT_REQUIRED,
        reason=BookHealthReason.IN_SEQUENCE,
        venue=venue,
        symbol=symbol,
        local_last_sequence=local_last_sequence,
        snapshot_last_sequence=snapshot_last_sequence,
    )


def _resync_required(
    *,
    reason: BookHealthReason,
    venue: str,
    symbol: str,
    local_last_sequence: int | None,
    snapshot_last_sequence: int | None,
) -> SnapshotResyncDecision:
    return SnapshotResyncDecision(
        decision=SnapshotResyncDecisionType.REQUIRED,
        reason=reason,
        venue=venue,
        symbol=symbol,
        local_last_sequence=local_last_sequence,
        snapshot_last_sequence=snapshot_last_sequence,
    )


def _coerce_status(status: BookHealthStatus | str) -> BookHealthStatus:
    try:
        return BookHealthStatus(status)
    except ValueError as exc:
        raise ValueError(f"unsupported book health status: {status}") from exc


def _coerce_reason(reason: BookHealthReason | str) -> BookHealthReason:
    try:
        return BookHealthReason(reason)
    except ValueError as exc:
        raise ValueError(f"unsupported book health reason: {reason}") from exc


def _required_text(field_name: str, value: object) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _non_negative_int(field_name: str, value: int) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must not be bool")
    if not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _optional_non_negative_int(field_name: str, value: int | None) -> int | None:
    if value is None:
        return None
    return _non_negative_int(field_name, value)


def _positive_int(field_name: str, value: int) -> int:
    integer = _non_negative_int(field_name, value)
    if integer <= 0:
        raise ValueError(f"{field_name} must be positive")
    return integer


__all__ = [
    "BookHealthDecision",
    "BookHealthReason",
    "BookHealthState",
    "BookHealthStatus",
    "L2BookUpdate",
    "SnapshotEvidence",
    "SnapshotResyncDecision",
    "SnapshotResyncDecisionType",
    "classify_book_staleness",
    "classify_l2_update",
    "decide_snapshot_resync",
]
