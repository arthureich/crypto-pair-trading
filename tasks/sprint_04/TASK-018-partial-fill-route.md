# TASK-018 - Partial-Fill Route Decision Helper

## Sprint

Sprint 4 - Recovery and Order Lifecycle Failure Routes

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
- `docs/state_machine.md`
- `docs/recovery_protocol.md`
- `docs/risk_limits.md`
- `src/reconciliation/cumulative_fill.py`
- `src/execution/ack_guard.py`
- `tasks/sprint_04/TASK-018-partial-fill-route.md`

## Objetivo

Implement a pure decision helper that routes partial-fill uncertainty to hedge-required or exit-lockdown outcomes without silently continuing entry.

## Escopo

- Create `src/recovery/partial_fill_route.py`.
- Create `tests/test_partial_fill_route.py`.
- Classify partial fill with unpaired exposure as `HEDGING_REQUIRED` when hedge action can reduce exposure under explicit inputs.
- Classify partial fill as `EXIT_LOCKDOWN` when hedge/risk-reducing proof is absent or residual status is uncertain.
- Keep helper deterministic and side-effect free.

## Fora de escopo

- Placing hedges.
- Canceling orders.
- Market data implementation.
- Model-driven exits.

## Arquivos permitidos

- `src/recovery/partial_fill_route.py`
- `src/recovery/__init__.py`
- `tests/test_partial_fill_route.py`
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

- Partial fill never returns continue-entry as a safe default.
- Unpaired exposure routes to `HEDGING_REQUIRED` only with explicit risk-reducing proof input.
- Missing proof, uncertain residual, or invalid inputs route to `EXIT_LOCKDOWN`.
- Tests pass.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_partial_fill_route.py`

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-018 `IN_REVIEW` in `TASK_BOARD.md`.
