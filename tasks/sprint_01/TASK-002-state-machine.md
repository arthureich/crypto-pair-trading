# TASK-002 - State Machine Specification

## Sprint

Sprint 1 - Operational System Specification

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
- `project_control/DECISIONS.md`
- `docs/architecture.md`
- `tasks/sprint_01/TASK-002-state-machine.md`

## Objetivo

Create `docs/state_machine.md` defining trade lifecycle states, valid transitions, illegal transitions, and failure transitions.

## Escopo

- Define all required states.
- Define allowed inbound and outbound transitions.
- Define illegal transitions and a negative transition matrix.
- Define critical failure routing.
- Keep exits, hedges, reconciliation, lockdown, and safe mode independent from ML.

## Fora de escopo

- Source code implementation.
- Ledger schema implementation.
- Exchange connector behavior.
- Model behavior.
- Backtest behavior.

## Arquivos permitidos

- `docs/state_machine.md`
- `project_control/INTERFACES.md`
- `project_control/HANDOFFS.md`
- `project_control/TEST_MATRIX.md`

## Arquivos proibidos

- `src/`
- `tests/`
- `notebooks/`
- `models/`
- `project_control/TASK_BOARD.md`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`

## Criterio de pronto

- Required states are documented: IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, PARTIALLY_FILLED, HEDGING_REQUIRED, POSITION_OPEN, EXIT_PENDING, EXIT_LOCKDOWN, RECONCILING, FLAT, ERROR_SAFE_MODE.
- Every state has allowed inbound and outbound transitions.
- Illegal transitions are listed.
- Negative transition matrix is included.
- Each critical failure has source state, triggering event, safe destination, and forbidden retries.
- Every critical failure routes to RECONCILING, EXIT_LOCKDOWN, or ERROR_SAFE_MODE.
- No exit, hedge, or reconciliation transition depends on ML.
- `TEST_MATRIX.md` includes review checks.
- Handoff is written.

## Testes obrigatorios

- Documentation keyword checks for required states.
- Documentation keyword checks for ACK_UNKNOWN, partial fill, duplicated fill, stale book, REST 500/502, missing WebSocket event, book gap, ledger uncertainty, crash after ORDER_SENT, and crash after partial fill.
- Documentation keyword checks for negative transition matrix and ML independence.

## Riscos

- State transition permits entry while lifecycle is uncertain.
- FLAT or IDLE is reached without reconciled truth.
- ACK_UNKNOWN is treated as retryable.
- ML affects deterministic safety transitions.

## Handoff esperado

Ao terminar, atualizar `project_control/HANDOFFS.md` com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- proximos passos
