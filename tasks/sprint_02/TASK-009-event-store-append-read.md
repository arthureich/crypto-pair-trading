# TASK-009 - EventStore Append and Reads

## Sprint

Sprint 2 - Ledger Base with SQLite WAL

## Dono

Ledger Agent

## Revisor obrigatorio

Architect Agent + QA / Chaos Testing Agent

## Status

DONE

## Progresso

100%

## Contexto obrigatorio

Antes de comecar, leia:

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `docs/event_contracts.md`
- `migrations/001_initial_schema.sql`
- `src/ledger/db.py`
- `src/ledger/models.py`
- `tasks/sprint_02/TASK-009-event-store-append-read.md`

## Objetivo

Implement `EventStore` append and read APIs.

## Escopo

- Create `src/ledger/event_store.py`.
- Implement transactional append.
- Implement idempotency-key handling.
- Implement `load_trade_events`.
- Implement `load_open_positions`.
- Respect single-writer assumptions.

## Fora de escopo

- Recovery boot.
- Order router.
- Exchange connectors.

## Arquivos permitidos

- `src/ledger/event_store.py`
- `src/ledger/__init__.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/execution/`
- `src/live/`
- `src/recovery/`
- `docs/`
- `migrations/` unless reviewer requests schema fix

## Criterio de pronto

- Events append in order.
- Duplicate idempotency key does not duplicate event.
- Append is transactional.
- Trade events can be loaded by trade id.
- Open positions can be loaded.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_event_store.py`

## Riscos

- Duplicate events mutate state.
- Append is not transactional.
- Reads derive state from memory instead of database.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-009 `IN_REVIEW` in `TASK_BOARD.md`.
