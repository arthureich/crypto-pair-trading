from __future__ import annotations

import sqlite3
import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ledger import EventStore, LedgerEvent
from src.ledger import db as ledger_db

MIGRATION_PATH = PROJECT_ROOT / "migrations" / "001_initial_schema.sql"


@pytest.fixture()
def ledger_connection(tmp_path: Path):
    connection = ledger_db.bootstrap(tmp_path / "ledger.sqlite", MIGRATION_PATH)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture()
def event_store(ledger_connection: sqlite3.Connection) -> EventStore:
    return EventStore(ledger_connection)


def make_event(
    *,
    event_id: str = "event-1",
    event_type: str = "TRADE_INTENT_CREATED",
    aggregate_type: str = "trade",
    aggregate_id: str = "trade-1",
    sequence: int = 1,
    idempotency_key: str | None = None,
    correlation_id: str = "trade-1",
    payload: dict[str, object] | None = None,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=event_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        sequence=sequence,
        schema_version="event.v0.1",
        occurred_at=f"2026-06-28T12:00:{sequence:02d}Z",
        payload=payload
        or {
            "trade_id": "trade-1",
            "strategy_id": "pair-v0",
            "venue": "binance",
            "account_id": "paper-main",
        },
        idempotency_key=idempotency_key
        or f"{event_type}:{aggregate_type}:{aggregate_id}:{sequence}",
        correlation_id=correlation_id,
        producer="pytest",
        consumer="ledger",
    )


