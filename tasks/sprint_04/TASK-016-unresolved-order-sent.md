# TASK-016 - Detect Unresolved ORDER_SENT After Restart

## Sprint

Sprint 4 - Recovery and Order Lifecycle Failure Routes

## Dono

Ledger Agent

## Revisor obrigatorio

Execution / Risk Agent + QA / Chaos Testing Agent

## Status

DONE

## Progresso

100%

## Contexto obrigatorio

Antes de comecar, leia:

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/TASK_BOARD.md`
- `docs/event_contracts.md`
- `docs/state_machine.md`
- `docs/recovery_protocol.md`
- `src/ledger/models.py`
- `src/ledger/event_store.py`
- `src/execution/ack_guard.py`
- `tasks/sprint_04/TASK-016-unresolved-order-sent.md`

## Objetivo

Implement pure helpers that identify orders made uncertain by a crash/restart after durable `ORDER_SENT` but before ACK, fill, cancel, or reconciliation truth.

## Escopo

- Create `src/recovery/order_state.py`.
- Create or update `src/recovery/__init__.py`.
- Create `tests/test_recovery_order_state.py`.
- Classify event histories where `ORDER_SENT` is unresolved.
- Treat `ORDER_ACKED`, `ORDER_ACK_UNKNOWN` resolution, `PARTIAL_FILL_RECONCILED`, `FILL_RECONCILED`, cancel reconciliation, or `FLAT_RECONCILED` as explicit resolution evidence when present.
- Return deterministic dataclass/enum results suitable for later recovery boot code.

## Fora de escopo

- Exchange queries.
- EventStore persistence changes.
- Live order router.
- Sending, canceling, hedging, or recovery side effects.
- Recovery boot orchestration.

## Arquivos permitidos

- `src/recovery/order_state.py`
- `src/recovery/__init__.py`
- `tests/test_recovery_order_state.py`
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

- Durable `ORDER_SENT` without later resolving truth is classified as unresolved and recovery-required.
- Event histories without `ORDER_SENT` do not create false unresolved orders.
- Later ACK/fill/cancel/reconciliation evidence clears the unresolved send state.
- Multiple orders are classified independently.
- Helpers are pure and side-effect free.
- Tests pass.
- Handoff is written.
- `TASK_BOARD.md` marks TASK-016 as `IN_REVIEW`.

## Testes obrigatorios

- `pytest tests/test_recovery_order_state.py`

## Riscos

- Crash after `ORDER_SENT` is treated as safe and duplicate retry becomes possible.
- Resolution evidence is overbroad and incorrectly clears uncertainty.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-016 `IN_REVIEW` in `TASK_BOARD.md`.
