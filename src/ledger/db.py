"""SQLite bootstrap helpers for the Ledger database."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Final

REQUIRED_TABLES: Final[tuple[str, ...]] = (
    "events",
    "orders",
    "fills",
    "positions",
    "trades",
    "reconciliation_runs",
    "outbox",
)


def connect(database_path: str | Path, *, timeout: float = 30.0) -> sqlite3.Connection:
    """Open a Ledger SQLite connection with required safety pragmas enabled."""
    connection = sqlite3.connect(str(database_path), timeout=timeout)
    connection.row_factory = sqlite3.Row
    configure_connection(connection, enable_wal=_supports_wal(database_path))
    return connection


def configure_connection(
    connection: sqlite3.Connection,
    *,
    enable_wal: bool = True,
) -> None:
    """Apply and verify connection-level SQLite settings."""
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA synchronous = NORMAL")

    if enable_wal:
        journal_mode = _pragma_scalar(connection, "journal_mode = WAL")
        if str(journal_mode).lower() != "wal":
            raise RuntimeError(f"SQLite WAL mode was not enabled: {journal_mode!r}")

    foreign_keys = _pragma_scalar(connection, "foreign_keys")
    if foreign_keys != 1:
        raise RuntimeError("SQLite foreign key enforcement was not enabled")


def apply_migration(
    connection: sqlite3.Connection,
    migration_path: str | Path,
) -> None:
    """Apply a SQL migration inside a single transaction."""
    sql = Path(migration_path).read_text(encoding="utf-8")

    try:
        connection.executescript(f"BEGIN IMMEDIATE;\n{sql}\nCOMMIT;")
    except sqlite3.Error:
        connection.rollback()
        raise


def bootstrap(
    database_path: str | Path,
    migration_path: str | Path,
    *,
    timeout: float = 30.0,
) -> sqlite3.Connection:
    """Open a configured connection and apply the Ledger schema migration."""
    connection = connect(database_path, timeout=timeout)
    try:
        apply_migration(connection, migration_path)
    except Exception:
        connection.close()
        raise
    return connection


def required_tables_exist(connection: sqlite3.Connection) -> bool:
    """Return whether all Sprint 2 Ledger base tables exist."""
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()
    table_names = {row["name"] for row in rows}
    return set(REQUIRED_TABLES).issubset(table_names)


def _supports_wal(database_path: str | Path) -> bool:
    return str(database_path) != ":memory:"


def _pragma_scalar(connection: sqlite3.Connection, pragma: str) -> object:
    row = connection.execute(f"PRAGMA {pragma}").fetchone()
    if row is None:
        raise RuntimeError(f"SQLite PRAGMA returned no value: {pragma}")
    return row[0]