def scalar(connection: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> object:
    return connection.execute(sql, params).fetchone()[0]


def insert_trade_projection(
    connection: sqlite3.Connection,
    *,
    trade_id: str,
    event: LedgerEvent,
) -> None:
    connection.execute(
        """
        INSERT INTO trades (
            trade_id,
            strategy_id,
            signal_id,
            pair_id,
            venue,
            account_id,
            status,
            target_notional,
            opened_at,
            closed_at,
            created_at,
            updated_at,
            last_event_id,
            last_event_number
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trade_id,
            "pair-v0",
            "signal-1",
            "BTC-ETH",
            "binance",
            "paper-main",
            "POSITION_OPEN",
            "1000",
            event.occurred_at,
            None,
            event.occurred_at,
            event.occurred_at,
            event.event_id,
            event.event_number,
        ),
    )


def test_bootstrap_applies_migration_with_wal_and_required_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "ledger.sqlite"
    connection = ledger_db.bootstrap(database_path, MIGRATION_PATH)
    try:
        assert ledger_db.required_tables_exist(connection)
        assert scalar(connection, "PRAGMA journal_mode") == "wal"
        assert scalar(connection, "PRAGMA foreign_keys") == 1
        assert scalar(connection, "PRAGMA quick_check") == "ok"
    finally:
        connection.close()

    reopened = ledger_db.connect(database_path)
    try:
        assert ledger_db.required_tables_exist(reopened)
        assert scalar(reopened, "PRAGMA journal_mode") == "wal"
        assert scalar(reopened, "PRAGMA foreign_keys") == 1
    finally:
        reopened.close()


def test_append_persists_event_and_events_table_is_append_only(
    ledger_connection: sqlite3.Connection,
    event_store: EventStore,
) -> None:
    persisted = event_store.append(make_event())

    row = ledger_connection.execute(
        "SELECT * FROM events WHERE event_id = ?", ("event-1",)
    ).fetchone()
    assert row is not None
    assert persisted.event_number == row["event_number"]
    assert persisted.payload["trade_id"] == "trade-1"
    assert scalar(ledger_connection, "SELECT COUNT(*) FROM events") == 1

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        ledger_connection.execute(
            "UPDATE events SET event_type = ? WHERE event_id = ?",
            ("ORDER_SENT", "event-1"),
        )
    ledger_connection.rollback()

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        ledger_connection.execute("DELETE FROM events WHERE event_id = ?", ("event-1",))
    ledger_connection.rollback()

    assert (
        scalar(ledger_connection, "SELECT COUNT(*) FROM events WHERE event_id = ?", ("event-1",))
        == 1
    )


def test_duplicate_idempotency_returns_existing_event_without_duplicate_state(
    ledger_connection: sqlite3.Connection,
    event_store: EventStore,
) -> None:
    first = event_store.append(
        make_event(event_id="event-original", idempotency_key="TRADE_INTENT_CREATED:trade-1")
    )

    duplicate = event_store.append(
        make_event(
            event_id="event-duplicate-attempt",
            sequence=99,
            idempotency_key="TRADE_INTENT_CREATED:trade-1",
            payload={"trade_id": "trade-1", "changed": True},
        )
    )

    assert duplicate == first
    assert duplicate.event_id == "event-original"
    assert duplicate.payload == first.payload
    assert scalar(ledger_connection, "SELECT COUNT(*) FROM events") == 1


def test_sequence_gap_rejection_leaves_no_partial_insert_and_next_sequence_can_append(
    ledger_connection: sqlite3.Connection,
    event_store: EventStore,
) -> None:
    event_store.append(make_event(event_id="event-1", sequence=1))

    with pytest.raises(ValueError, match="expected 2, got 3"):
        event_store.append(make_event(event_id="event-gap", sequence=3))

    assert scalar(ledger_connection, "SELECT COUNT(*) FROM events") == 1
    assert (
        scalar(ledger_connection, "SELECT COUNT(*) FROM events WHERE event_id = ?", ("event-gap",))
        == 0
    )

    second = event_store.append(make_event(event_id="event-2", sequence=2))
    assert second.sequence == 2
    assert scalar(ledger_connection, "SELECT COUNT(*) FROM events") == 2


def test_failed_append_rolls_back_and_does_not_corrupt_sequence_state(
    ledger_connection: sqlite3.Connection,
    event_store: EventStore,
) -> None:
    event_store.append(make_event(event_id="event-1", sequence=1))

    with pytest.raises(sqlite3.IntegrityError):
        event_store.append(make_event(event_id="event-invalid", event_type="", sequence=2))

    assert scalar(ledger_connection, "SELECT COUNT(*) FROM events") == 1
    assert (
        scalar(
            ledger_connection, "SELECT COUNT(*) FROM events WHERE event_id = ?", ("event-invalid",)
        )
        == 0
    )

    valid_second = event_store.append(make_event(event_id="event-2", sequence=2))
    assert valid_second.sequence == 2
    assert scalar(ledger_connection, "SELECT COUNT(*) FROM events") == 2


def test_load_trade_events_returns_trade_lifecycle_events_in_persisted_order(
    event_store: EventStore,
) -> None:
    trade_event = event_store.append(
        make_event(event_id="trade-event", aggregate_type="trade", aggregate_id="trade-1")
    )
    order_event = event_store.append(
        make_event(
            event_id="order-event",
            event_type="ORDER_INTENT_CREATED",
            aggregate_type="order",
            aggregate_id="client-order-1",
            sequence=1,
            idempotency_key="ORDER_INTENT_CREATED:client-order-1",
            correlation_id="signal-1",
            payload={"trade_id": "trade-1", "client_order_id": "client-order-1"},
        )
    )
    event_store.append(
        make_event(
            event_id="unrelated-trade",
            aggregate_type="trade",
            aggregate_id="trade-2",
            idempotency_key="TRADE_INTENT_CREATED:trade-2",
            correlation_id="trade-2",
            payload={"trade_id": "trade-2"},
        )
    )

    loaded = event_store.load_trade_events("trade-1")

    assert [event.event_id for event in loaded] == [trade_event.event_id, order_event.event_id]
    assert [event.event_number for event in loaded] == sorted(
        event.event_number for event in loaded if event.event_number is not None
    )


def test_load_open_positions_returns_only_open_projection_rows(
    ledger_connection: sqlite3.Connection,
    event_store: EventStore,
) -> None:
    trade_event = event_store.append(make_event(event_id="trade-event"))
    insert_trade_projection(ledger_connection, trade_id="trade-1", event=trade_event)
    ledger_connection.executemany(
        """
        INSERT INTO positions (
            position_id,
            trade_id,
            venue,
            account_id,
            symbol,
            leg,
            side,
            quantity,
            avg_entry_price,
            realized_pnl,
            unrealized_pnl,
            is_open,
            opened_at,
            closed_at,
            last_reconciled_at,
            updated_at,
            last_event_id,
            last_event_number
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                "pos-open",
                "trade-1",
                "binance",
                "paper-main",
                "BTCUSDT",
                "A",
                "LONG",
                "0.5",
                "30000",
                "0",
                "12.5",
                1,
                trade_event.occurred_at,
                None,
                trade_event.occurred_at,
                trade_event.occurred_at,
                trade_event.event_id,
                trade_event.event_number,
            ),
            (
                "pos-closed",
                "trade-1",
                "binance",
                "paper-main",
                "ETHUSDT",
                "B",
                "SHORT",
                "0",
                "1800",
                "2.5",
                None,
                0,
                trade_event.occurred_at,
                trade_event.occurred_at,
                trade_event.occurred_at,
                trade_event.occurred_at,
                trade_event.event_id,
                trade_event.event_number,
            ),
        ),
    )
    ledger_connection.commit()

    positions = event_store.load_open_positions()

    assert [position.position_id for position in positions] == ["pos-open"]
    assert positions[0].quantity == Decimal("0.5")
    assert positions[0].avg_entry_price == Decimal("30000")
    assert positions[0].is_open is True
