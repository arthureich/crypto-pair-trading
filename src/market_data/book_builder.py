"""Small pure local L2 order book builder."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class BookApplyReason(StrEnum):
    """Stable reason codes for snapshot and diff application."""

    SNAPSHOT_APPLIED = "SNAPSHOT_APPLIED"
    DIFF_APPLIED = "DIFF_APPLIED"
    OLD_UPDATE = "OLD_UPDATE"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    OUT_OF_SYNC = "OUT_OF_SYNC"


@dataclass(frozen=True, slots=True)
class BookLevel:
    """One normalized L2 book level."""

    price: float
    qty: float


BookLevelInput = BookLevel | tuple[float, float] | list[float]


@dataclass(frozen=True, slots=True)
class BookSnapshot:
    """Full L2 snapshot used to seed or resync a local order book."""

    venue: str
    symbol: str
    sequence: int
    received_at_ms: int
    bids: tuple[BookLevelInput, ...]
    asks: tuple[BookLevelInput, ...]


@dataclass(frozen=True, slots=True)
class BookDiffUpdate:
    """Incremental L2 update applied after a snapshot."""

    venue: str
    symbol: str
    sequence: int
    received_at_ms: int
    bids: tuple[BookLevelInput, ...] = ()
    asks: tuple[BookLevelInput, ...] = ()


@dataclass(frozen=True, slots=True)
class BookApplyResult:
    """Outcome of applying, discarding, or rejecting book evidence."""

    applied: bool
    reason: BookApplyReason
    venue: str
    symbol: str
    last_sequence: int | None
    in_sync: bool
    valid: bool
    needs_resync: bool
    expected_sequence: int | None = None
    actual_sequence: int | None = None


class LocalOrderBook:
    """Mutable in-memory L2 book with deterministic snapshot and diff handling."""

    def __init__(self, *, venue: str, symbol: str) -> None:
        self.venue = _required_text("venue", venue)
        self.symbol = _required_text("symbol", symbol)
        self._bids: dict[float, float] = {}
        self._asks: dict[float, float] = {}
        self.last_sequence: int | None = None
        self.last_update_received_at_ms: int | None = None
        self.in_sync = False
        self.needs_resync = True

    @property
    def bids(self) -> tuple[BookLevel, ...]:
        """Bid levels sorted from best to worst."""

        return tuple(
            BookLevel(price=price, qty=qty)
            for price, qty in sorted(self._bids.items(), reverse=True)
        )

    @property
    def asks(self) -> tuple[BookLevel, ...]:
        """Ask levels sorted from best to worst."""

        return tuple(BookLevel(price=price, qty=qty) for price, qty in sorted(self._asks.items()))

    @property
    def best_bid(self) -> float | None:
        """Best bid price, when the bid side is populated."""

        if not self._bids:
            return None
        return max(self._bids)

    @property
    def best_ask(self) -> float | None:
        """Best ask price, when the ask side is populated."""

        if not self._asks:
            return None
        return min(self._asks)

    @property
    def best_bid_level(self) -> BookLevel | None:
        """Best bid price and quantity, when available."""

        price = self.best_bid
        if price is None:
            return None
        return BookLevel(price=price, qty=self._bids[price])

    @property
    def best_ask_level(self) -> BookLevel | None:
        """Best ask price and quantity, when available."""

        price = self.best_ask
        if price is None:
            return None
        return BookLevel(price=price, qty=self._asks[price])

    @property
    def valid(self) -> bool:
        """Whether the local book is usable before applying a staleness threshold."""

        return self.in_sync and not self.needs_resync and bool(self._bids) and bool(self._asks)

    def book_age_ms(self, *, now_ms: int) -> int | None:
        """Return the age of the latest accepted snapshot or diff."""

        now = _non_negative_int("now_ms", now_ms)
        if self.last_update_received_at_ms is None:
            return None
        if now < self.last_update_received_at_ms:
            raise ValueError("now_ms must be greater than or equal to last_update_received_at_ms")
        return now - self.last_update_received_at_ms

    def is_stale(self, *, now_ms: int, stale_after_ms: int) -> bool:
        """Detect staleness using only caller-supplied time evidence."""

        stale_after = _positive_int("stale_after_ms", stale_after_ms)
        age = self.book_age_ms(now_ms=now_ms)
        return age is None or age > stale_after

    def valid_at(self, *, now_ms: int, stale_after_ms: int) -> bool:
        """Return book usability including staleness."""

        return self.valid and not self.is_stale(now_ms=now_ms, stale_after_ms=stale_after_ms)

    def apply_snapshot(self, snapshot: BookSnapshot) -> BookApplyResult:
        """Replace local state with a full L2 snapshot."""

        self._validate_event_identity(snapshot.venue, snapshot.symbol)
        sequence = _non_negative_int("sequence", snapshot.sequence)
        received_at_ms = _non_negative_int("received_at_ms", snapshot.received_at_ms)

        self._bids = _levels_to_map("bids", snapshot.bids)
        self._asks = _levels_to_map("asks", snapshot.asks)
        self.last_sequence = sequence
        self.last_update_received_at_ms = received_at_ms
        self.in_sync = True
        self.needs_resync = False
        return self._result(applied=True, reason=BookApplyReason.SNAPSHOT_APPLIED)

    def apply_diff(self, update: BookDiffUpdate) -> BookApplyResult:
        """Apply one incremental L2 update when it is exactly in sequence."""

        self._validate_event_identity(update.venue, update.symbol)
        sequence = _non_negative_int("sequence", update.sequence)
        received_at_ms = _non_negative_int("received_at_ms", update.received_at_ms)

        if self.last_sequence is None:
            self.in_sync = False
            self.needs_resync = True
            return self._result(
                applied=False,
                reason=BookApplyReason.OUT_OF_SYNC,
                actual_sequence=sequence,
            )

        if sequence <= self.last_sequence:
            return self._result(
                applied=False,
                reason=BookApplyReason.OLD_UPDATE,
                expected_sequence=self.last_sequence + 1,
                actual_sequence=sequence,
            )

        expected_sequence = self.last_sequence + 1
        if sequence != expected_sequence:
            self.in_sync = False
            self.needs_resync = True
            return self._result(
                applied=False,
                reason=BookApplyReason.SEQUENCE_GAP,
                expected_sequence=expected_sequence,
                actual_sequence=sequence,
            )

        if not self.in_sync or self.needs_resync:
            return self._result(
                applied=False,
                reason=BookApplyReason.OUT_OF_SYNC,
                expected_sequence=expected_sequence,
                actual_sequence=sequence,
            )

        self._apply_side_updates(self._bids, "bids", update.bids)
        self._apply_side_updates(self._asks, "asks", update.asks)
        self.last_sequence = sequence
        self.last_update_received_at_ms = received_at_ms
        return self._result(
            applied=True,
            reason=BookApplyReason.DIFF_APPLIED,
            expected_sequence=expected_sequence,
            actual_sequence=sequence,
        )

    def _apply_side_updates(
        self,
        side: dict[float, float],
        side_name: str,
        levels: Iterable[BookLevelInput],
    ) -> None:
        for level in levels:
            normalized = _normalize_level(side_name, level)
            if normalized.qty == 0:
                side.pop(normalized.price, None)
            else:
                side[normalized.price] = normalized.qty

    def _validate_event_identity(self, venue: str, symbol: str) -> None:
        event_venue = _required_text("venue", venue)
        event_symbol = _required_text("symbol", symbol)
        if event_venue != self.venue:
            raise ValueError(f"venue mismatch: expected {self.venue}, got {event_venue}")
        if event_symbol != self.symbol:
            raise ValueError(f"symbol mismatch: expected {self.symbol}, got {event_symbol}")

    def _result(
        self,
        *,
        applied: bool,
        reason: BookApplyReason,
        expected_sequence: int | None = None,
        actual_sequence: int | None = None,
    ) -> BookApplyResult:
        return BookApplyResult(
            applied=applied,
            reason=reason,
            venue=self.venue,
            symbol=self.symbol,
            last_sequence=self.last_sequence,
            in_sync=self.in_sync,
            valid=self.valid,
            needs_resync=self.needs_resync,
            expected_sequence=expected_sequence,
            actual_sequence=actual_sequence,
        )


BookBuilder = LocalOrderBook


def _levels_to_map(side_name: str, levels: Iterable[BookLevelInput]) -> dict[float, float]:
    normalized_levels: dict[float, float] = {}
    for level in levels:
        normalized = _normalize_level(side_name, level)
        if normalized.qty > 0:
            normalized_levels[normalized.price] = normalized.qty
    return normalized_levels


def _normalize_level(side_name: str, level: BookLevelInput) -> BookLevel:
    if isinstance(level, BookLevel):
        price = level.price
        qty = level.qty
    else:
        try:
            price, qty = level
        except ValueError as exc:
            raise ValueError(f"{side_name} level must contain price and qty") from exc

    normalized_price = _positive_float(f"{side_name}.price", price)
    normalized_qty = _non_negative_float(f"{side_name}.qty", qty)
    return BookLevel(price=normalized_price, qty=normalized_qty)


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


def _positive_int(field_name: str, value: int) -> int:
    integer = _non_negative_int(field_name, value)
    if integer <= 0:
        raise ValueError(f"{field_name} must be positive")
    return integer


def _positive_float(field_name: str, value: float) -> float:
    number = _finite_float(field_name, value)
    if number <= 0:
        raise ValueError(f"{field_name} must be positive")
    return number


def _non_negative_float(field_name: str, value: float) -> float:
    number = _finite_float(field_name, value)
    if number < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return number


def _finite_float(field_name: str, value: float) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must not be bool")
    if not isinstance(value, int | float):
        raise TypeError(f"{field_name} must be numeric")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


__all__ = [
    "BookApplyReason",
    "BookApplyResult",
    "BookBuilder",
    "BookDiffUpdate",
    "BookLevel",
    "BookSnapshot",
    "LocalOrderBook",
]
