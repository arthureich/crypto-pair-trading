# TASK-003 - Event Contracts Specification

## Sprint

Sprint 1 - Operational System Specification

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
- `project_control/TASK_BOARD.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `docs/architecture.md`
- `docs/state_machine.md`
- `tasks/sprint_01/TASK-003-event-contracts.md`

## Objetivo

Create `docs/event_contracts.md` defining P0 event names, payloads, idempotency keys, ordering expectations, and reconciliation semantics.

## Escopo

- Define P0 lifecycle events and audit events.
- Define event producers and consumers.
- Define required fields and idempotency keys.
- Define ordering expectations.
- Define cumulative fill reconciliation semantics.
- Define ACK_UNKNOWN resolution path.

## Fora de escopo

- SQLite schema implementation.
- EventStore implementation.
- Exchange connector implementation.
- Order router implementation.
- Model implementation.

## Arquivos permitidos

- `docs/event_contracts.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/`
- `tests/`
- `notebooks/`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`

## Criterio de pronto

- Each P0 event has purpose, required fields, idempotency key, producer, and consumer.
- No order is sent without persisted ORDER_INTENT_CREATED and ORDER_SENT.
- ORDER_SENT is defined as durable pre-side-effect send attempt, not exchange confirmation.
- clientOrderId requirements are deterministic, versioned, stable after restart, and unique by venue/account/strategy/trade/leg/phase/symbol/attempt or slice.
- Fill reconciliation uses cumulative executedQty.
- `delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)` is documented.
- ACK_UNKNOWN resolves only through reconciliation by clientOrderId, exchange order id, and cumulative fills.
- No new slice may be created on the same leg while a previous slice is uncertain.
- Recovery, safe mode, risk-reducing mode, and kill switch audit events are documented or explicitly deferred with rationale.
- Handoff is written.

## Testes obrigatorios

- Documentation keyword checks for all P0 events.
- Documentation keyword checks for deterministic clientOrderId, cumulative executedQty, ACK_UNKNOWN, and no blind retry.

## Riscos

- Ambiguous event semantics create duplicate orders or duplicate fills.
- ORDER_SENT is misunderstood as exchange acknowledgement.
- ACK_UNKNOWN is retried blindly.
- Recovery lacks audit events.

## Handoff esperado

Ao terminar, atualizar `project_control/HANDOFFS.md` com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- proximos passos
- marcar TASK-003 como IN_REVIEW em `project_control/TASK_BOARD.md`
