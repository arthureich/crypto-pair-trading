# TASK-012 - Ledger Idempotency Helpers

## Sprint

Sprint 3 - Idempotency, clientOrderId, and Cumulative Reconciliation

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
- `docs/event_contracts.md`
- `src/ledger/event_store.py`
- `tasks/sprint_03/TASK-012-idempotency-helpers.md`

## Objetivo

Implement Ledger idempotency helper functions for duplicate event and observation handling.

## Escopo

- Create `src/ledger/idempotency.py`.
- Create `tests/test_idempotency.py`.
- Define deterministic idempotency key helpers for order ack, ack unknown, partial fill, full fill, and reconciliation observations.
- Keep helpers pure and side-effect free.

## Fora de escopo

- EventStore persistence changes unless explicitly required by tests.
- Exchange connectors.
- Order routing.

## Arquivos permitidos

- `src/ledger/idempotency.py`
- `src/ledger/__init__.py`
- `tests/test_idempotency.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/execution/`
- `src/reconciliation/`
- `src/live/`
- `docs/`
- `migrations/`

## Criterio de pronto

- Idempotency keys are deterministic.
- Duplicate semantic observations produce identical keys.
- Different semantic observations produce different keys.
- Tests pass.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_idempotency.py`

## Riscos

- Duplicate fill gets different idempotency key.
- Different fill observations collide.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-012 `IN_REVIEW` in `TASK_BOARD.md`.
