# TASK-014 - ACK_UNKNOWN Retry Guard

## Sprint

Sprint 3 - Idempotency, clientOrderId, and Cumulative Reconciliation

## Dono

Execution / Risk Agent

## Revisor obrigatorio

Ledger Agent + QA / Chaos Testing Agent

## Status

DONE

## Progresso

100%

## Contexto obrigatorio

Antes de comecar, leia:

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `docs/event_contracts.md`
- `docs/state_machine.md`
- `src/execution/client_order_id.py`
- `src/ledger/idempotency.py`
- `tasks/sprint_03/TASK-014-ack-unknown-guard.md`

## Objetivo

Implement deterministic guard semantics preventing blind retry after ACK_UNKNOWN.

## Escopo

- Create `src/execution/ack_guard.py`.
- Create `tests/test_ack_guard.py`.
- Block retry while ACK_UNKNOWN is unresolved.
- Block same-leg new slice while previous slice is uncertain.

## Fora de escopo

- Sending/canceling orders.
- Exchange queries.
- Recovery boot.

## Arquivos permitidos

- `src/execution/ack_guard.py`
- `src/execution/__init__.py`
- `tests/test_ack_guard.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/ledger/`
- `src/reconciliation/`
- `src/live/`
- `docs/`
- `migrations/`

## Criterio de pronto

- ACK_UNKNOWN blocks blind retry.
- Same-leg uncertain slice blocks new slice.
- Resolved uncertainty permits action only when explicit resolved state is provided.
- Tests pass.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_ack_guard.py`

## Riscos

- Retry is allowed before reconciliation.
- Same-leg uncertain exit slice duplicates exposure.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-014 `IN_REVIEW` in `TASK_BOARD.md`.
