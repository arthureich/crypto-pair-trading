"""Round-trip pair-trade execution simulation for the Sprint 9 backtest.

Replaces the Sprint 8 assumption of a perfect, fully-filled mark-to-market
trade with a simulation built from two independently-filled legs. Each leg
can partially fill, expire, or come back ACK_UNKNOWN; the realized PnL
reflects exactly what was actually filled, not what was intended -- and a
leg-fill mismatch (one leg filling more than the other) is surfaced
explicitly rather than averaged away.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from src.execution.ack_guard import (
    AckGuardAction,
    AckGuardOrderStatus,
    AckGuardRequest,
    GuardedOrderState,
    evaluate_ack_guard,
)
from src.execution.slippage_estimator import SlippageSide

from .fill_model import (
    FillModelConfig,
    FillOutcome,
    FillStatus,
    OrderType,
    TopOfBookQuote,
    simulate_market_fill,
)

DEFAULT_HOLDING_PERIOD_MS = 60 * 60 * 1000
LEG_FILL_MISMATCH_TOLERANCE = 0.05
_VENUE = "BINANCE"
_ACCOUNT_ID = "SPRINT9_BACKTEST"


class TradeStatus(StrEnum):
    """Outcome of one simulated round-trip pair trade."""

    EXECUTED = "EXECUTED"
    NO_ENTRY_FILL = "NO_ENTRY_FILL"
    NO_EXIT_FILL = "NO_EXIT_FILL"


class ExecutionSimulatorError(ValueError):
    """Raised when execution-simulator inputs are invalid."""


@dataclass(frozen=True, slots=True)
class RoundTripTradeResult:
    """Result of simulating one signal's entry and exit on both legs."""

    signal_id: str
    pair: str
    status: TradeStatus
    entry_fill_a: FillOutcome
    entry_fill_b: FillOutcome
    exit_fill_a: FillOutcome | None
    exit_fill_b: FillOutcome | None
    leg_fill_mismatch: bool
    exit_delayed_by_ack_unknown_ms: int
    net_pnl_quote: float

    @property
    def net_pnl_bps(self) -> float:
        target_notional = self.entry_fill_a.requested_quantity * (
            self.entry_fill_a.average_price or 0.0
        )
        if target_notional <= 0.0:
            return 0.0
        return (self.net_pnl_quote / target_notional) * 10_000.0


def simulate_round_trip_trade(
    intent: object,
    *,
    quotes_a: Sequence[TopOfBookQuote],
    quotes_b: Sequence[TopOfBookQuote],
    holding_period_ms: int = DEFAULT_HOLDING_PERIOD_MS,
    config: FillModelConfig | None = None,
) -> RoundTripTradeResult:
    """Simulate a beta-weighted round-trip pair trade against real quotes.

    ``intent`` is a ``src.research.sprint8.OfflineSignalIntent`` (typed as
    ``object`` here to avoid a research-plane import dependency; this module
    only reads its fields).
    """

    cfg = config or FillModelConfig()
    signal_id = str(intent.signal_id)
    _positive_finite("target_notional", float(intent.target_notional))
    _finite("beta", float(intent.beta))
    reference_a = _reference_price(quotes_a, intent.created_at)
    reference_b = _reference_price(quotes_b, intent.created_at)
    if reference_a is None or reference_b is None:
        empty = _empty_fill(signal_id, intent.side_a)
        empty_b = _empty_fill(f"{signal_id}-B", intent.side_b)
        return RoundTripTradeResult(
            signal_id=signal_id,
            pair=str(intent.pair),
            status=TradeStatus.NO_ENTRY_FILL,
            entry_fill_a=empty,
            entry_fill_b=empty_b,
            exit_fill_a=None,
            exit_fill_b=None,
            leg_fill_mismatch=False,
            exit_delayed_by_ack_unknown_ms=0,
            net_pnl_quote=0.0,
        )

    beta_weight = abs(float(intent.beta))
    quantity_a = float(intent.target_notional) / reference_a
    quantity_b = (beta_weight * float(intent.target_notional)) / reference_b

    entry_a = simulate_market_fill(
        order_id=f"{signal_id}-A-ENTRY",
        side=intent.side_a,
        quantity=quantity_a,
        quotes=quotes_a,
        decision_time=intent.created_at,
        config=cfg,
        reference_price=reference_a,
    )
    entry_b = simulate_market_fill(
        order_id=f"{signal_id}-B-ENTRY",
        side=intent.side_b,
        quantity=quantity_b,
        quotes=quotes_b,
        decision_time=intent.created_at,
        config=cfg,
        reference_price=reference_b,
    )

    if entry_a.filled_quantity <= 0.0 and entry_b.filled_quantity <= 0.0:
        return RoundTripTradeResult(
            signal_id=signal_id,
            pair=str(intent.pair),
            status=TradeStatus.NO_ENTRY_FILL,
            entry_fill_a=entry_a,
            entry_fill_b=entry_b,
            exit_fill_a=None,
            exit_fill_b=None,
            leg_fill_mismatch=False,
            exit_delayed_by_ack_unknown_ms=0,
            net_pnl_quote=0.0,
        )

    planned_exit_time = intent.created_at + holding_period_ms
    exit_time_a = _effective_exit_time(signal_id, "A", entry_a, planned_exit_time)
    exit_time_b = _effective_exit_time(signal_id, "B", entry_b, planned_exit_time)
    exit_delay_ms = max(exit_time_a, exit_time_b) - planned_exit_time

    exit_a = (
        simulate_market_fill(
            order_id=f"{signal_id}-A-EXIT",
            side=_opposite_side(intent.side_a),
            quantity=entry_a.filled_quantity,
            quotes=quotes_a,
            decision_time=exit_time_a,
            config=cfg,
            reference_price=reference_a,
        )
        if entry_a.filled_quantity > 0.0
        else None
    )
    exit_b = (
        simulate_market_fill(
            order_id=f"{signal_id}-B-EXIT",
            side=_opposite_side(intent.side_b),
            quantity=entry_b.filled_quantity,
            quotes=quotes_b,
            decision_time=exit_time_b,
            config=cfg,
            reference_price=reference_b,
        )
        if entry_b.filled_quantity > 0.0
        else None
    )

    if (exit_a is None or exit_a.filled_quantity <= 0.0) and (
        exit_b is None or exit_b.filled_quantity <= 0.0
    ):
        status = TradeStatus.NO_EXIT_FILL
    else:
        status = TradeStatus.EXECUTED

    net_pnl_quote = _leg_pnl_quote(intent.side_a, entry_a, exit_a) + _leg_pnl_quote(
        intent.side_b, entry_b, exit_b
    )
    leg_fill_mismatch = _is_leg_fill_mismatch(entry_a, entry_b)

    return RoundTripTradeResult(
        signal_id=signal_id,
        pair=str(intent.pair),
        status=status,
        entry_fill_a=entry_a,
        entry_fill_b=entry_b,
        exit_fill_a=exit_a,
        exit_fill_b=exit_b,
        leg_fill_mismatch=leg_fill_mismatch,
        exit_delayed_by_ack_unknown_ms=max(0, exit_delay_ms),
        net_pnl_quote=net_pnl_quote,
    )


