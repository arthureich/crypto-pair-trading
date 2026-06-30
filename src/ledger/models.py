"""Typed Ledger data models.

These models mirror the Sprint 2 Ledger event envelope and SQLite projection
tables. They intentionally contain no persistence or EventStore business logic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

JsonObject = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    """Append-only event envelope used by the Ledger."""

    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    sequence: int
    schema_version: str
    occurred_at: str
    payload: JsonObject
    idempotency_key: str
    correlation_id: str
    producer: str
    consumer: str
    causation_id: str | None = None
    raw_payload_ref: str | None = None
    event_number: int | None = None
    inserted_at: str | None = None


@dataclass(frozen=True, slots=True)
class TradeRecord:
    """Queryable trade lifecycle projection."""

    trade_id: str
    strategy_id: str
    venue: str
    account_id: str
    status: str
    created_at: str
    updated_at: str
    last_event_id: str
    last_event_number: int
    signal_id: str | None = None
    pair_id: str | None = None
    target_notional: Decimal | None = None
    opened_at: str | None = None
    closed_at: str | None = None


@dataclass(frozen=True, slots=True)
class OrderRecord:
    """Queryable order projection keyed by deterministic client order id."""

    order_id: str
    trade_id: str
    venue: str
    account_id: str
    symbol: str
    leg: str
    phase: str
    side: str
    order_type: str
    quantity: Decimal
    client_order_id: str
    client_order_id_version: str
    status: str
    is_open: bool
    is_uncertain: bool
    cumulative_filled_qty: Decimal
    created_at: str
    updated_at: str
    last_event_id: str
    last_event_number: int
    order_intent_id: str | None = None
    strategy_id: str | None = None
    limit_price: Decimal | None = None
    exchange_order_id: str | None = None
    attempt: int | None = None
    slice_id: str | None = None
    avg_fill_price: Decimal | None = None
    last_ack_at: str | None = None
    last_reconciled_at: str | None = None


@dataclass(frozen=True, slots=True)
class FillRecord:
    """Queryable fill reconciliation projection using cumulative exchange truth."""

    fill_id: str
    fill_event_id: str
    trade_id: str
    venue: str
    account_id: str
    symbol: str
    leg: str
    phase: str
    client_order_id: str
    exchange_order_id: str
    order_quantity: Decimal
    exchange_cum_qty: Decimal
    ledger_cum_qty: Decimal
    delta_fill: Decimal
    reconciled_at: str
    idempotency_key: str
    event_id: str
    event_number: int
    order_id: str | None = None
    avg_price: Decimal | None = None
    fee: Decimal | None = None
    fee_asset: str | None = None
    liquidity_flag: str | None = None
    terminal_order_status: str | None = None
    raw_payload_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PositionRecord:
    """Queryable position projection rebuilt from reconciled fills."""

    position_id: str
    trade_id: str
    venue: str
    account_id: str
    symbol: str
    leg: str
    side: str
    quantity: Decimal
    realized_pnl: Decimal
    is_open: bool
    updated_at: str
    last_event_id: str
    last_event_number: int
    avg_entry_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    opened_at: str | None = None
    closed_at: str | None = None
    last_reconciled_at: str | None = None


@dataclass(frozen=True, slots=True)
class ReconciliationRunRecord:
    """Queryable recovery/reconciliation run projection."""

    recovery_run_id: str
    status: str
    trigger: str
    started_at: str
    orders_checked: int
    positions_checked: int
    unresolved_orders_count: int
    unresolved_positions_count: int
    safe_mode_required: bool
    last_event_id: str
    last_event_number: int
    decision: str | None = None
    completed_at: str | None = None
    ledger_state_hash: str | None = None
    evidence_ref: str | None = None
    operator_note: str | None = None


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    """Transactional outbox projection for downstream event dispatch."""

    outbox_id: str
    event_id: str
    event_number: int
    topic: str
    payload: JsonObject
    status: str
    attempt_count: int
    next_attempt_at: str
    created_at: str
    updated_at: str
    locked_by: str | None = None
    locked_at: str | None = None
    dispatched_at: str | None = None


__all__ = [
    "FillRecord",
    "JsonObject",
    "LedgerEvent",
    "OrderRecord",
    "OutboxMessage",
    "PositionRecord",
    "ReconciliationRunRecord",
    "TradeRecord",
]
