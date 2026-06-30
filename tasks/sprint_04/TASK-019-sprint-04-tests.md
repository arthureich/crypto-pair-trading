# TASK-019 - Sprint 4 Chaos and Integration Tests

## Sprint

Sprint 4 - Recovery and Order Lifecycle Failure Routes

## Dono

QA / Chaos Testing Agent

## Revisor obrigatorio

Ledger Agent

## Status

DONE

## Progresso

100%

## Objetivo

Create Sprint 4 chaos/integration tests tying crash-after-ORDER_SENT detection, recovery boot gating, and partial-fill routing together.

## Arquivos permitidos

- `tests/test_recovery_order_state.py`
- `tests/test_recovery_boot.py`
- `tests/test_partial_fill_route.py`
- `project_control/TEST_MATRIX.md`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/` unless reviewer explicitly requests a testability fix
- `docs/`
- `migrations/`

## Criterio de pronto

- Crash after `ORDER_SENT` test passes.
- Partial fill routes test passes.
- Sprint 4 TEST_MATRIX rows are updated.
- Required tests pass.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py tests/test_partial_fill_route.py`
- `pytest tests`

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-019 `IN_REVIEW` in `TASK_BOARD.md`.
