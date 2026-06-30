# Architecture Specification

Status: Sprint 1 draft for review.

Owner: Architect Agent.

## Purpose

This document defines the operational architecture for the crypto futures pairs trading system. The architecture is designed to keep survivability ahead of edge: no component may create an unsafe order path, hidden state truth, or model-dependent emergency behavior.

The MVP architecture is composed of:

```text
Market Data Plane
Signal Plane
Execution Plane
Ledger Plane
External Dead Man Switch
ML component
Recovery component
```

ML and Recovery are first-class components with explicit interfaces, but they are not independent order-sending planes in the MVP.

## Core Invariants

The following invariants are mandatory across all later specifications and implementation tasks:

```text
Signal Plane cannot send, cancel, replace, hedge, or liquidate orders.
Signal Plane can emit only SignalIntent toward Execution.
Execution exits, hedges, and reconciliation do not depend on ML.
Ledger is the transactional truth for intents, orders, fills, positions, and uncertainty.
No order is sent without deterministic clientOrderId.
No order is sent without durable events persisted first.
ORDER_SENT is a durable pre-side-effect send attempt record, not exchange confirmation.
External Dead Man Switch is independent from the main trading process.
Recovery can block entries and coordinate risk reduction, but cannot create new strategy entries.
Uncertain state blocks new entries until reconciliation resolves it or safe mode is entered.
```

## Market Data Plane

The Market Data Plane owns exchange market-data ingestion, normalization, freshness checks, and derived execution features.

Responsibilities:

```text
consume exchange WebSocket and REST market-data sources
maintain normalized books, trades, candles, and health metadata
calculate book age, in-sync status, depth, spread, and slippage estimates
publish read-only market features to Signal and Execution
mark data stale or uncertain when sequence, latency, or snapshot rules fail
```

It must not:

```text
send orders
modify positions
write order lifecycle truth
override Ledger uncertainty
invent fills from market data
```

Entry is blocked when market data is stale, out of sync, too shallow, or expected slippage exceeds configured limits. Exit and recovery logic may still use exchange snapshots and risk-reducing paths when entry is blocked.

## Signal Plane

The Signal Plane owns strategy evaluation and entry proposal generation. It converts market features, pair statistics, and optional ML advisory scores into a `SignalIntent`.

Responsibilities:

```text
read market features and pair state
apply deterministic strategy filters
consume ML advisory scores only for entry filtering or ranking
emit SignalIntent with pair, side, size target, expiry, and model metadata when applicable
```

The Signal Plane must not:

```text
send orders
cancel orders
replace orders
hedge positions
trigger emergency exit
write live order state directly
declare fills or positions
call exchange trading endpoints
```

A `SignalIntent` is advisory. It gives Execution permission to evaluate an entry candidate; it does not authorize an order by itself. Execution may reject, expire, resize, or ignore any signal based on Ledger truth, risk limits, market-data health, or recovery state.

## Execution Plane

The Execution Plane owns deterministic order lifecycle control, position entry orchestration, exits, hedges, reconciliation coordination, and risk-reducing actions.

Responsibilities:

```text
consume SignalIntent from Signal
read transactional state from Ledger
read execution health features from Market Data
apply risk limits and deployment gates
create deterministic clientOrderId values
persist required order events before exchange side effects
send, cancel, replace, exit, and hedge orders through approved exchange connectors
coordinate reconciliation with Ledger and Recovery when state is uncertain
```

Durable pre-side-effect rule:

```text
Before attempting an exchange send, Execution must persist ORDER_INTENT_CREATED and ORDER_SENT.
ORDER_SENT means "the system durably recorded that it is about to attempt the send."
ORDER_SENT does not mean the exchange accepted, acknowledged, placed, or filled the order.
Exchange confirmation requires later ORDER_ACKED, fill, or reconciliation events.
```

Execution exits, hedges, and reconciliation must be deterministic. They must not call ML, depend on an ML score, or wait for notebooks, dashboards, or research services. If ML is unavailable or corrupt, Execution must still be able to exit, hedge, reconcile, and enter safe mode.

## Ledger Plane

The Ledger Plane is the transactional truth of the system. Any component that needs to know current live state must derive it from Ledger events and approved reconciliation snapshots, not from process memory.

Responsibilities:

```text
persist trade intents, order intents, send attempts, acknowledgements, fills, reconciliations, positions, and safe-mode events
enforce append-only auditability for live lifecycle events
derive current order and position state from events
track ACK_UNKNOWN and other uncertainty states
apply fills only through reconciliation using cumulative executedQty
expose durable state to Execution and Recovery
```

The Ledger must not accept blind fill deltas as truth. Missing WebSocket events and REST 5xx responses must produce uncertainty and reconciliation work, not optimistic state transitions.

When Ledger state is uncertain:

```text
new entries are blocked
blind retries are blocked
new exit slices over an uncertain previous slice are blocked
risk-reducing actions may proceed only through explicit recovery or safe-mode rules
```

## External Dead Man Switch

The External Dead Man Switch is a safety control outside the main trading process. It exists to reduce risk when the main process cannot prove it is alive and healthy.

Independence requirements:

```text
runs as a separate process or service from the main trading engine
uses an external heartbeat observation path
does not depend on Signal, ML, dashboard, notebooks, or in-process scheduler health
has separately controlled permissions and configuration
can alert operators without the main process
```

Allowed actions:

```text
observe heartbeat and health evidence
alert operators
cancel open orders when heartbeat is missing
trigger emergency liquidation only through predefined risk-reducing rules
```

