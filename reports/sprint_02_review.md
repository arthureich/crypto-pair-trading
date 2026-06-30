# Sprint 02 Review

## Objetivo do sprint

Create the durable Ledger foundation before any signal, execution, or live order path exists.

## Entregas concluidas

- `migrations/001_initial_schema.sql`
- `src/ledger/db.py`
- `src/ledger/models.py`
- `src/ledger/event_store.py`
- `src/ledger/__init__.py`
- `tests/test_event_store.py`
- Sprint 2 control updates in `project_control/`

## Entregas nao concluidas

- None for Sprint 2.

## Testes rodados

- SQLite schema parse and quick checks - passed.
- WAL/foreign key bootstrap checks on file-backed SQLite - passed.
- Python compile checks for Ledger modules - passed.
- `pytest tests/test_event_store.py` - passed, 7 tests.

## Bugs encontrados

- Initial schema allowed inconsistent `delta_fill`. Fixed with a SQLite `CASE` check.
- Initial schema allowed nullable `fills.exchange_order_id`. Fixed to `TEXT NOT NULL`.
- Initial EventStore accepted aggregate sequence gaps. Fixed with contiguous per-aggregate sequence validation.

## Decisoes tomadas

- Ledger base uses SQLite with WAL enabled for file-backed databases.
- `events` is append-only through schema triggers.
- Duplicate `idempotency_key` appends return the existing event.
- EventStore rejects aggregate sequence gaps.

## Divida tecnica

- Projection writes and outbox insertion are not yet implemented in EventStore.
- Recovery boot remains Sprint 4 scope.
- Git metadata still is not recognized as a valid repository; stable commit remains undefined.

## Riscos remanescentes

- Sprint 3 must implement deterministic `clientOrderId` without weakening idempotency.
- Sprint 3 must implement cumulative fill reconciliation without blind deltas.
- Projection/outbox transaction coupling must be preserved when EventStore expands.

## Gate do sprint

PASSOU

## Justificativa do gate

- Ledger base stores events durably in SQLite.
- WAL bootstrap is implemented and tested.
- Required tables exist: events, orders, fills, positions, trades, reconciliation_runs, outbox.
- Events are append-only.
- Event append is transactional.
- Duplicate idempotency keys do not duplicate state.
- Aggregate sequence gaps are rejected.
- Ledger can load trade events.
- Ledger can load open positions.
- Basic state read behavior is covered by tests.

## Proximo sprint recomendado

Sprint 3 - Idempotency, clientOrderId, and cumulative reconciliation.

## Tarefas prioritarias para o proximo sprint

1. Implement deterministic `clientOrderId`.
2. Implement idempotency helpers for repeated order/fill events.
3. Implement cumulative fill reconciliation.
4. Test duplicate fills do not duplicate position.
5. Test `ACK_UNKNOWN` blocks blind retry.
