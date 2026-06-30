# Sprint 01 Review

## Objetivo do sprint

Specify the operational system before implementation: architecture, state machine, event contracts, risk limits, recovery protocol, and safety boundaries between planes.

## Entregas concluidas

- `docs/architecture.md`
- `docs/state_machine.md`
- `docs/event_contracts.md`
- `docs/risk_limits.md`
- `docs/recovery_protocol.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/TASK_BOARD.md`
- `project_control/TEST_MATRIX.md`
- `project_control/RISKS.md`
- `project_control/HANDOFFS.md`
- Sprint folders `tasks/sprint_01` through `tasks/sprint_28`

## Entregas nao concluidas

- None for Sprint 1.

## Testes rodados

- Documentation keyword checks for architecture invariants, forbidden flows, failure isolation, and deploy assumptions.
- Documentation keyword checks for required state machine states, negative transition matrix, critical failures, and ML independence.
- Documentation keyword checks for P0 events, `clientOrderId`, `ACK_UNKNOWN`, no blind retry, and cumulative `executedQty`.
- Documentation keyword checks for forbidden configurations, entry blockers, kill-switch triggers, fail-closed behavior, and risk-reducing proof.
- Documentation keyword checks for recovery boot, safe mode, orphan orders, REST 5xx, missing WebSocket event, cumulative `executedQty`, and `FLAT_RECONCILED`.

## Bugs encontrados

- Control metadata drift in task files after agent completion. Fixed by PM before DONE.
- `TEST_MATRIX.md` still marked P0 event contracts as pending after TASK-003 review. Fixed by PM before DONE.

## Decisoes tomadas

- ADR-0001 - Control Files Are Source of Truth
- ADR-0002 - Safety Before Edge
- ADR-0003 - Plane Separation
- ADR-0004 - ML and Recovery Component Status
- ADR-0005 - Control File Format Normalization
- TASK-003 event contract semantics: `ORDER_SENT` is durable pre-side-effect, not exchange confirmation.

## Divida tecnica

- Daily realized loss and drawdown thresholds are intentionally unresolved numeric values; live entries fail closed until approved.
- No implementation exists yet; Sprint 2 must implement Ledger foundations before any execution path.
- Git metadata exists in the workspace but is not recognized by `git status`; stable commit remains undefined.

## Riscos remanescentes

- Event contracts must be translated into Ledger schema without weakening idempotency.
- Recovery implementation must preserve the no-normal-resume-before-reconciliation rule.
- Risk limits must fail closed when thresholds or inputs are missing.
- External Dead Man Switch is specified but not implemented.

## Gate do sprint

PASSOU

## Justificativa do gate

- Critical failures have defined responses in `docs/state_machine.md`, `docs/risk_limits.md`, and `docs/recovery_protocol.md`.
- No order path exists without prior persisted events: `ORDER_INTENT_CREATED` and `ORDER_SENT`.
- Every core state has valid transitions and illegal transitions documented.
- Every P0 event is documented in `docs/event_contracts.md`.
- Main interfaces between planes are defined and versioned in `project_control/INTERFACES.md`.
- All Sprint 1 tasks have handoffs and required reviews.

## Proximo sprint recomendado

Sprint 2 - Ledger base with SQLite WAL.

## Tarefas prioritarias para o proximo sprint

1. Define Sprint 2 task breakdown for Ledger schema, EventStore, SQLite WAL, single writer, and outbox.
2. Create `migrations/001_initial_schema.sql`.
3. Implement `src/ledger/models.py`.
4. Implement `src/ledger/db.py`.
5. Implement `src/ledger/event_store.py`.
6. Add `tests/test_event_store.py`.