It must fail closed. If it cannot prove the main process is healthy, it must alert and block escalation paths rather than assume safety.

## ML Component

The ML component provides advisory inference for signal filtering, ranking, or confidence scoring. It is not part of deterministic execution safety.

Allowed responsibilities:

```text
train and version models from approved historical data
serve calibrated probabilities or scores to Signal
record model version and inference metadata for audit
degrade entries when model confidence is absent or below threshold
```

Forbidden responsibilities:

```text
send orders
cancel orders
modify positions
drive exits, hedges, reconciliation, recovery, or emergency liquidation
write live order or fill truth
override Ledger uncertainty
```

ML failure can block or degrade new ML-assisted entries. It must not block exits, hedges, reconciliation, safe mode, or the External Dead Man Switch.

## Recovery Component

The Recovery component owns boot-time and runtime safety recovery. It is jointly constrained by Ledger truth and Execution risk-reducing capabilities.

Responsibilities:

```text
block new entries during boot and uncertain states
rebuild state from Ledger events and exchange snapshots
resolve ACK_UNKNOWN before retrying or advancing lifecycle state
use cumulative executedQty for fill reconciliation
coordinate deterministic risk reduction with Execution
emit auditable recovery and safe-mode events
restore normal operation only after uncertainty is resolved
```

Recovery must not create new strategy entries. Its outputs are reconciliation decisions, safe-mode transitions, risk-reducing instructions, and permission to resume normal trading when safe.

## Allowed Data Flow

The only allowed high-level data flows are:

```text
Exchange market data -> Market Data Plane
Market Data Plane -> Signal Plane
Market Data Plane -> Execution Plane
ML component -> Signal Plane
Signal Plane -> Execution Plane via SignalIntent only
Execution Plane -> Ledger Plane for durable lifecycle writes
Ledger Plane -> Execution Plane for transactional state reads
Execution Plane -> Exchange trading endpoints after required durable events
Exchange trading snapshots/events -> Ledger Plane through reconciliation paths
Ledger Plane -> Recovery component
Recovery component -> Ledger Plane for recovery and safe-mode events
Recovery component -> Execution Plane for deterministic risk-reducing coordination
External Dead Man Switch -> Exchange risk-reducing endpoints
External Dead Man Switch -> Operators
```

Any new data flow must be recorded in `project_control/INTERFACES.md` before implementation.

## Forbidden Data Flow

The following flows are forbidden:

```text
Signal Plane -> Exchange trading endpoints
Signal Plane -> order router
Signal Plane -> live order state writes
Signal Plane -> emergency exit trigger
ML component -> Execution Plane exit, hedge, or reconciliation decisions
ML component -> Exchange trading endpoints
ML component -> Ledger live truth writes
Dashboard or notebooks -> order sending, cancellation, liquidation, or reconciliation authority
Market Data Plane -> fill or position truth
Execution Plane -> Exchange send before ORDER_INTENT_CREATED and ORDER_SENT are durable
Execution Plane -> blind retry after ACK_UNKNOWN
Recovery component -> new strategy entries
External Dead Man Switch -> dependency on main process internals for its own trigger path
```

Forbidden flows should fail at interface boundaries, not only by convention.

## Failure Isolation Rules

Failure isolation is part of the architecture, not an implementation detail.

```text
Market Data stale or out of sync: block new entries; preserve exits and recovery paths.
Signal unavailable: no new strategy entries; existing positions remain managed by Execution, Ledger, and Recovery.
ML unavailable or invalid: block or degrade ML-assisted entries; exits, hedges, reconciliation, and safe mode continue.
Execution crash: Recovery rebuilds from Ledger and exchange snapshots; process memory is not trusted.
Ledger uncertainty: block new entries and blind retries until reconciliation or safe mode resolves the state.
Exchange REST 5xx: treat send/cancel result as unknown until reconciled; do not assume no fill.
Missing WebSocket event: reconcile with cumulative exchange state; do not assume no fill.
ACK_UNKNOWN: block blind retry and block new exit slices over the uncertain order path.
Dashboard or notebook outage: no effect on order safety, recovery, or dead-man behavior.
External Dead Man Switch heartbeat loss: alert and execute predefined risk-reducing actions independently.
```

No failure in Signal, ML, dashboard, notebooks, or analytics may prevent deterministic exits, hedges, reconciliation, or emergency risk reduction.

## Initial Deploy Assumptions

The MVP deployment starts with conservative operational assumptions:

```text
single exchange venue for live trading
single main trading process plus independent External Dead Man Switch
isolated margin only; Cross Margin is forbidden
no Kelly sizing
no high leverage; leverage increases only after long validation
paper trading before live trading
small live notional before scale
deterministic clientOrderId for every order attempt
durable Ledger storage available before any live order path
operator alerting available before serious production
manual operator intervention remains available for unresolved safe-mode states
multi-exchange behavior starts only in paper
```

These assumptions are deployment gates. Relaxing any of them requires an explicit decision record and updated interface/risk documentation before implementation.

## Review Checklist

Before this architecture can be treated as accepted for Sprint 1, reviewers should verify:

```text
No hidden order path exists from Signal or ML to exchange trading endpoints.
No hidden state truth exists outside Ledger.
ORDER_SENT is understood as durable pre-side-effect intent, not exchange confirmation.
External Dead Man Switch can act without the main process.
Execution can exit, hedge, reconcile, and enter safe mode without ML.
Allowed and forbidden data flows are explicit.
Failure isolation rules preserve risk-reducing behavior.
Initial deploy assumptions are explicit deployment gates.
```
