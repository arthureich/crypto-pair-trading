# TASK-010 - EventStore Tests and Rebuild Checks

## Sprint

Sprint 2 - Ledger Base with SQLite WAL

## Dono

QA / Chaos Testing Agent

## Revisor obrigatorio

Ledger Agent

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
- `src/ledger/event_store.py`
- `tasks/sprint_02/TASK-010-event-store-tests.md`

## Objetivo

Create tests proving Ledger base invariants.

## Escopo

- Create `tests/test_event_store.py`.
- Test migration/bootstrap.
- Test append-only event persistence.
- Test duplicate idempotency handling.
- Test trade event loading.
- Test open position loading.
- Test crash-like partial transaction does not corrupt state where practical.

## Fora de escopo

- Exchange integration tests.
- Recovery boot tests.
- Market data tests.

## Arquivos permitidos

- `tests/test_event_store.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`
- `project_control/TEST_MATRIX.md`

## Arquivos proibidos

- `src/` unless reviewer explicitly requests a testability fix
- `docs/`
- `migrations/`

## Criterio de pronto

- Required tests pass.
- Test matrix is updated.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_event_store.py`

## Riscos

- Tests assert implementation details instead of invariants.
- Missing negative/idempotency tests.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-010 `IN_REVIEW` in `TASK_BOARD.md`.
