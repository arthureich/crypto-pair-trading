# TASK-015 - Sprint 3 Integration Tests

## Sprint

Sprint 3 - Idempotency, clientOrderId, and Cumulative Reconciliation

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
- `src/execution/client_order_id.py`
- `src/ledger/idempotency.py`
- `src/reconciliation/cumulative_fill.py`
- `src/execution/ack_guard.py`
- `tasks/sprint_03/TASK-015-sprint-03-tests.md`

## Objetivo

Create integrated Sprint 3 tests tying deterministic IDs, idempotency, cumulative reconciliation, and ACK_UNKNOWN guards together.

## Escopo

- Extend or create focused tests under `tests/`.
- Update `project_control/TEST_MATRIX.md`.
- Verify all Sprint 3 required tests pass.

## Fora de escopo

- Exchange integration.
- Order routing.
- Recovery boot.

## Arquivos permitidos

- `tests/test_client_order_id.py`
- `tests/test_idempotency.py`
- `tests/test_cumulative_reconciliation.py`
- `tests/test_ack_guard.py`
- `project_control/TEST_MATRIX.md`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/` unless reviewer explicitly requests a testability fix
- `docs/`
- `migrations/`

## Criterio de pronto

- All Sprint 3 tests pass.
- TEST_MATRIX is updated.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_client_order_id.py tests/test_idempotency.py tests/test_cumulative_reconciliation.py tests/test_ack_guard.py`

## Riscos

- Tests miss duplicate fill or ACK_UNKNOWN negative cases.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-015 `IN_REVIEW` in `TASK_BOARD.md`.
