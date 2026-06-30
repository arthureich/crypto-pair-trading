# TASK-005 - Recovery Protocol Specification

## Sprint

Sprint 1 - Operational System Specification

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
- `project_control/TASK_BOARD.md`
- `project_control/INTERFACES.md`
- `project_control/RISKS.md`
- `project_control/DECISIONS.md`
- `docs/architecture.md`
- `docs/state_machine.md`
- `tasks/sprint_01/TASK-005-recovery-protocol.md`

## Objetivo

Create `docs/recovery_protocol.md` defining recovery boot, safe mode, reconciliation order, orphan handling, and risk-reducing behavior after crash or uncertainty.

## Escopo

- Define recovery boot sequence.
- Define safe mode rules.
- Define orphan order handling.
- Define residual exposure handling.
- Define ACK_UNKNOWN handling after restart.
- Define criteria to resume normal operation.

## Fora de escopo

- Recovery code implementation.
- Exchange connector implementation.
- Ledger database implementation.
- Order router implementation.
- Model implementation.

## Arquivos permitidos

- `docs/recovery_protocol.md`
- `project_control/INTERFACES.md`
- `project_control/RISKS.md`
- `project_control/HANDOFFS.md`
- `project_control/TEST_MATRIX.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/`
- `tests/`
- `notebooks/`
- `models/`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`

## Criterio de pronto

- System never boots into normal trading before reconciliation.
- Safe mode permits only cancellation, reconciliation, and risk reduction.
- Cumulative executedQty reconciliation is required.
- ACK_UNKNOWN resolution is specified.
- Orphan handling is specified.
- Safe orphan cancel means cancel by exchange order id, then requery order/fill state.
- REST 5xx or timeout during orphan handling keeps system in safe mode.
- Never assume no fill because cancel, REST, or WebSocket response is missing.
- Resume normal only after zero ACK_UNKNOWN, cumulative fills applied, exchange and Ledger positions match, orphan orders resolved, and FLAT_RECONCILED or equivalent reconciled state is persisted.
- `RISKS.md` and `TEST_MATRIX.md` are updated.
- Handoff is written.

## Testes obrigatorios

- Documentation keyword checks for recovery boot, safe mode, ACK_UNKNOWN, orphan order, REST 5xx, WebSocket missing event, cumulative executedQty, and FLAT_RECONCILED.

## Riscos

- Boot resumes trading before reconciliation.
- REST 5xx is treated as no fill.
- Orphan order cancellation skips fill requery.
- Safe mode allows non-risk-reducing action.

## Handoff esperado

Ao terminar, atualizar `project_control/HANDOFFS.md` com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- proximos passos
- marcar TASK-005 como IN_REVIEW em `project_control/TASK_BOARD.md`
