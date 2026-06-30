# TASK-006 - Initial SQLite Schema

## Sprint

Sprint 2 - Ledger Base with SQLite WAL

## Dono

Ledger Agent

## Revisor obrigatorio

Architect Agent

## Status

DONE

## Progresso

100%

## Contexto obrigatorio

Antes de comecar, leia:

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/TASK_BOARD.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `docs/event_contracts.md`
- `tasks/sprint_02/TASK-006-initial-sqlite-schema.md`

## Objetivo

Create the initial SQLite schema migration for the Ledger base.

## Escopo

- Create `migrations/001_initial_schema.sql`.
- Define tables: `events`, `orders`, `fills`, `positions`, `trades`, `reconciliation_runs`, `outbox`.
- Include primary keys, required timestamps, idempotency keys, aggregate sequencing, and useful indexes.
- Preserve append-only event storage by schema design.

## Fora de escopo

- Python EventStore implementation.
- SQLite connection/bootstrap code.
- Recovery implementation.
- Order router.
- Exchange integration.

## Arquivos permitidos

- `migrations/001_initial_schema.sql`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/`
- `tests/`
- `docs/`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`

## Criterio de pronto

- All required tables are present.
- `events` supports append-only event sourcing.
- `events` has unique `event_id`.
- `events` has unique `idempotency_key`.
- `events` has unique aggregate sequence.
- Schema supports transactional outbox.
- Schema supports cumulative fill reconciliation fields.
- Schema supports open order, open position, trade, and reconciliation run queries.
- Handoff is written.
- `TASK_BOARD.md` marks TASK-006 as `IN_REVIEW` when complete.

## Testes obrigatorios

- Run a SQLite parse/bootstrap check if available, for example executing the migration against a temporary SQLite database.

## Riscos

- Schema permits duplicate semantic events.
- Schema cannot reconstruct state by aggregate.
- Fill table encourages blind deltas instead of cumulative reconciliation.
- Outbox cannot support transactional dispatch.

## Handoff esperado

Ao terminar, atualizar `project_control/HANDOFFS.md` com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- proximos passos
- marcar TASK-006 como IN_REVIEW em `project_control/TASK_BOARD.md`
