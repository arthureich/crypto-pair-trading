from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data import (
    BookHealthReason,
    BookHealthState,
    BookHealthStatus,
    L2BookUpdate,
    SnapshotEvidence,
    SnapshotResyncDecisionType,
    classify_book_staleness,
    classify_l2_update,
    decide_snapshot_resync,
)


def _update(sequence: int = 101) -> L2BookUpdate:
    return L2BookUpdate(
        venue="BINANCE",
        symbol="BTCUSDT",
        sequence=sequence,
        received_at_ms=1_000,
    )


def test_l2_update_dataclass_and_book_health_enums_exist() -> None:
    update = _update()

    assert update.sequence == 101
    assert BookHealthStatus.HEALTHY.value == "HEALTHY"
    assert BookHealthStatus.INVALID.value == "INVALID"
    assert BookHealthReason.SEQUENCE_GAP.value == "SEQUENCE_GAP"


def test_initial_update_is_healthy_and_entry_eligible() -> None:
    decision = classify_l2_update(_update(sequence=50), previous_last_sequence=None)

    assert decision.status is BookHealthStatus.HEALTHY
    assert decision.reason is BookHealthReason.INITIAL_UPDATE
    assert decision.valid is True
    assert decision.entry_eligible is True
    assert decision.last_sequence == 50


def test_in_sequence_update_classifies_book_as_healthy_and_valid() -> None:
    decision = classify_l2_update(_update(sequence=101), previous_last_sequence=100)

    assert decision.status is BookHealthStatus.HEALTHY
    assert decision.reason is BookHealthReason.IN_SEQUENCE
    assert decision.healthy is True
    assert decision.valid is True
    assert decision.entry_eligible is True
    assert decision.expected_sequence == 101
    assert decision.actual_sequence == 101
    assert decision.last_sequence == 101


def test_sequence_gap_invalidates_book_and_blocks_entry_eligibility() -> None:
    decision = classify_l2_update(_update(sequence=103), previous_last_sequence=100)

    assert decision.status is BookHealthStatus.INVALID
    assert decision.reason is BookHealthReason.SEQUENCE_GAP
    assert decision.invalid is True
    assert decision.entry_eligible is False
    assert decision.expected_sequence == 101
    assert decision.actual_sequence == 103
    assert decision.last_sequence == 100


def test_stale_book_evidence_invalidates_entry_eligibility() -> None:
    decision = classify_book_staleness(
        BookHealthState(
            venue="BINANCE",
            symbol="BTCUSDT",
            last_sequence=101,
            last_update_received_at_ms=1_000,
        ),
        now_ms=1_601,
        stale_after_ms=600,
    )

    assert decision.status is BookHealthStatus.INVALID
    assert decision.reason is BookHealthReason.STALE_BOOK
    assert decision.entry_eligible is False
    assert decision.age_ms == 601


def test_fresh_book_evidence_remains_entry_eligible() -> None:
    decision = classify_book_staleness(
        BookHealthState(
            venue="BINANCE",
            symbol="BTCUSDT",
            last_sequence=101,
            last_update_received_at_ms=1_000,
        ),
        now_ms=1_600,
        stale_after_ms=600,
    )

    assert decision.status is BookHealthStatus.HEALTHY
    assert decision.reason is BookHealthReason.IN_SEQUENCE
    assert decision.entry_eligible is True
    assert decision.age_ms == 600


def test_existing_invalid_book_state_remains_entry_ineligible() -> None:
    decision = classify_book_staleness(
        BookHealthState(
            venue="BINANCE",
            symbol="BTCUSDT",
            last_sequence=100,
            last_update_received_at_ms=1_000,
            status=BookHealthStatus.INVALID,
            reason=BookHealthReason.SEQUENCE_GAP,
        ),
        now_ms=1_100,
        stale_after_ms=600,
    )

    assert decision.status is BookHealthStatus.INVALID
    assert decision.reason is BookHealthReason.SEQUENCE_GAP
    assert decision.entry_eligible is False


def test_snapshot_mismatch_requires_resync() -> None:
    decision = decide_snapshot_resync(
        SnapshotEvidence(
            venue="BINANCE",
            symbol="BTCUSDT",
            snapshot_complete=True,
            local_last_sequence=101,
            snapshot_last_sequence=100,
        )
    )

    assert decision.decision is SnapshotResyncDecisionType.REQUIRED
    assert decision.resync_required is True
    assert decision.reason is BookHealthReason.SNAPSHOT_MISMATCH


