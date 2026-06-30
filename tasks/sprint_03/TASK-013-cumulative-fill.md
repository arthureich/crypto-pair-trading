# TASK-013 - Cumulative Fill Reconciliation

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
- `migrations/001_initial_schema.sql`
- `tasks/sprint_03/TASK-013-cumulative-fill.md`

## Objetivo

Implement cumulative fill reconciliation math.

## Escopo

- Create `src/reconciliation/cumulative_fill.py`.
- Create `tests/test_cumulative_reconciliation.py`.
- Implement `delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)`.
- Identify duplicate observations, new partial fills, and inconsistent regressions.

## Fora de escopo

- Exchange REST queries.
- Position projection writes.
- Recovery boot.
- Order routing.

## Arquivos permitidos

- `src/reconciliation/cumulative_fill.py`
- `src/reconciliation/__init__.py`
- `tests/test_cumulative_reconciliation.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/execution/`
- `src/ledger/`
- `src/live/`
- `docs/`
- `migrations/`

## Criterio de pronto

- Duplicate cumulative observation yields zero delta.
- Increased cumulative observation yields positive delta.
- Lower exchange cumulative quantity is flagged as inconsistent.
- No blind delta API exists.
- Tests pass.
- Handoff is written.

## Testes obrigatorios

- `pytest tests/test_cumulative_reconciliation.py`

## Riscos

- Duplicate fill increases position.
- Regressed exchange cumulative quantity is silently accepted.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-013 `IN_REVIEW` in `TASK_BOARD.md`.
