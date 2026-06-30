"""Pure execution-quality features derived from local book evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.market_data.book_health import BookHealthDecision, SnapshotResyncDecision

BPS_DENOMINATOR = Decimal("10000")
DEPTH_5_BPS = Decimal("5")
DEPTH_10_BPS = Decimal("10")
MIN_VOLATILITY_OBSERVATIONS = 2


class ExecutionFeatureReason(StrEnum):
    """Stable usability reason codes for execution-derived features."""

    USABLE = "USABLE"
    INVALID_BOOK = "INVALID_BOOK"
    STALE_BOOK = "STALE_BOOK"
    RESYNC_REQUIRED = "RESYNC_REQUIRED"
    CROSSED_OR_EMPTY_BOOK = "CROSSED_OR_EMPTY_BOOK"


@dataclass(frozen=True, slots=True)
class BookLevel:
    """One L2 price level."""

    price: Decimal | str | int
    quantity: Decimal | str | int


@dataclass(frozen=True, slots=True)
class DepthBySide:
    """Aggregated depth within a configured basis-point band."""

    bid_quantity: Decimal
    ask_quantity: Decimal
    bid_notional: Decimal
    ask_notional: Decimal


@dataclass(frozen=True, slots=True)
class VolatilityObservation:
    """One mid-price observation available at or before ``observed_at_ms``."""

    observed_at_ms: int
    mid_price: Decimal


@dataclass(frozen=True, slots=True)
class VolatilityState:
    """Rolling mid-price observations for execution feature volatility."""

    observations: tuple[VolatilityObservation, ...] = ()


@dataclass(frozen=True, slots=True)
class VolatilityFeatures:
    """Windowed volatility estimates from historical mid-price observations."""

    state: VolatilityState
    volatility_1s: Decimal
    volatility_5s: Decimal


@dataclass(frozen=True, slots=True)
class BookExecutionFeatures:
    """Execution feature snapshot derived only from supplied book/evidence."""

    venue: str
    symbol: str
    generated_at_ms: int
    best_bid: Decimal | None
    best_ask: Decimal | None
    mid_price: Decimal | None
    spread_bps: Decimal | None
    depth_5_bps: DepthBySide
    depth_10_bps: DepthBySide
    order_book_imbalance: Decimal | None
    volatility_1s: Decimal
    volatility_5s: Decimal
    usable_for_trading: bool
    reason: ExecutionFeatureReason

    @property
    def unusable_for_trading(self) -> bool:
        return not self.usable_for_trading


def build_book_execution_features(
    *,
    venue: str,
    symbol: str,
    bids: Iterable[BookLevel],
    asks: Iterable[BookLevel],
    generated_at_ms: int,
    book_health: BookHealthDecision,
    snapshot_resync: SnapshotResyncDecision | None = None,
    volatility: VolatilityFeatures | None = None,
) -> BookExecutionFeatures:
    """Build one fail-closed execution feature snapshot from local evidence."""

    generated_at = _non_negative_int("generated_at_ms", generated_at_ms)
    reason = _feature_reason(book_health, snapshot_resync)
    try:
        normalized_bids = _normalize_levels(bids, descending=True)
        normalized_asks = _normalize_levels(asks, descending=False)
    except (TypeError, ValueError):
        return _empty_features(
            venue,
            symbol,
            generated_at,
            volatility,
            ExecutionFeatureReason.INVALID_BOOK,
        )

    if not normalized_bids or not normalized_asks:
        reason = ExecutionFeatureReason.CROSSED_OR_EMPTY_BOOK
        return _empty_features(venue, symbol, generated_at, volatility, reason)

    best_bid = normalized_bids[0].price
    best_ask = normalized_asks[0].price
    if best_bid >= best_ask:
        reason = ExecutionFeatureReason.CROSSED_OR_EMPTY_BOOK
        return _empty_features(venue, symbol, generated_at, volatility, reason)

    mid = mid_price(best_bid=best_bid, best_ask=best_ask)
    spread = spread_bps(best_bid=best_bid, best_ask=best_ask)
    depth_5 = depth_within_bps(normalized_bids, normalized_asks, mid_price=mid, bps=DEPTH_5_BPS)
    depth_10 = depth_within_bps(normalized_bids, normalized_asks, mid_price=mid, bps=DEPTH_10_BPS)
    imbalance = order_book_imbalance(normalized_bids, normalized_asks)
    vol = volatility or VolatilityFeatures(
        state=VolatilityState(),
        volatility_1s=Decimal("0"),
        volatility_5s=Decimal("0"),
    )

    return BookExecutionFeatures(
        venue=_required_text("venue", venue),
        symbol=_required_text("symbol", symbol),
        generated_at_ms=generated_at,
        best_bid=best_bid,
        best_ask=best_ask,
        mid_price=mid,
        spread_bps=spread,
        depth_5_bps=depth_5,
        depth_10_bps=depth_10,
        order_book_imbalance=imbalance,
        volatility_1s=vol.volatility_1s,
        volatility_5s=vol.volatility_5s,
        usable_for_trading=reason is ExecutionFeatureReason.USABLE,
        reason=reason,
    )


def mid_price(*, best_bid: Decimal | str | int, best_ask: Decimal | str | int) -> Decimal:
    """Return midpoint from positive best bid/ask."""

    bid = _positive_decimal("best_bid", best_bid)
    ask = _positive_decimal("best_ask", best_ask)
    if bid >= ask:
        raise ValueError("best_bid must be less than best_ask")
    return (bid + ask) / Decimal("2")


def spread_bps(*, best_bid: Decimal | str | int, best_ask: Decimal | str | int) -> Decimal:
    """Return spread in basis points over mid price."""

    bid = _positive_decimal("best_bid", best_bid)
    ask = _positive_decimal("best_ask", best_ask)
    mid = mid_price(best_bid=bid, best_ask=ask)
    return ((ask - bid) / mid) * BPS_DENOMINATOR


def depth_within_bps(
    bids: Iterable[BookLevel],
    asks: Iterable[BookLevel],
    *,
    mid_price: Decimal | str | int,
    bps: Decimal | str | int,
) -> DepthBySide:
    """Aggregate bid/ask depth inside ``bps`` from midpoint."""

    mid = _positive_decimal("mid_price", mid_price)
    band = _non_negative_decimal("bps", bps) / BPS_DENOMINATOR
    min_bid = mid * (Decimal("1") - band)
    max_ask = mid * (Decimal("1") + band)
    bid_qty = Decimal("0")
    bid_notional = Decimal("0")
    ask_qty = Decimal("0")
    ask_notional = Decimal("0")

    for level in _normalize_levels(bids, descending=True):
        if level.price >= min_bid:
            bid_qty += level.quantity
            bid_notional += level.price * level.quantity
    for level in _normalize_levels(asks, descending=False):
        if level.price <= max_ask:
            ask_qty += level.quantity
            ask_notional += level.price * level.quantity

    return DepthBySide(
        bid_quantity=bid_qty,
        ask_quantity=ask_qty,
        bid_notional=bid_notional,
        ask_notional=ask_notional,
    )


def order_book_imbalance(
    bids: Iterable[BookLevel],
    asks: Iterable[BookLevel],
) -> Decimal | None:
    """Return deterministic top-book quantity imbalance."""

    bid_qty = sum(
        (level.quantity for level in _normalize_levels(bids, descending=True)),
        Decimal("0"),
    )
    ask_qty = sum(
        (level.quantity for level in _normalize_levels(asks, descending=False)),
        Decimal("0"),
    )
    total = bid_qty + ask_qty
    if total == 0:
        return None
    return (bid_qty - ask_qty) / total


def update_volatility(
    previous: VolatilityState | None,
    *,
    mid_price: Decimal | str | int,
    observed_at_ms: int,
) -> VolatilityFeatures:
    """Update rolling 1s/5s volatility without future observations or pandas."""

    observed_at = _non_negative_int("observed_at_ms", observed_at_ms)
    mid = _positive_decimal("mid_price", mid_price)
    existing = previous.observations if previous is not None else ()
    if existing and observed_at < existing[-1].observed_at_ms:
        raise ValueError("observed_at_ms must not move backward")

    cutoff = observed_at - 5_000
    observations = tuple(obs for obs in existing if obs.observed_at_ms >= cutoff) + (
        VolatilityObservation(observed_at_ms=observed_at, mid_price=mid),
    )
    state = VolatilityState(observations=observations)
    return VolatilityFeatures(
        state=state,
        volatility_1s=_window_volatility(observations, observed_at_ms=observed_at, window_ms=1_000),
        volatility_5s=_window_volatility(observations, observed_at_ms=observed_at, window_ms=5_000),
    )


def _window_volatility(
    observations: tuple[VolatilityObservation, ...],
    *,
    observed_at_ms: int,
    window_ms: int,
) -> Decimal:
    window = [
        obs.mid_price
        for obs in observations
        if observed_at_ms - window_ms <= obs.observed_at_ms <= observed_at_ms
    ]
    if len(window) < MIN_VOLATILITY_OBSERVATIONS:
        return Decimal("0")
    returns = [
        abs((current - previous_price) / previous_price)
        for previous_price, current in zip(window, window[1:], strict=False)
        if previous_price > 0
    ]
    if not returns:
        return Decimal("0")
    return sum(returns, Decimal("0")) / Decimal(len(returns))


def _feature_reason(
    book_health: BookHealthDecision,
    snapshot_resync: SnapshotResyncDecision | None,
) -> ExecutionFeatureReason:
    if snapshot_resync is not None and snapshot_resync.resync_required:
        return ExecutionFeatureReason.RESYNC_REQUIRED
    if _enum_value(book_health.status) == "INVALID":
        if _enum_value(book_health.reason) == "STALE_BOOK":
            return ExecutionFeatureReason.STALE_BOOK
        return ExecutionFeatureReason.INVALID_BOOK
    if not book_health.entry_eligible:
        return ExecutionFeatureReason.INVALID_BOOK
    return ExecutionFeatureReason.USABLE


def _empty_features(
    venue: str,
    symbol: str,
    generated_at_ms: int,
    volatility: VolatilityFeatures | None,
    reason: ExecutionFeatureReason,
) -> BookExecutionFeatures:
    empty_depth = DepthBySide(
        bid_quantity=Decimal("0"),
        ask_quantity=Decimal("0"),
        bid_notional=Decimal("0"),
        ask_notional=Decimal("0"),
    )
    vol = volatility or VolatilityFeatures(
        state=VolatilityState(),
        volatility_1s=Decimal("0"),
        volatility_5s=Decimal("0"),
    )
    return BookExecutionFeatures(
        venue=_required_text("venue", venue),
        symbol=_required_text("symbol", symbol),
        generated_at_ms=generated_at_ms,
        best_bid=None,
        best_ask=None,
        mid_price=None,
        spread_bps=None,
        depth_5_bps=empty_depth,
        depth_10_bps=empty_depth,
        order_book_imbalance=None,
        volatility_1s=vol.volatility_1s,
        volatility_5s=vol.volatility_5s,
        usable_for_trading=False,
        reason=reason,
    )


def _normalize_levels(levels: Iterable[BookLevel], *, descending: bool) -> tuple[BookLevel, ...]:
    normalized = tuple(
        normalized_level
        for level in levels
        if (
            normalized_level := BookLevel(
                price=_positive_decimal("price", level.price),
                quantity=_non_negative_decimal("quantity", level.quantity),
            )
        ).quantity
        > 0
    )
    return tuple(sorted(normalized, key=lambda level: level.price, reverse=descending))


def _enum_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _required_text(field_name: str, value: object) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _non_negative_int(field_name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _positive_decimal(field_name: str, value: Decimal | str | int) -> Decimal:
    decimal = _decimal(field_name, value)
    if decimal <= 0:
        raise ValueError(f"{field_name} must be positive")
    return decimal


def _non_negative_decimal(field_name: str, value: Decimal | str | int) -> Decimal:
    decimal = _decimal(field_name, value)
    if decimal < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return decimal


def _decimal(field_name: str, value: Decimal | str | int) -> Decimal:
    if isinstance(value, bool | float):
        raise TypeError(f"{field_name} must be Decimal, str, or int")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be decimal-compatible") from exc


__all__ = [
    "BookExecutionFeatures",
    "BookLevel",
    "DepthBySide",
    "ExecutionFeatureReason",
    "VolatilityFeatures",
    "VolatilityObservation",
    "VolatilityState",
    "build_book_execution_features",
    "depth_within_bps",
    "mid_price",
    "order_book_imbalance",
    "spread_bps",
    "update_volatility",
]
