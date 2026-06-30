# DECISIONS

Use this file as a simplified ADR log. Any interface, state machine, ledger schema, risk gate, sizing, live mode, leverage, or dead man switch policy change requires an ADR.

## ADR Template

```markdown
# ADR-XXX - Title

## Status
Proposed / Accepted / Rejected / Superseded

## Context
What problem are we solving?

## Decision
What was decided?

## Consequences
What improves?
What gets worse?
What must change?

## Agent Impact
- agent 1
- agent 2

## Migration
How should the system be updated?
```

## ADR-0001 - Control Files Are Source of Truth

## Status

Accepted

## Context

Multiple agents need a shared project memory that does not depend on conversation history.

## Decision

`project_control/` is the operational source of truth. Conversation history is not source of truth.

## Consequences

Every completed task updates `TASK_BOARD.md` and `HANDOFFS.md`. Architecture changes update `DECISIONS.md`. New tests or scenarios update `TEST_MATRIX.md`. Blockers update `BLOCKERS.md`.

## Agent Impact

- PM Agent
- Documentation Agent
- All specialized agents

## Migration

All agents must start by reading `PROJECT_STATE.md`, `CURRENT_SPRINT.md`, `TASK_BOARD.md`, assigned task files, and relevant contracts.

## ADR-0002 - Safety Before Edge

## Status

Accepted

## Context

The system can lose real money if execution, ledger, recovery, or risk controls are unsafe.

## Decision

The project proves operational safety before proving edge, and proves edge before scaling risk.

## Consequences

No real order execution implementation before specification and ledger/recovery foundations. No leverage, Cross Margin, Kelly sizing, or live multi-exchange behavior in MVP.

## Agent Impact

- PM Agent
- Execution / Risk Agent
- Ledger Agent
- ML Agent
- Quant Research Agent

## Migration

All sprint gates must preserve this order: safety, edge, small live, scale.

## ADR-0003 - Plane Separation

## Status

Accepted

## Context

Signal, execution, ledger, market data, ML, and recovery responsibilities must not collapse into one unsafe pipeline.

## Decision

Responsibilities remain separated by explicit interfaces.

## Consequences

SignalIntent is advisory only. Execution owns order lifecycle and deterministic exits. Ledger owns transactional truth. ML never controls emergency or reconciliation logic.

## Agent Impact

- Architect Agent
- Signal-related agents
- Execution / Risk Agent
- Ledger Agent
- ML Agent

## Migration

All interface changes must be added to `INTERFACES.md` and reviewed through ADR when they affect contracts.

## ADR-0004 - ML and Recovery Component Status

## Status

Accepted

## Context

The architecture needs ML and Recovery as explicit components without making them independent order-sending planes.

## Decision

ML and Recovery are first-class components with explicit interfaces, but they are not independent order-sending planes in the MVP.

## Consequences

ML is advisory to Signal only. Recovery is safety-critical and may block entries, reconcile, enter safe mode, and coordinate risk reduction. Recovery cannot create new strategy entries. External Dead Man Switch remains independent from the main process.

## Agent Impact

- Architect Agent
- ML Agent
- Ledger Agent
- Execution / Risk Agent
- DevOps / Observability Agent

## Migration

Architecture and interfaces must distinguish planes from safety/advisory components.

## ADR-0005 - Control File Format Normalization

## Status

Accepted

## Context

The PM operating instructions require specific templates for `PROJECT_STATE.md`, `CURRENT_SPRINT.md`, `TASK_BOARD.md`, `OWNERSHIP.md`, `INTERFACES.md`, `DECISIONS.md`, `HANDOFFS.md`, and `TEST_MATRIX.md`.

## Decision

Normalize control files to the required PM templates while preserving Sprint 1 technical content.

## Consequences

Agents can onboard from files without reading conversation history. `INTERFACES.md` now carries versioned contract skeletons.

## Agent Impact

- PM Agent
- Architect Agent
- Ledger Agent
- Execution / Risk Agent
- QA / Chaos Testing Agent
- Documentation Agent

## Migration

Future task files and handoffs should follow the normalized templates.

## ADR-0006 - Durable Event Contracts Before Exchange Side Effects

## Status

Accepted

## Context

Order lifecycle ambiguity can create duplicate sends, duplicate fills, unsafe retries, and unclear recovery after process crashes or exchange uncertainty.

## Decision

P0 lifecycle and audit events are specified in `docs/event_contracts.md`. Every exchange-facing order path must persist `ORDER_INTENT_CREATED` and `ORDER_SENT` before the exchange side effect. `ORDER_SENT` is a durable pre-side-effect send attempt, not exchange confirmation. `clientOrderId` values must be deterministic, versioned, stable after restart, and unique by venue/account/strategy/trade/leg/phase/symbol/attempt or slice. Fill reconciliation uses cumulative exchange `executedQty` and applies only `delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)`.

## Consequences

Ledger can recover order truth from persisted events after restart. `ACK_UNKNOWN` blocks blind retry and resolves only through reconciliation by `clientOrderId`, exchange order id, and cumulative fills. Same-leg slicing is blocked while a previous slice is uncertain. Recovery, safe-mode, risk-reducing, and kill-switch actions now have audit event contracts.

## Agent Impact

- Ledger Agent
- Execution / Risk Agent
- Architect Agent
- QA / Chaos Testing Agent
- DevOps / Observability Agent

## Migration

Implementation tasks must derive Ledger schema, order router behavior, recovery boot, and documentation checks from `docs/event_contracts.md`. Any future contract-breaking event or `clientOrderId` change requires a new ADR and migration plan.
