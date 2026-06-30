# TASK-011 - Deterministic clientOrderId

## Sprint

Sprint 3 - Idempotency, clientOrderId, and Cumulative Reconciliation

## Dono

Execution / Risk Agent

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
- `docs/event_contracts.md`
- `src/ledger/models.py`
- `tasks/sprint_03/TASK-011-client-order-id.md`

## Objetivo

Implement deterministic `clientOrderId` generation.

## Escopo

- Create `src/execution/client_order_id.py`.
- Create `tests/test_client_order_id.py`.
- Generate versioned, deterministic, restart-stable IDs from immutable order intent fields.
- Support attempt-based and slice-based IDs.
- Support venue-safe shortening through deterministic hashing when needed.

## Fora de escopo

- Sending orders.
- Exchange connectors.
- EventStore changes.
- Live router.
- ACK_UNKNOWN retry policy.

## Arquivos permitidos

- `src/execution/client_order_id.py`
- `src/execution/__init__.py`
- `tests/test_client_order_id.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

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

- IDs are deterministic.
- IDs are versioned.
- IDs are stable after restart from the same inputs.
- IDs are unique by venue/account/strategy/trade/leg/phase/symbol/attempt or slice.
- IDs do not depend on unpersisted timestamp or randomness.
- Shortened IDs are deterministic and preserve canonical inputs separately.
- Tests pass.
- Handoff is written.
- `TASK_BOARD.md` marks TASK-011 as `IN_REVIEW`.

## Testes obrigatorios

- `pytest tests/test_client_order_id.py`

## Riscos

- Non-deterministic ID causes duplicate order or unrecoverable order.
- ID omits leg/phase/slice and collides.
- Venue-shortened ID cannot be reconstructed.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` and mark TASK-011 `IN_REVIEW` in `TASK_BOARD.md`.
