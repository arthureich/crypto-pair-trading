"""Realistic top-of-book fill simulation for the Sprint 9 executable backtest.

This module never assumes a fill. It consumes only real, checksum-verified
top-of-book quotes (best bid/ask + quantity at that single level) already
downloaded for Sprint 7/8 -- it never fabricates depth beyond level 1. All
consumption math reuses ``estimate_slippage`` from
``src.execution.slippage_estimator`` (already reviewed and tested in Sprint 6)
instead of duplicating book-consumption logic.

ACK_UNKNOWN here mirrors the real invariant from
``src.execution.ack_guard``: an ACK_UNKNOWN order is not "no fill", it is
"fill unknown until reconciled". The fill result computed here IS the truth
the backtest will eventually learn; ACK_UNKNOWN only adds a reconciliation
delay before that truth becomes usable by the caller (e.g. before an exit
order may be placed on the same leg).
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from src.execution.ack_guard import AckGuardOrderStatus
from src.execution.slippage_estimator import (
    BookLevel,
    SlippageEstimate,
    SlippageRequest,
    SlippageSide,
    estimate_slippage,
)

DEFAULT_LATENCY_MS = 250
DEFAULT_LIMIT_TTL_MS = 5_000
DEFAULT_ACK_UNKNOWN_RATE = 0.02
DEFAULT_RECONCILIATION_LATENCY_MS = 2_000
_HASH_HEX_DIGITS = 8
_HASH_MAX_VALUE = 16**_HASH_HEX_DIGITS - 1


class OrderType(StrEnum):
    """Supported simulated order types."""

    MARKET_IOC = "MARKET_IOC"
    LIMIT = "LIMIT"


class FillStatus(StrEnum):
    """Outcome of one simulated order against real top-of-book quotes."""

    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    EXPIRED = "EXPIRED"
    NO_QUOTE = "NO_QUOTE"


class FillModelError(ValueError):
    """Raised when fill-model inputs are invalid."""


@dataclass(frozen=True, slots=True)
class TopOfBookQuote:
    """One verified top-of-book observation (level 1 only, no fabricated depth)."""

    event_time: int
    best_bid: float
    best_ask: float
    best_bid_qty: float
    best_ask_qty: float

    def __post_init__(self) -> None:
        if self.best_bid <= 0.0 or self.best_ask <= 0.0:
            raise FillModelError("quote prices must be positive")
        if self.best_ask < self.best_bid:
            raise FillModelError("quote is crossed: best_ask < best_bid")
        if self.best_bid_qty < 0.0 or self.best_ask_qty < 0.0:
            raise FillModelError("quote quantities must be non-negative")


@dataclass(frozen=True, slots=True)
class FillModelConfig:
    """Timing and reliability controls for simulated order fills."""

    latency_ms: int = DEFAULT_LATENCY_MS
    limit_ttl_ms: int = DEFAULT_LIMIT_TTL_MS
    ack_unknown_rate: float = DEFAULT_ACK_UNKNOWN_RATE
    reconciliation_latency_ms: int = DEFAULT_RECONCILIATION_LATENCY_MS

    def __post_init__(self) -> None:
        if self.latency_ms < 0:
            raise FillModelError("latency_ms must be non-negative")
        if self.limit_ttl_ms <= 0:
            raise FillModelError("limit_ttl_ms must be positive")
        if not (0.0 <= self.ack_unknown_rate <= 1.0):
            raise FillModelError("ack_unknown_rate must be in [0, 1]")
        if self.reconciliation_latency_ms < 0:
            raise FillModelError("reconciliation_latency_ms must be non-negative")


@dataclass(frozen=True, slots=True)
class FillOutcome:
    """Result of simulating one order against real quotes."""

    order_id: str
    order_type: OrderType
    side: SlippageSide
    requested_quantity: float
    filled_quantity: float
    average_price: float | None
    slippage_bps: float | None
    status: FillStatus
    decision_time: int
    execution_time: int | None
    ack_status: AckGuardOrderStatus
    reconciliation_available_time: int | None

    @property
    def fill_ratio(self) -> float:
        if self.requested_quantity <= 0.0:
            return 0.0
        return self.filled_quantity / self.requested_quantity


def simulate_market_fill(
    *,
    order_id: str,
    side: SlippageSide | str,
    quantity: float,
    quotes: Sequence[TopOfBookQuote],
    decision_time: int,
    config: FillModelConfig | None = None,
    reference_price: float | None = None,
) -> FillOutcome:
    """Simulate a MARKET/IOC order: fill only what level 1 offers, right now.

    Quantity beyond the quoted level-1 size is never fabricated as filled --
    it is left unfilled, exactly as a real IOC order would cancel the
    remainder instead of walking into liquidity that was never observed.
    """

    cfg = config or FillModelConfig()
    _positive_float("quantity", quantity)
    resolved_side = _coerce_side(side)

    quote = _select_quote_after_latency(quotes, decision_time, cfg.latency_ms)
    if quote is None:
        return no_quote_fill_outcome(
            order_id, OrderType.MARKET_IOC, resolved_side, quantity, decision_time
        )

    estimate = estimate_slippage(
        SlippageRequest(
            side=resolved_side,
            quantity=Decimal(str(quantity)),
            reference_price=_optional_decimal(reference_price),
        ),
        bids=(BookLevel(price=_decimal(quote.best_bid), quantity=_decimal(quote.best_bid_qty)),),
        asks=(BookLevel(price=_decimal(quote.best_ask), quantity=_decimal(quote.best_ask_qty)),),
    )
    status = FillStatus.FILLED if estimate.success else FillStatus.PARTIALLY_FILLED
    # estimate_slippage (Sprint 6) nulls out average_price/slippage_bps on any
    # failure, including a genuine partial fill -- but a partial IOC fill has
    # a real executed price on the quantity that DID fill, computed here from
    # spent_notional/filled_quantity, which estimate_slippage always
    # populates regardless of success. Losing this would silently zero out a
    # leg's realized PnL in the caller whenever it partially fills.
    realized_average_price, realized_slippage_bps = _realized_price_and_slippage(
        estimate, resolved_side, reference_price
    )
    return _build_outcome(
        order_id=order_id,
        order_type=OrderType.MARKET_IOC,
        side=resolved_side,
        quantity=quantity,
        filled_quantity=float(estimate.filled_quantity),
        average_price=realized_average_price,
        slippage_bps=realized_slippage_bps,
        status=status,
        decision_time=decision_time,
        execution_time=quote.event_time,
        config=cfg,
    )


def simulate_limit_fill(
    *,
    order_id: str,
    side: SlippageSide | str,
    quantity: float,
    limit_price: float,
    quotes: Sequence[TopOfBookQuote],
    decision_time: int,
    config: FillModelConfig | None = None,
    reference_price: float | None = None,
) -> FillOutcome:
    """Simulate a resting LIMIT order: fills only while a later quote crosses it.

    Only the crossing side's quoted level-1 quantity is available at each
    step; quantity beyond that is carried forward to the next crossing quote
    inside the TTL window, or left unfilled (EXPIRED/PARTIALLY_FILLED) if the
    window elapses first.
    """

    cfg = config or FillModelConfig()
    _positive_float("quantity", quantity)
    _positive_float("limit_price", limit_price)
    resolved_side = _coerce_side(side)

    earliest_live_time = decision_time + cfg.latency_ms
    ttl_end = decision_time + cfg.limit_ttl_ms
    candidates = [quote for quote in quotes if earliest_live_time <= quote.event_time <= ttl_end]
    candidates.sort(key=lambda quote: quote.event_time)

    remaining = quantity
    filled_notional = 0.0
    filled_quantity = 0.0
    last_execution_time: int | None = None
    for quote in candidates:
        crossing_price, crossing_qty = _crossing_level(resolved_side, quote, limit_price)
        if crossing_price is None:
            continue
        take = min(remaining, crossing_qty)
        if take <= 0.0:
            continue
        filled_quantity += take
        filled_notional += take * limit_price
        remaining -= take
        last_execution_time = quote.event_time
        if remaining <= 0.0:
            break

    if filled_quantity <= 0.0:
        status = FillStatus.EXPIRED
    elif remaining > 0.0:
        status = FillStatus.PARTIALLY_FILLED
    else:
        status = FillStatus.FILLED
    average_price = (filled_notional / filled_quantity) if filled_quantity > 0.0 else None
    slippage_bps = _limit_slippage_bps(average_price, reference_price, resolved_side)
    return _build_outcome(
        order_id=order_id,
        order_type=OrderType.LIMIT,
        side=resolved_side,
        quantity=quantity,
        filled_quantity=filled_quantity,
        average_price=average_price,
        slippage_bps=slippage_bps,
        status=status,
        decision_time=decision_time,
        execution_time=last_execution_time,
        config=cfg,
    )


def _limit_slippage_bps(
    average_price: float | None,
    reference_price: float | None,
    side: SlippageSide,
) -> float | None:
    """Slippage of a filled LIMIT order vs. an external reference price.

    Uses the same sign convention as ``_realized_price_and_slippage`` for
    MARKET orders (positive = adverse to the order's side), so LIMIT and
    MARKET fills are comparable on the same metric. Previously this always
    returned ``0.0`` when filled regardless of ``reference_price`` -- an
    inconsistent definition versus MARKET orders (QA Agent finding, Sprint 9
    review) that would have made a passive-vs-aggressive execution
    comparison misleading. Returns ``None`` when no reference price is
    supplied, rather than fabricating a zero.
    """

    if average_price is None or reference_price is None:
        return None
    average = Decimal(str(average_price))
    reference = Decimal(str(reference_price))
    if side is SlippageSide.BUY:
        bps = ((average - reference) / reference) * Decimal("10000")
    else:
        bps = ((reference - average) / reference) * Decimal("10000")
    return float(bps)


def _crossing_level(
    side: SlippageSide,
    quote: TopOfBookQuote,
    limit_price: float,
) -> tuple[float | None, float]:
    """Return (price, available quantity) if the quote crosses the resting limit."""

    if side is SlippageSide.BUY and quote.best_ask <= limit_price:
        return limit_price, quote.best_ask_qty
    if side is SlippageSide.SELL and quote.best_bid >= limit_price:
        return limit_price, quote.best_bid_qty
    return None, 0.0


def _realized_price_and_slippage(
    estimate: SlippageEstimate,
    side: SlippageSide,
    reference_price: float | None,
) -> tuple[float | None, float | None]:
    """Recover the real executed price/slippage of a partial fill.

    ``estimate_slippage`` always populates ``filled_quantity`` and
    ``spent_notional`` even when it reports failure for not filling the full
    requested quantity; only its derived ``average_price``/``slippage_bps``
    are nulled on that path. A partial IOC fill is a real, priced execution
    on whatever quantity did fill, so it must not be treated as unpriced.
    """

    if estimate.filled_quantity <= 0:
        return None, None
    average = estimate.spent_notional / estimate.filled_quantity
    if reference_price is None:
        return float(average), None
    reference = Decimal(str(reference_price))
    if side is SlippageSide.BUY:
        slippage_bps = ((average - reference) / reference) * Decimal("10000")
    else:
        slippage_bps = ((reference - average) / reference) * Decimal("10000")
    return float(average), float(slippage_bps)


def _select_quote_after_latency(
    quotes: Sequence[TopOfBookQuote],
    decision_time: int,
    latency_ms: int,
) -> TopOfBookQuote | None:
    """Return the earliest quote reachable at or after decision_time + latency."""

    earliest_reachable = decision_time + latency_ms
    reachable = [quote for quote in quotes if quote.event_time >= earliest_reachable]
    if not reachable:
        return None
    return min(reachable, key=lambda quote: quote.event_time)


def _build_outcome(
    *,
    order_id: str,
    order_type: OrderType,
    side: SlippageSide,
    quantity: float,
    filled_quantity: float,
    average_price: float | None,
    slippage_bps: float | None,
    status: FillStatus,
    decision_time: int,
    execution_time: int | None,
    config: FillModelConfig,
) -> FillOutcome:
    is_ack_unknown = _is_ack_unknown(order_id, config.ack_unknown_rate)
    ack_status = (
        AckGuardOrderStatus.ACK_UNKNOWN_UNRESOLVED if is_ack_unknown else AckGuardOrderStatus.ACKED
    )
    reconciliation_available_time = (
        (execution_time + config.reconciliation_latency_ms)
        if is_ack_unknown and execution_time is not None
        else execution_time
    )
    return FillOutcome(
        order_id=order_id,
        order_type=order_type,
        side=side,
        requested_quantity=quantity,
        filled_quantity=filled_quantity,
        average_price=average_price,
        slippage_bps=slippage_bps,
        status=status,
        decision_time=decision_time,
        execution_time=execution_time,
        ack_status=ack_status,
        reconciliation_available_time=reconciliation_available_time,
    )


def no_quote_fill_outcome(
    order_id: str,
    order_type: OrderType,
    side: SlippageSide,
    quantity: float,
    decision_time: int,
) -> FillOutcome:
    """Build a NO_QUOTE outcome for a leg with no observable book at decision time.

    Exposed publicly (not just used internally by ``simulate_market_fill``)
    so callers that construct their own limit price from a book quote --
    e.g. ``execution_simulator.py`` choosing a passive touch price -- can
    fail closed the same way when no causal quote exists yet, instead of
    duplicating this outcome shape.
    """
    return FillOutcome(
        order_id=order_id,
        order_type=order_type,
        side=side,
        requested_quantity=quantity,
        filled_quantity=0.0,
        average_price=None,
        slippage_bps=None,
        status=FillStatus.NO_QUOTE,
        decision_time=decision_time,
        execution_time=None,
        ack_status=AckGuardOrderStatus.ACKED,
        reconciliation_available_time=None,
    )


def _is_ack_unknown(order_id: str, ack_unknown_rate: float) -> bool:
    """Deterministic pseudo-random decision keyed by order_id, not global RNG state."""

    if ack_unknown_rate <= 0.0:
        return False
    digest = hashlib.sha256(order_id.encode("utf-8")).hexdigest()[:_HASH_HEX_DIGITS]
    fraction = int(digest, 16) / _HASH_MAX_VALUE
    return fraction < ack_unknown_rate


def _coerce_side(side: SlippageSide | str) -> SlippageSide:
    if isinstance(side, SlippageSide):
        resolved = side
    else:
        try:
            resolved = SlippageSide(side)
        except ValueError as exc:
            raise FillModelError(f"invalid order side: {side!r}") from exc
    if resolved is SlippageSide.UNKNOWN:
        raise FillModelError(f"invalid order side: {side!r}")
    return resolved


def _decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: float | None) -> Decimal | None:
    return None if value is None else _decimal(value)


def _maybe_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _positive_float(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise FillModelError(f"{name} must be numeric")
    if not math.isfinite(value) or value <= 0.0:
        raise FillModelError(f"{name} must be positive and finite")
    return float(value)


__all__ = [
    "FillModelConfig",
    "FillModelError",
    "FillOutcome",
    "FillStatus",
    "OrderType",
    "TopOfBookQuote",
    "no_quote_fill_outcome",
    "simulate_limit_fill",
    "simulate_market_fill",
]
