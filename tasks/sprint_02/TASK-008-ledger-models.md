# TASK-008 - Ledger Models

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
- `project_control/INTERFACES.md`
- `docs/event_contracts.md`
- `tasks/sprint_02/TASK-008-ledger-models.md`

## Objetivo

Create typed Ledger models aligned with Sprint 1 event contracts.

## Escopo

- Create `src/ledger/models.py`.
- Define models for Ledger events, order records, fill records, positions, trades, reconciliation runs, and outbox messages.
- Preserve cumulative fill semantics.

## Fora de escopo

- EventStore persistence implementation.
- Exchange adapters.
- Recovery implementation.

## Arquivos permitidos

- `src/ledger/models.py`
- `src/ledger/__init__.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/execution/`
- `src/live/`
- `src/recovery/`
- `docs/`
- `migrations/`

## Criterio de pronto

- Models match `docs/event_contracts.md`.
- `LedgerEvent` contains event id, type, aggregate id, sequence, schema version, payload, idempotency key, correlation id, and causation id.
- Fill model carries cumulative exchange quantity and computed delta field names.
- Handoff is written.

## Testes obrigatorios

- Import/type construction check if tests exist; otherwise document as pending for TASK-010.

## Riscos

- Models drift from event contracts.
- Models encourage blind fill deltas.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-008 `IN_REVIEW` in `TASK_BOARD.md`.
