# TASK-007 - SQLite WAL Bootstrap

## Sprint

Sprint 2 - Ledger Base with SQLite WAL

## Dono

Ledger Agent

## Revisor obrigatorio

QA / Chaos Testing Agent

## Status

DONE

## Progresso

100%

## Contexto obrigatorio

Antes de comecar, leia:

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/TASK_BOARD.md`
- `migrations/001_initial_schema.sql`
- `tasks/sprint_02/TASK-007-sqlite-wal-bootstrap.md`

## Objetivo

Implement SQLite connection/bootstrap helpers with WAL mode.

## Escopo

- Create `src/ledger/db.py`.
- Apply PRAGMA settings for WAL, foreign keys, and reasonable durability.
- Provide migration bootstrap helper.

## Fora de escopo

- EventStore business logic.
- Exchange integration.
- Recovery boot.

## Arquivos permitidos

- `src/ledger/db.py`
- `src/ledger/__init__.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/execution/`
- `src/live/`
- `src/recovery/`
- `docs/`
- `migrations/001_initial_schema.sql` unless reviewer requests schema fix

## Criterio de pronto

- WAL mode is enabled.
- Foreign keys are enabled.
- Migration can be applied through helper.
- Connection helper is deterministic and testable.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_event_store.py` once available, or a focused bootstrap test if created by this task.

## Riscos

- WAL is assumed but not actually enabled.
- Foreign keys are disabled.
- Migration bootstrap silently partially applies schema.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-007 `IN_REVIEW` in `TASK_BOARD.md`.