def test_incomplete_snapshot_requires_resync() -> None:
    decision = decide_snapshot_resync(
        SnapshotEvidence(
            venue="BINANCE",
            symbol="BTCUSDT",
            snapshot_complete=False,
            local_last_sequence=101,
            snapshot_last_sequence=None,
        )
    )

    assert decision.decision is SnapshotResyncDecisionType.REQUIRED
    assert decision.resync_required is True
    assert decision.reason is BookHealthReason.INCOMPLETE_SNAPSHOT


def test_missing_snapshot_sequence_requires_resync_even_when_marked_complete() -> None:
    decision = decide_snapshot_resync(
        SnapshotEvidence(
            venue="BINANCE",
            symbol="BTCUSDT",
            snapshot_complete=True,
            local_last_sequence=101,
            snapshot_last_sequence=None,
        )
    )

    assert decision.decision is SnapshotResyncDecisionType.REQUIRED
    assert decision.resync_required is True
    assert decision.reason is BookHealthReason.INCOMPLETE_SNAPSHOT


def test_healthy_in_sequence_update_does_not_require_resync() -> None:
    update_decision = classify_l2_update(_update(sequence=101), previous_last_sequence=100)
    resync_decision = decide_snapshot_resync(
        SnapshotEvidence(
            venue="BINANCE",
            symbol="BTCUSDT",
            snapshot_complete=True,
            local_last_sequence=update_decision.last_sequence,
            snapshot_last_sequence=101,
            book_status=update_decision.status,
        )
    )

    assert update_decision.status is BookHealthStatus.HEALTHY
    assert resync_decision.decision is SnapshotResyncDecisionType.NOT_REQUIRED
    assert resync_decision.resync_required is False
    assert resync_decision.reason is BookHealthReason.IN_SEQUENCE


def test_invalid_book_status_requires_snapshot_resync() -> None:
    decision = decide_snapshot_resync(
        SnapshotEvidence(
            venue="BINANCE",
            symbol="BTCUSDT",
            snapshot_complete=True,
            local_last_sequence=100,
            snapshot_last_sequence=100,
            book_status=BookHealthStatus.INVALID,
            book_reason=BookHealthReason.SEQUENCE_GAP,
        )
    )

    assert decision.resync_required is True
    assert decision.reason is BookHealthReason.SEQUENCE_GAP


def test_stale_book_status_requires_snapshot_resync() -> None:
    decision = decide_snapshot_resync(
        SnapshotEvidence(
            venue="BINANCE",
            symbol="BTCUSDT",
            snapshot_complete=True,
            local_last_sequence=101,
            snapshot_last_sequence=101,
            book_status=BookHealthStatus.INVALID,
            book_reason=BookHealthReason.STALE_BOOK,
        )
    )

    assert decision.resync_required is True
    assert decision.reason is BookHealthReason.STALE_BOOK


def test_helpers_are_pure_and_inputs_are_immutable() -> None:
    update = _update(sequence=101)

    first = classify_l2_update(update, previous_last_sequence=100)
    second = classify_l2_update(update, previous_last_sequence=100)

    assert first == second
    with pytest.raises(FrozenInstanceError):
        update.sequence = 102  # type: ignore[misc]


@pytest.mark.parametrize(
    "update,previous_last_sequence,match",
    (
        (L2BookUpdate("", "BTCUSDT", 101, 1_000), 100, "venue is required"),
        (L2BookUpdate("BINANCE", "", 101, 1_000), 100, "symbol is required"),
        (L2BookUpdate("BINANCE", "BTCUSDT", -1, 1_000), 100, "sequence"),
        (L2BookUpdate("BINANCE", "BTCUSDT", 101, -1), 100, "received_at_ms"),
        (L2BookUpdate("BINANCE", "BTCUSDT", 101, 1_000), -1, "previous_last_sequence"),
    ),
)
def test_invalid_sequence_inputs_raise(
    update: L2BookUpdate,
    previous_last_sequence: int | None,
    match: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=match):
        classify_l2_update(update, previous_last_sequence=previous_last_sequence)


def test_staleness_rejects_clock_regression() -> None:
    with pytest.raises(ValueError, match="now_ms"):
        classify_book_staleness(
            BookHealthState(
                venue="BINANCE",
                symbol="BTCUSDT",
                last_sequence=101,
                last_update_received_at_ms=1_000,
            ),
            now_ms=999,
            stale_after_ms=600,
        )
