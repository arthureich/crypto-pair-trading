-- Sprint 2 Ledger base schema.
-- Events are the durable source of truth; the remaining tables are queryable
-- ledger projections maintained transactionally by future EventStore code.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    event_number INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    occurred_at TEXT NOT NULL,
    producer TEXT NOT NULL,
    consumer TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    causation_id TEXT,
    payload TEXT NOT NULL,
    raw_payload_ref TEXT,
    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(event_id) > 0),
    CHECK (length(event_type) > 0),
    CHECK (length(schema_version) > 0),
    CHECK (length(aggregate_type) > 0),
    CHECK (length(aggregate_id) > 0),
    CHECK (sequence > 0),
    CHECK (length(idempotency_key) > 0),
    CHECK (length(correlation_id) > 0),
    CHECK (length(payload) > 0),
    UNIQUE (event_id),
    UNIQUE (idempotency_key),
    UNIQUE (aggregate_type, aggregate_id, sequence)
);

CREATE TRIGGER IF NOT EXISTS trg_events_append_only_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events table is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_events_append_only_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events table is append-only');
END;

CREATE INDEX IF NOT EXISTS idx_events_aggregate
    ON events (aggregate_type, aggregate_id, sequence);

CREATE INDEX IF NOT EXISTS idx_events_type_time
    ON events (event_type, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_correlation
    ON events (correlation_id, event_number);

CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    signal_id TEXT,
    pair_id TEXT,
    venue TEXT NOT NULL,
    account_id TEXT NOT NULL,
    status TEXT NOT NULL,
    target_notional NUMERIC,
    opened_at TEXT,
    closed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_event_id TEXT NOT NULL,
    last_event_number INTEGER NOT NULL,
    CHECK (length(trade_id) > 0),
    CHECK (length(strategy_id) > 0),
    CHECK (length(venue) > 0),
    CHECK (length(account_id) > 0),
    CHECK (length(status) > 0),
    CHECK (target_notional IS NULL OR target_notional >= 0),
    FOREIGN KEY (last_event_id) REFERENCES events (event_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_trades_status
    ON trades (status, updated_at);

CREATE INDEX IF NOT EXISTS idx_trades_signal
    ON trades (strategy_id, signal_id);

CREATE INDEX IF NOT EXISTS idx_trades_venue_account
    ON trades (venue, account_id, updated_at);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    order_intent_id TEXT,
    trade_id TEXT NOT NULL,
    strategy_id TEXT,
    venue TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    leg TEXT NOT NULL,
    phase TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity NUMERIC NOT NULL,
    limit_price NUMERIC,
    client_order_id TEXT NOT NULL,
    client_order_id_version TEXT NOT NULL,
    exchange_order_id TEXT,
    attempt INTEGER,
    slice_id TEXT,
    status TEXT NOT NULL,
    is_open INTEGER NOT NULL DEFAULT 1,
    is_uncertain INTEGER NOT NULL DEFAULT 0,
    cumulative_filled_qty NUMERIC NOT NULL DEFAULT 0,
    avg_fill_price NUMERIC,
    last_ack_at TEXT,
    last_reconciled_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_event_id TEXT NOT NULL,
    last_event_number INTEGER NOT NULL,
    CHECK (length(order_id) > 0),
    CHECK (length(trade_id) > 0),
    CHECK (length(venue) > 0),
    CHECK (length(account_id) > 0),
    CHECK (length(symbol) > 0),
    CHECK (length(leg) > 0),
    CHECK (length(phase) > 0),
    CHECK (length(side) > 0),
    CHECK (length(order_type) > 0),
    CHECK (quantity > 0),
    CHECK (length(client_order_id) > 0),
    CHECK (length(client_order_id_version) > 0),
    CHECK (length(status) > 0),
    CHECK (is_open IN (0, 1)),
    CHECK (is_uncertain IN (0, 1)),
    CHECK (cumulative_filled_qty >= 0),
    CHECK (cumulative_filled_qty <= quantity),
    CHECK (attempt IS NULL OR attempt > 0),
    UNIQUE (venue, account_id, client_order_id),
    UNIQUE (venue, account_id, exchange_order_id),
    FOREIGN KEY (trade_id) REFERENCES trades (trade_id) ON DELETE RESTRICT,
    FOREIGN KEY (last_event_id) REFERENCES events (event_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_orders_open
    ON orders (venue, account_id, is_open, symbol, updated_at);

CREATE INDEX IF NOT EXISTS idx_orders_uncertain
    ON orders (is_uncertain, venue, account_id, updated_at);

CREATE INDEX IF NOT EXISTS idx_orders_trade
    ON orders (trade_id, leg, phase, created_at);

CREATE INDEX IF NOT EXISTS idx_orders_exchange_order
    ON orders (venue, account_id, exchange_order_id);

CREATE TABLE IF NOT EXISTS fills (
    fill_id TEXT PRIMARY KEY,
    fill_event_id TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    order_id TEXT,
    venue TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    leg TEXT NOT NULL,
    phase TEXT NOT NULL,
    client_order_id TEXT NOT NULL,
    exchange_order_id TEXT NOT NULL,
    order_quantity NUMERIC NOT NULL,
    exchange_cum_qty NUMERIC NOT NULL,
    ledger_cum_qty NUMERIC NOT NULL,
    delta_fill NUMERIC NOT NULL,
    avg_price NUMERIC,
    fee NUMERIC,
    fee_asset TEXT,
    liquidity_flag TEXT,
    terminal_order_status TEXT,
    reconciled_at TEXT NOT NULL,
    raw_payload_ref TEXT,
    idempotency_key TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_number INTEGER NOT NULL,
    CHECK (length(fill_id) > 0),
    CHECK (length(fill_event_id) > 0),
    CHECK (length(trade_id) > 0),
    CHECK (length(venue) > 0),
    CHECK (length(account_id) > 0),
    CHECK (length(symbol) > 0),
    CHECK (length(leg) > 0),
    CHECK (length(phase) > 0),
    CHECK (length(client_order_id) > 0),
    CHECK (length(exchange_order_id) > 0),
    CHECK (order_quantity > 0),
    CHECK (exchange_cum_qty >= 0),
    CHECK (ledger_cum_qty >= 0),
    CHECK (delta_fill >= 0),
    CHECK (delta_fill = CASE WHEN exchange_cum_qty > ledger_cum_qty THEN exchange_cum_qty - ledger_cum_qty ELSE 0 END),
    CHECK (delta_fill <= order_quantity),
    CHECK (exchange_cum_qty <= order_quantity),
    CHECK (ledger_cum_qty <= order_quantity),
    CHECK (fee IS NULL OR fee >= 0),
    CHECK (length(idempotency_key) > 0),
    UNIQUE (fill_event_id),
    UNIQUE (idempotency_key),
    UNIQUE (event_id),
    UNIQUE (venue, account_id, client_order_id, exchange_order_id, exchange_cum_qty),
    FOREIGN KEY (trade_id) REFERENCES trades (trade_id) ON DELETE RESTRICT,
    FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE RESTRICT,
    FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_fills_order_cumulative
    ON fills (venue, account_id, client_order_id, exchange_cum_qty);

CREATE INDEX IF NOT EXISTS idx_fills_trade
    ON fills (trade_id, symbol, reconciled_at);

CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    trade_id TEXT NOT NULL,
    venue TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    leg TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity NUMERIC NOT NULL DEFAULT 0,
    avg_entry_price NUMERIC,
    realized_pnl NUMERIC NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC,
    is_open INTEGER NOT NULL DEFAULT 0,
    opened_at TEXT,
    closed_at TEXT,
    last_reconciled_at TEXT,
    updated_at TEXT NOT NULL,
    last_event_id TEXT NOT NULL,
    last_event_number INTEGER NOT NULL,
    CHECK (length(position_id) > 0),
    CHECK (length(trade_id) > 0),
    CHECK (length(venue) > 0),
    CHECK (length(account_id) > 0),
    CHECK (length(symbol) > 0),
    CHECK (length(leg) > 0),
    CHECK (length(side) > 0),
    CHECK (quantity >= 0),
    CHECK (is_open IN (0, 1)),
    UNIQUE (trade_id, venue, account_id, symbol, leg),
    FOREIGN KEY (trade_id) REFERENCES trades (trade_id) ON DELETE RESTRICT,
    FOREIGN KEY (last_event_id) REFERENCES events (event_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_positions_open
    ON positions (venue, account_id, is_open, symbol, updated_at);

CREATE INDEX IF NOT EXISTS idx_positions_trade
    ON positions (trade_id, leg, symbol);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
    recovery_run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    trigger TEXT NOT NULL,
    decision TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    ledger_state_hash TEXT,
    orders_checked INTEGER NOT NULL DEFAULT 0,
    positions_checked INTEGER NOT NULL DEFAULT 0,
    unresolved_orders_count INTEGER NOT NULL DEFAULT 0,
    unresolved_positions_count INTEGER NOT NULL DEFAULT 0,
    safe_mode_required INTEGER NOT NULL DEFAULT 0,
    evidence_ref TEXT,
    operator_note TEXT,
    last_event_id TEXT NOT NULL,
    last_event_number INTEGER NOT NULL,
    CHECK (length(recovery_run_id) > 0),
    CHECK (length(status) > 0),
    CHECK (length(trigger) > 0),
    CHECK (orders_checked >= 0),
    CHECK (positions_checked >= 0),
    CHECK (unresolved_orders_count >= 0),
    CHECK (unresolved_positions_count >= 0),
    CHECK (safe_mode_required IN (0, 1)),
    FOREIGN KEY (last_event_id) REFERENCES events (event_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_runs_status
    ON reconciliation_runs (status, started_at);

CREATE INDEX IF NOT EXISTS idx_reconciliation_runs_decision
    ON reconciliation_runs (decision, completed_at);

CREATE TABLE IF NOT EXISTS outbox (
    outbox_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    event_number INTEGER NOT NULL,
    topic TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_by TEXT,
    locked_at TEXT,
    dispatched_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(outbox_id) > 0),
    CHECK (length(event_id) > 0),
    CHECK (event_number > 0),
    CHECK (length(topic) > 0),
    CHECK (length(payload) > 0),
    CHECK (length(status) > 0),
    CHECK (attempt_count >= 0),
    UNIQUE (event_id),
    FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_outbox_dispatch
    ON outbox (status, next_attempt_at, event_number);

CREATE INDEX IF NOT EXISTS idx_outbox_locked
    ON outbox (locked_by, locked_at);