def _effective_exit_time(
    signal_id: str,
    leg: str,
    entry_fill: FillOutcome,
    planned_exit_time: int,
) -> int:
    """Delay the exit if the entry leg is still ACK_UNKNOWN-unresolved.

    Mirrors the real ``evaluate_ack_guard`` "same leg uncertain slice
    blocked" rule: a new slice (the exit order) cannot be created on a leg
    whose most recent order is still uncertain.
    """

    if entry_fill.reconciliation_available_time is None:
        return planned_exit_time
    # The guard checks a point-in-time status, not a clock. If reconciliation
    # would already have completed by the planned exit time, the leg is no
    # longer uncertain *at that time* even though the raw ack_status field
    # (captured at entry) still reads ACK_UNKNOWN_UNRESOLVED.
    still_unresolved_at_planned_exit = planned_exit_time < entry_fill.reconciliation_available_time
    effective_status = (
        entry_fill.ack_status if still_unresolved_at_planned_exit else AckGuardOrderStatus.ACKED
    )
    state = GuardedOrderState(
        venue=_VENUE,
        account_id=_ACCOUNT_ID,
        trade_id=signal_id,
        leg=leg,
        client_order_id=entry_fill.order_id,
        status=effective_status,
    )
    decision = evaluate_ack_guard(
        AckGuardRequest(
            action=AckGuardAction.CREATE_NEW_SLICE,
            venue=_VENUE,
            account_id=_ACCOUNT_ID,
            trade_id=signal_id,
            leg=leg,
            slice_id=f"{signal_id}-{leg}-EXIT",
        ),
        (state,),
    )
    if decision.allowed:
        return planned_exit_time
    return max(planned_exit_time, entry_fill.reconciliation_available_time)


def _reference_price(quotes: Sequence[TopOfBookQuote], decision_time: int) -> float | None:
    """Return the most recent quote's mid price at or before decision_time."""

    causal = [quote for quote in quotes if quote.event_time <= decision_time]
    if not causal:
        return None
    latest = max(causal, key=lambda quote: quote.event_time)
    return (latest.best_bid + latest.best_ask) / 2.0


def _opposite_side(side: SlippageSide | str) -> SlippageSide:
    resolved = SlippageSide(side) if not isinstance(side, SlippageSide) else side
    return SlippageSide.SELL if resolved is SlippageSide.BUY else SlippageSide.BUY


def _leg_pnl_quote(
    side: SlippageSide | str,
    entry: FillOutcome,
    exit_fill: FillOutcome | None,
) -> float:
    if exit_fill is None or exit_fill.filled_quantity <= 0.0:
        return 0.0
    if entry.average_price is None or exit_fill.average_price is None:
        return 0.0
    closed_quantity = min(entry.filled_quantity, exit_fill.filled_quantity)
    direction = 1.0 if SlippageSide(side) is SlippageSide.BUY else -1.0
    return direction * closed_quantity * (exit_fill.average_price - entry.average_price)


def _is_leg_fill_mismatch(entry_a: FillOutcome, entry_b: FillOutcome) -> bool:
    return abs(entry_a.fill_ratio - entry_b.fill_ratio) > LEG_FILL_MISMATCH_TOLERANCE


def _empty_fill(order_id: str, side: str) -> FillOutcome:
    return FillOutcome(
        order_id=order_id,
        order_type=OrderType.MARKET_IOC,
        side=SlippageSide(side) if side in ("BUY", "SELL") else SlippageSide.UNKNOWN,
        requested_quantity=0.0,
        filled_quantity=0.0,
        average_price=None,
        slippage_bps=None,
        status=FillStatus.NO_QUOTE,
        decision_time=0,
        execution_time=None,
        ack_status=AckGuardOrderStatus.ACKED,
        reconciliation_available_time=None,
    )


def _finite(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ExecutionSimulatorError(f"{name} must be finite")
    return value


def _positive_finite(name: str, value: float) -> float:
    _finite(name, value)
    if value <= 0.0:
        raise ExecutionSimulatorError(f"{name} must be positive")
    return value


__all__ = [
    "ExecutionSimulatorError",
    "RoundTripTradeResult",
    "TradeStatus",
    "simulate_round_trip_trade",
]
