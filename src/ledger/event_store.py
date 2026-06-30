"""EventStore append and read APIs for the Ledger."""

from __future__ import annotations

import json
import sqlite3
from decimal import Decimal

from .models import JsonObject, LedgerEvent, PositionRecord


class EventStore:
    """Persist and read Ledger events from SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def append(self, event: LedgerEvent) -> LedgerEvent:
        """Append an event transactionally or return the existing idempotent event."""
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self._load_event_by_idempotency_key(event.idempotency_key)
            if existing is not None:
                self._connection.commit()
                return existing

            self._validate_next_sequence(event)

            self._connection.execute(
                """
                INSERT INTO events (
                    event_id,
                    event_type,
                    schema_version,
                    aggregate_type,
                    aggregate_id,
                    sequence,
                    occurred_at,
                    producer,
                    consumer,
                    idempotency_key,
                    correlation_id,
                    causation_id,
                    payload,
                    raw_payload_ref
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.schema_version,
                    event.aggregate_type,
                    event.aggregate_id,
                    event.sequence,
                    event.occurred_at,
                    event.producer,
                    event.consumer,
                    event.idempotency_key,
                    event.correlation_id,
                    event.causation_id,
                    _payload_to_json(event.payload),
                    event.raw_payload_ref,
                ),
            )
            persisted = self._load_event_by_idempotency_key(event.idempotency_key)
            if persisted is None:
                raise RuntimeError("Ledger event append succeeded but event could not be reloaded")
            self._connection.commit()
            return persisted
        except Exception:
            self._connection.rollback()
            raise

    def load_trade_events(self, trade_id: str) -> list[LedgerEvent]:
        """Load persisted events associated with a trade id."""
        try:
            rows = self._connection.execute(
                """
                SELECT *
                FROM events
                WHERE (aggregate_type = 'trade' AND aggregate_id = ?)
                   OR correlation_id = ?
                   OR json_extract(payload, '$.trade_id') = ?
                ORDER BY event_number ASC
                """,
                (trade_id, trade_id, trade_id),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = [
                row
                for row in self._connection.execute(
                    """
                    SELECT *
                    FROM events
                    ORDER BY event_number ASC
                    """
                ).fetchall()
                if _row_matches_trade_id(row, trade_id)
            ]
        return [_event_from_row(row) for row in rows]

    def load_open_positions(self) -> list[PositionRecord]:
        """Load open position projections from SQLite."""
        rows = self._connection.execute(
            """
            SELECT *
            FROM positions
            WHERE is_open = 1
            ORDER BY venue, account_id, symbol, leg, position_id
            """
        ).fetchall()
        return [_position_from_row(row) for row in rows]

    def _load_event_by_idempotency_key(self, idempotency_key: str) -> LedgerEvent | None:
        row = self._connection.execute(
            """
            SELECT *
            FROM events
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return _event_from_row(row)

    def _validate_next_sequence(self, event: LedgerEvent) -> None:
        row = self._connection.execute(
            """
            SELECT MAX(sequence)
            FROM events
            WHERE aggregate_type = ?
              AND aggregate_id = ?
            """,
            (event.aggregate_type, event.aggregate_id),
        ).fetchone()
        current_sequence = row[0] if row is not None else None
        expected_sequence = 1 if current_sequence is None else int(current_sequence) + 1
        if event.sequence != expected_sequence:
            raise ValueError(
                "Ledger event sequence must be contiguous for aggregate "
                f"{event.aggregate_type}:{event.aggregate_id}; "
                f"expected {expected_sequence}, got {event.sequence}"
            )


def _payload_to_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _payload_from_json(payload: str) -> JsonObject:
    return json.loads(payload)


def _event_from_row(row: sqlite3.Row) -> LedgerEvent:
    return LedgerEvent(
        event_id=row["event_id"],
        event_type=row["event_type"],
        aggregate_type=row["aggregate_type"],
        aggregate_id=row["aggregate_id"],
        sequence=row["sequence"],
        schema_version=row["schema_version"],
        occurred_at=row["occurred_at"],
        payload=_payload_from_json(row["payload"]),
        idempotency_key=row["idempotency_key"],
        correlation_id=row["correlation_id"],
        producer=row["producer"],
        consumer=row["consumer"],
        causation_id=row["causation_id"],
        raw_payload_ref=row["raw_payload_ref"],
        event_number=row["event_number"],
        inserted_at=row["inserted_at"],
    )


def _position_from_row(row: sqlite3.Row) -> PositionRecord:
    return PositionRecord(
        position_id=row["position_id"],
        trade_id=row["trade_id"],
        venue=row["venue"],
        account_id=row["account_id"],
        symbol=row["symbol"],
        leg=row["leg"],
        side=row["side"],
        quantity=_decimal(row["quantity"]),
        realized_pnl=_decimal(row["realized_pnl"]),
        is_open=bool(row["is_open"]),
        updated_at=row["updated_at"],
        last_event_id=row["last_event_id"],
        last_event_number=row["last_event_number"],
        avg_entry_price=_optional_decimal(row["avg_entry_price"]),
        unrealized_pnl=_optional_decimal(row["unrealized_pnl"]),
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
        last_reconciled_at=row["last_reconciled_at"],
    )


def _row_matches_trade_id(row: sqlite3.Row, trade_id: str) -> bool:
    if row["aggregate_type"] == "trade" and row["aggregate_id"] == trade_id:
        return True
    if row["correlation_id"] == trade_id:
        return True
    payload = _payload_from_json(row["payload"])
    return isinstance(payload, dict) and payload.get("trade_id") == trade_id


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value)


__all__ = ["EventStore"]
