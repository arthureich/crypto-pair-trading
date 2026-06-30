from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data import (
    BookApplyReason,
    BookDiffUpdate,
    BookLevel,
    BookSnapshot,
    LocalOrderBook,
)


def _book() -> LocalOrderBook:
    return LocalOrderBook(venue="BINANCE", symbol="BTCUSDT")


def _snapshot(sequence: int = 100, received_at_ms: int = 1_000) -> BookSnapshot:
    return BookSnapshot(
        venue="BINANCE",
        symbol="BTCUSDT",
        sequence=sequence,
        received_at_ms=received_at_ms,
        bids=((99.0, 1.0), (98.0, 2.0)),
        asks=((101.0, 1.5), (102.0, 3.0)),
    )


def _diff(
    sequence: int,
    *,
    received_at_ms: int = 1_100,
    bids: tuple[BookLevel | tuple[float, float] | list[float], ...] = (),
    asks: tuple[BookLevel | tuple[float, float] | list[float], ...] = (),
) -> BookDiffUpdate:
    return BookDiffUpdate(
        venue="BINANCE",
        symbol="BTCUSDT",
        sequence=sequence,
        received_at_ms=received_at_ms,
        bids=bids,
        asks=asks,
    )


def test_snapshot_is_applied_and_best_prices_are_exposed() -> None:
    book = _book()

    result = book.apply_snapshot(_snapshot())

    assert result.applied is True
    assert result.reason is BookApplyReason.SNAPSHOT_APPLIED
    assert book.last_sequence == 100
    assert book.in_sync is True
    assert book.valid is True
    assert book.needs_resync is False
    assert book.best_bid == 99.0
    assert book.best_ask == 101.0
    assert book.best_bid_level == BookLevel(price=99.0, qty=1.0)
    assert book.best_ask_level == BookLevel(price=101.0, qty=1.5)
    assert book.bids == (BookLevel(99.0, 1.0), BookLevel(98.0, 2.0))
    assert book.asks == (BookLevel(101.0, 1.5), BookLevel(102.0, 3.0))


def test_diff_update_in_sequence_updates_bid_and_ask_levels() -> None:
    book = _book()
    book.apply_snapshot(_snapshot())

    result = book.apply_diff(
        _diff(
            101,
            bids=((100.0, 4.0),),
            asks=((100.5, 2.5),),
        )
    )

    assert result.applied is True
    assert result.reason is BookApplyReason.DIFF_APPLIED
    assert result.expected_sequence == 101
    assert result.actual_sequence == 101
    assert book.last_sequence == 101
    assert book.best_bid == 100.0
    assert book.best_ask == 100.5
    assert book.best_bid_level == BookLevel(price=100.0, qty=4.0)
    assert book.best_ask_level == BookLevel(price=100.5, qty=2.5)


def test_qty_zero_removes_price_level() -> None:
    book = _book()
    book.apply_snapshot(_snapshot())
    book.apply_diff(_diff(101, bids=((99.0, 0.0),), asks=((101.0, 0.0),)))

    assert book.best_bid == 98.0
    assert book.best_ask == 102.0
    assert BookLevel(price=99.0, qty=1.0) not in book.bids
    assert BookLevel(price=101.0, qty=1.5) not in book.asks


def test_old_or_duplicate_event_is_discarded_without_corrupting_state() -> None:
    book = _book()
    book.apply_snapshot(_snapshot())
    book.apply_diff(_diff(101, bids=((100.0, 4.0),), asks=((100.5, 2.5),)))

    duplicate = book.apply_diff(_diff(101, bids=((101.0, 99.0),), asks=((100.1, 99.0),)))
    old = book.apply_diff(_diff(100, bids=((101.0, 99.0),), asks=((100.1, 99.0),)))

    assert duplicate.applied is False
    assert duplicate.reason is BookApplyReason.OLD_UPDATE
    assert old.applied is False
    assert old.reason is BookApplyReason.OLD_UPDATE
    assert book.last_sequence == 101
    assert book.in_sync is True
    assert book.valid is True
    assert book.needs_resync is False
    assert book.best_bid == 100.0
    assert book.best_ask == 100.5
    assert book.best_bid_level == BookLevel(price=100.0, qty=4.0)
    assert book.best_ask_level == BookLevel(price=100.5, qty=2.5)


def test_sequence_gap_invalidates_book_and_marks_resync_required() -> None:
    book = _book()
    book.apply_snapshot(_snapshot())

    result = book.apply_diff(_diff(103, bids=((100.0, 4.0),)))

    assert result.applied is False
    assert result.reason is BookApplyReason.SEQUENCE_GAP
    assert result.expected_sequence == 101
    assert result.actual_sequence == 103
    assert book.last_sequence == 100
    assert book.in_sync is False
    assert book.valid is False
    assert book.needs_resync is True
    assert book.best_bid == 99.0


def test_diff_after_gap_is_not_applied_until_snapshot_resync() -> None:
    book = _book()
    book.apply_snapshot(_snapshot())
    book.apply_diff(_diff(103, bids=((100.0, 4.0),)))

    result = book.apply_diff(_diff(101, bids=((100.0, 4.0),)))

    assert result.applied is False
    assert result.reason is BookApplyReason.OUT_OF_SYNC
    assert book.last_sequence == 100
    assert book.in_sync is False
    assert book.valid is False
    assert book.needs_resync is True
    assert book.best_bid == 99.0


def test_stale_book_is_detected_with_age_ms() -> None:
    book = _book()
    book.apply_snapshot(_snapshot(received_at_ms=1_000))

    assert book.book_age_ms(now_ms=1_600) == 600
    assert book.is_stale(now_ms=1_600, stale_after_ms=600) is False
    assert book.valid_at(now_ms=1_600, stale_after_ms=600) is True
    assert book.book_age_ms(now_ms=1_601) == 601
    assert book.is_stale(now_ms=1_601, stale_after_ms=600) is True
    assert book.valid_at(now_ms=1_601, stale_after_ms=600) is False


@pytest.mark.parametrize(
    "bids,asks",
    (
        ((), ((101.0, 1.5),)),
        (((99.0, 1.0),), ()),
    ),
)
def test_book_without_bids_or_asks_is_invalid(
    bids: tuple[tuple[float, float], ...],
    asks: tuple[tuple[float, float], ...],
) -> None:
    book = _book()

    result = book.apply_snapshot(
        BookSnapshot(
            venue="BINANCE",
            symbol="BTCUSDT",
            sequence=100,
            received_at_ms=1_000,
            bids=bids,
            asks=asks,
        )
    )

    assert result.applied is True
    assert book.in_sync is True
    assert book.valid is False
    assert book.needs_resync is False


def test_snapshot_can_resync_after_gap() -> None:
    book = _book()
    book.apply_snapshot(_snapshot(sequence=100))
    book.apply_diff(_diff(103))

    result = book.apply_snapshot(_snapshot(sequence=200, received_at_ms=2_000))

    assert result.applied is True
    assert result.reason is BookApplyReason.SNAPSHOT_APPLIED
    assert book.last_sequence == 200
    assert book.in_sync is True
    assert book.valid is True
    assert book.needs_resync is False
    assert book.book_age_ms(now_ms=2_025) == 25
