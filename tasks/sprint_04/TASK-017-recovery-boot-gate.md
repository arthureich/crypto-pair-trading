# TASK-017 - Recovery Boot Gate and Resume Classifier

## Sprint

Sprint 4 - Recovery and Order Lifecycle Failure Routes

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
- `docs/recovery_protocol.md`
- `docs/state_machine.md`
- `src/recovery/order_state.py`
- `tasks/sprint_04/TASK-017-recovery-boot-gate.md`

## Objetivo

Implement pure recovery boot classification that blocks normal entries until order and position truth is explicitly reconciled.

## Escopo

- Create `src/recovery/recovery_boot.py`.
- Create `tests/test_recovery_boot.py`.
- Classify recovery boot as blocking normal entries when unresolved orders, open positions, or incomplete reconciliation evidence exist.
- Permit normal resume only with explicit flat/reconciled truth.

## Fora de escopo

- Exchange snapshots.
- Persistence writes.
- Operator UI.
- Live router.

## Arquivos permitidos

- `src/recovery/recovery_boot.py`
- `src/recovery/__init__.py`
- `tests/test_recovery_boot.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/execution/`
- `src/ledger/`
- `src/reconciliation/`
- `src/live/`
- `docs/`
- `migrations/`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `tasks/`

## Criterio de pronto

- Recovery boot blocks entries by default when truth is incomplete.
- Unresolved orders block resume.
- Open positions block normal entry until explicitly allowed by recovery state.
- Flat/reconciled evidence permits resume.
- Tests pass.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_recovery_boot.py`

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-017 `IN_REVIEW` in `TASK_BOARD.md`.
