# State Machine Specification

Status: Sprint 1 draft for review.

Owner: Execution / Risk Agent.

## Purpose

This document defines the deterministic trade lifecycle state machine for the MVP crypto futures pairs trading system. It covers normal lifecycle transitions, illegal transitions, and failure routing for uncertain execution states.

The state machine is owned by Execution and Ledger together:

```text
Execution chooses allowed lifecycle actions.
Ledger is the durable truth for the current state and transition history.
Recovery resolves uncertainty before normal trading resumes.
```

No exit, hedge, reconciliation, lockdown, or safe-mode transition may depend on ML output, model availability, notebooks, dashboards, or Signal Plane approval.

## Required States

```text
IDLE
SIGNAL_ACCEPTED
ENTRY_PENDING
PARTIALLY_FILLED
HEDGING_REQUIRED
POSITION_OPEN
EXIT_PENDING
EXIT_LOCKDOWN
RECONCILING
FLAT
ERROR_SAFE_MODE
```

## State Definitions

| State | Meaning | Entry allowed? | Risk-reducing actions allowed? |
|---|---|---:|---:|
| IDLE | No accepted signal, open order, open position, or unresolved uncertainty for the pair lifecycle. | Yes | Not applicable |
| SIGNAL_ACCEPTED | Execution accepted a `SignalIntent` for deterministic validation, sizing, and order-intent creation. | No new parallel entry for same pair | Cancel acceptance before order send |
| ENTRY_PENDING | Entry order path has persisted pre-send events and at least one entry order is live, ACK_UNKNOWN, or awaiting reconciliation. | No | Cancel, reconcile, or lockdown |
| PARTIALLY_FILLED | A fill has been reconciled for less than the intended paired exposure and residual order or hedge handling is still unresolved. | No | Cancel residual, hedge, reconcile, or lockdown |
| HEDGING_REQUIRED | Exposure is materially unbalanced and deterministic hedge or risk-reduction is required. | No | Hedge, reduce, reconcile, or lockdown |
| POSITION_OPEN | Paired position is open, reconciled, and within allowed risk state. | No new duplicate entry for same pair | Exit, hedge if imbalance is detected |
| EXIT_PENDING | Exit order path has persisted pre-send events and at least one exit order is live, ACK_UNKNOWN, or awaiting reconciliation. | No | Cancel/replace under deterministic rules, reconcile, lockdown |
| EXIT_LOCKDOWN | New non-risk-reducing actions are blocked while Execution reduces or freezes exposure under explicit safety rules. | No | Cancel, reduce, flatten, reconcile |
| RECONCILING | Recovery/Ledger is rebuilding truth from durable events and exchange snapshots. | No | Only actions explicitly permitted by recovery protocol |
| FLAT | Exchange and Ledger agree there is no open position or live order for the lifecycle after trading activity. | Yes, after transition to IDLE | Not applicable |
| ERROR_SAFE_MODE | State is unsafe or unresolved beyond automated confidence; system is fail-closed and operator attention is required. | No | Only predefined emergency or manual-approved risk reduction |

## Allowed Transitions

Every transition must be persisted as a Ledger event before any external side effect that depends on the new state.

| From state | Allowed inbound transitions | Allowed outbound transitions |
|---|---|---|
| IDLE | `FLAT -> IDLE`, `ERROR_SAFE_MODE -> IDLE` after operator-approved reset and reconciled flat state | `IDLE -> SIGNAL_ACCEPTED`, `IDLE -> RECONCILING`, `IDLE -> ERROR_SAFE_MODE` |
| SIGNAL_ACCEPTED | `IDLE -> SIGNAL_ACCEPTED` | `SIGNAL_ACCEPTED -> ENTRY_PENDING`, `SIGNAL_ACCEPTED -> IDLE`, `SIGNAL_ACCEPTED -> RECONCILING`, `SIGNAL_ACCEPTED -> ERROR_SAFE_MODE` |
| ENTRY_PENDING | `SIGNAL_ACCEPTED -> ENTRY_PENDING` | `ENTRY_PENDING -> POSITION_OPEN`, `ENTRY_PENDING -> PARTIALLY_FILLED`, `ENTRY_PENDING -> FLAT`, `ENTRY_PENDING -> RECONCILING`, `ENTRY_PENDING -> EXIT_LOCKDOWN`, `ENTRY_PENDING -> ERROR_SAFE_MODE` |
| PARTIALLY_FILLED | `ENTRY_PENDING -> PARTIALLY_FILLED`, `RECONCILING -> PARTIALLY_FILLED` only when cumulative executedQty proves partial state | `PARTIALLY_FILLED -> HEDGING_REQUIRED`, `PARTIALLY_FILLED -> POSITION_OPEN`, `PARTIALLY_FILLED -> EXIT_PENDING`, `PARTIALLY_FILLED -> RECONCILING`, `PARTIALLY_FILLED -> EXIT_LOCKDOWN`, `PARTIALLY_FILLED -> ERROR_SAFE_MODE` |
| HEDGING_REQUIRED | `PARTIALLY_FILLED -> HEDGING_REQUIRED`, `POSITION_OPEN -> HEDGING_REQUIRED`, `RECONCILING -> HEDGING_REQUIRED` when reconciled imbalance exists | `HEDGING_REQUIRED -> POSITION_OPEN`, `HEDGING_REQUIRED -> EXIT_PENDING`, `HEDGING_REQUIRED -> RECONCILING`, `HEDGING_REQUIRED -> EXIT_LOCKDOWN`, `HEDGING_REQUIRED -> ERROR_SAFE_MODE` |
| POSITION_OPEN | `ENTRY_PENDING -> POSITION_OPEN`, `PARTIALLY_FILLED -> POSITION_OPEN`, `HEDGING_REQUIRED -> POSITION_OPEN`, `RECONCILING -> POSITION_OPEN` | `POSITION_OPEN -> EXIT_PENDING`, `POSITION_OPEN -> HEDGING_REQUIRED`, `POSITION_OPEN -> RECONCILING`, `POSITION_OPEN -> EXIT_LOCKDOWN`, `POSITION_OPEN -> ERROR_SAFE_MODE` |
| EXIT_PENDING | `POSITION_OPEN -> EXIT_PENDING`, `PARTIALLY_FILLED -> EXIT_PENDING`, `HEDGING_REQUIRED -> EXIT_PENDING`, `EXIT_LOCKDOWN -> EXIT_PENDING` for approved risk reduction | `EXIT_PENDING -> FLAT`, `EXIT_PENDING -> PARTIALLY_FILLED`, `EXIT_PENDING -> RECONCILING`, `EXIT_PENDING -> EXIT_LOCKDOWN`, `EXIT_PENDING -> ERROR_SAFE_MODE` |
| EXIT_LOCKDOWN | Any active or uncertain state through critical failure routing | `EXIT_LOCKDOWN -> EXIT_PENDING`, `EXIT_LOCKDOWN -> RECONCILING`, `EXIT_LOCKDOWN -> FLAT`, `EXIT_LOCKDOWN -> ERROR_SAFE_MODE` |
| RECONCILING | Any state when durable state, exchange state, or event ordering is uncertain | `RECONCILING -> IDLE`, `RECONCILING -> PARTIALLY_FILLED`, `RECONCILING -> HEDGING_REQUIRED`, `RECONCILING -> POSITION_OPEN`, `RECONCILING -> EXIT_PENDING`, `RECONCILING -> EXIT_LOCKDOWN`, `RECONCILING -> FLAT`, `RECONCILING -> ERROR_SAFE_MODE` |
| FLAT | `ENTRY_PENDING -> FLAT`, `EXIT_PENDING -> FLAT`, `EXIT_LOCKDOWN -> FLAT`, `RECONCILING -> FLAT` | `FLAT -> IDLE`, `FLAT -> RECONCILING`, `FLAT -> ERROR_SAFE_MODE` |
| ERROR_SAFE_MODE | Any state when automated recovery cannot prove safety | `ERROR_SAFE_MODE -> RECONCILING` only after operator-approved recovery start, `ERROR_SAFE_MODE -> IDLE` only after reconciled flat state and operator-approved reset |

## Normal Lifecycle Events

| Event | Required source state | Destination state | Notes |
|---|---|---|---|
| `SIGNAL_ACCEPTED` | IDLE | SIGNAL_ACCEPTED | Signal is advisory; Execution still validates deterministic gates. |
| `SIGNAL_REJECTED_OR_EXPIRED` | SIGNAL_ACCEPTED | IDLE | No order may have been sent. |
| `ORDER_INTENT_CREATED` plus durable `ORDER_SENT` | SIGNAL_ACCEPTED | ENTRY_PENDING | `ORDER_SENT` is pre-side-effect send attempt persistence, not exchange ACK. |
| `ENTRY_ACKED_AND_FULLY_RECONCILED` | ENTRY_PENDING | POSITION_OPEN | Uses cumulative executedQty, not blind deltas. |
| `ENTRY_PARTIAL_FILL_RECONCILED` | ENTRY_PENDING | PARTIALLY_FILLED | Safe only when Ledger can prove cumulative partial fill. |
| `ENTRY_CANCELED_WITH_ZERO_FILL_RECONCILED` | ENTRY_PENDING | FLAT | Requires exchange/Ledger agreement that no fill exists. |
| `HEDGE_REQUIRED` | PARTIALLY_FILLED or POSITION_OPEN | HEDGING_REQUIRED | Triggered by deterministic exposure imbalance. |
| `HEDGE_FILLED_AND_RECONCILED` | HEDGING_REQUIRED | POSITION_OPEN | Hedge result must be reconciled by Ledger. |
| `EXIT_INTENT_CREATED` plus durable `ORDER_SENT` | POSITION_OPEN, PARTIALLY_FILLED, HEDGING_REQUIRED, or EXIT_LOCKDOWN | EXIT_PENDING | Exit is deterministic and ML-independent. |
| `EXIT_PARTIAL_FILL_RECONCILED` | EXIT_PENDING | PARTIALLY_FILLED | Remaining exposure must be known before another slice. |
| `EXIT_FULLY_RECONCILED` | EXIT_PENDING or EXIT_LOCKDOWN | FLAT | All orders closed and position is zero by cumulative exchange state. |
| `RECOVERY_STARTED` | Any state | RECONCILING | Blocks new entries until resolved. |
| `SAFE_MODE_ENTERED` | Any state | ERROR_SAFE_MODE | Fail-closed state. |

## Illegal Transition Rules

The following transition classes are always illegal:

```text
Any active or uncertain state -> SIGNAL_ACCEPTED for a new same-pair entry.
Any state -> ENTRY_PENDING without durable ORDER_INTENT_CREATED and ORDER_SENT.
ENTRY_PENDING -> ENTRY_PENDING as a blind retry after ACK_UNKNOWN.
EXIT_PENDING -> EXIT_PENDING as a new exit slice over an uncertain previous slice.
Any state -> POSITION_OPEN from a WebSocket-only fill delta.
Any state -> FLAT without reconciled exchange and Ledger agreement.
Any state -> IDLE while live orders, open positions, ACK_UNKNOWN, or ledger uncertainty exists.
RECONCILING -> any normal trading state without cumulative exchange snapshot validation.
ERROR_SAFE_MODE -> any trading state without operator-approved recovery and reconciled truth.
Any exit, hedge, reconciliation, lockdown, or safe-mode transition gated by ML.
```

## Negative Transition Matrix

This matrix lists direct transitions that must be rejected unless a row in the allowed transition table or critical failure table explicitly permits them.

| From state | Illegal direct destinations |
|---|---|
| IDLE | ENTRY_PENDING, PARTIALLY_FILLED, HEDGING_REQUIRED, POSITION_OPEN, EXIT_PENDING, EXIT_LOCKDOWN, FLAT |
| SIGNAL_ACCEPTED | PARTIALLY_FILLED, HEDGING_REQUIRED, POSITION_OPEN, EXIT_PENDING, EXIT_LOCKDOWN, FLAT |
| ENTRY_PENDING | IDLE, SIGNAL_ACCEPTED, HEDGING_REQUIRED, EXIT_PENDING |
| PARTIALLY_FILLED | IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, FLAT |
| HEDGING_REQUIRED | IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, PARTIALLY_FILLED, FLAT |
| POSITION_OPEN | IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, PARTIALLY_FILLED, FLAT |
| EXIT_PENDING | IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, HEDGING_REQUIRED, POSITION_OPEN |
| EXIT_LOCKDOWN | IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, PARTIALLY_FILLED, HEDGING_REQUIRED, POSITION_OPEN |
| RECONCILING | SIGNAL_ACCEPTED, ENTRY_PENDING |
| FLAT | SIGNAL_ACCEPTED, ENTRY_PENDING, PARTIALLY_FILLED, HEDGING_REQUIRED, POSITION_OPEN, EXIT_PENDING, EXIT_LOCKDOWN |
| ERROR_SAFE_MODE | SIGNAL_ACCEPTED, ENTRY_PENDING, PARTIALLY_FILLED, HEDGING_REQUIRED, POSITION_OPEN, EXIT_PENDING, EXIT_LOCKDOWN, FLAT |

## Critical Failure Routing

Every critical failure must route to `RECONCILING`, `EXIT_LOCKDOWN`, or `ERROR_SAFE_MODE`. The destination must be persisted before automated actions continue.

| Critical failure | Source state | Triggering event | Safe destination | Forbidden retries |
|---|---|---|---|---|
| ACK_UNKNOWN | ENTRY_PENDING or EXIT_PENDING | REST send/cancel/replace result cannot prove exchange acceptance or rejection | RECONCILING | Blind resend with same intent; new exit slice over uncertain order; assuming no fill |
| Partial fill with unresolved pair exposure | ENTRY_PENDING, EXIT_PENDING, or PARTIALLY_FILLED | Cumulative executedQty proves partial fill but paired exposure is incomplete or residual order status is uncertain | EXIT_LOCKDOWN | Continuing entry; increasing exposure; retrying residual slice before exposure is bounded |
| Duplicated fill | ENTRY_PENDING, EXIT_PENDING, PARTIALLY_FILLED, or RECONCILING | Duplicate fill event or repeated cumulative fill observation conflicts with Ledger idempotency | RECONCILING | Applying blind delta; incrementing position twice; treating duplicate as a new fill |
| Stale book | IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, POSITION_OPEN, or EXIT_PENDING | `book_age_ms` exceeds threshold, `book.in_sync` is false, or executable depth/slippage cannot be trusted | RECONCILING for active uncertainty; ERROR_SAFE_MODE if exits cannot be priced safely | New entry; blind cancel/replace based on stale price; ML-approved override |
| REST 500/502 | ENTRY_PENDING, EXIT_PENDING, HEDGING_REQUIRED, or EXIT_LOCKDOWN | Exchange REST trading endpoint returns 500 or 502 after a send/cancel/replace attempt | RECONCILING | Assuming order failed; blind retry; advancing to FLAT or POSITION_OPEN without snapshot |
| Missing WebSocket event | ENTRY_PENDING, EXIT_PENDING, POSITION_OPEN, or RECONCILING | Expected order, fill, cancel, or account event is absent beyond timeout | RECONCILING | Assuming no fill; applying stale in-memory state; sending next slice |
| Book gap | IDLE, SIGNAL_ACCEPTED, ENTRY_PENDING, POSITION_OPEN, EXIT_PENDING, or HEDGING_REQUIRED | Sequence gap, snapshot mismatch, or market-data resync failure | RECONCILING for active orders/positions; ERROR_SAFE_MODE if recovery cannot regain market-data truth | New entry; price-sensitive hedge based on gapped book; ML-approved override |
| Ledger uncertainty | Any state | Ledger cannot derive one current order/position truth from events and reconciliations | RECONCILING or ERROR_SAFE_MODE if unresolved | New entry; blind retry; state advancement from process memory |
| Crash after ORDER_SENT | ENTRY_PENDING or EXIT_PENDING | Process restarts after durable `ORDER_SENT` but before ACK/fill/cancel truth is known | RECONCILING | Re-sending same order path; assuming no exchange side effect; trusting pre-crash memory |
| Crash after partial fill | PARTIALLY_FILLED, HEDGING_REQUIRED, or EXIT_PENDING | Process restarts after cumulative partial fill was observed or persisted before final exposure resolution | EXIT_LOCKDOWN then RECONCILING | Continuing entry; placing new exit slice over uncertain residual; applying blind fill delta |

## Reconciliation Rules

Reconciliation must use durable Ledger events and exchange snapshots. It must not use process memory as truth.

Mandatory rules:

```text
ACK_UNKNOWN is resolved before retry or state advancement.
Cumulative executedQty is the only source for final fill quantity.
Duplicate fills are idempotency conflicts until reconciled, not additional exposure.
Missing WebSocket events are treated as uncertainty.
REST 500/502 is treated as unknown exchange side effect.
Book gaps and stale books block entries and may block price-sensitive risk reduction.
Uncertain Ledger state blocks entries.
```

Allowed reconciliation exits:

```text
RECONCILING -> IDLE only when no order was sent and no live state exists.
RECONCILING -> PARTIALLY_FILLED only when cumulative executedQty proves known residual exposure.
RECONCILING -> HEDGING_REQUIRED only when known imbalance requires deterministic hedge.
RECONCILING -> POSITION_OPEN only when paired exposure is complete and all orders are known.
RECONCILING -> EXIT_PENDING only when a deterministic risk-reducing exit order is already live or must continue.
RECONCILING -> EXIT_LOCKDOWN when exposure exists but normal exit sequencing is unsafe.
RECONCILING -> FLAT only when exchange and Ledger agree all orders are closed and position is zero.
RECONCILING -> ERROR_SAFE_MODE when automated reconciliation cannot prove safe state.
```

## ML Independence

The following transitions must be possible when ML is unavailable, corrupt, stale, or disabled:

```text
POSITION_OPEN -> EXIT_PENDING
PARTIALLY_FILLED -> HEDGING_REQUIRED
HEDGING_REQUIRED -> EXIT_PENDING
ENTRY_PENDING -> RECONCILING
EXIT_PENDING -> RECONCILING
Any state -> EXIT_LOCKDOWN
Any state -> ERROR_SAFE_MODE
RECONCILING -> EXIT_LOCKDOWN
RECONCILING -> FLAT
```

ML may influence only whether Signal emits or ranks a new entry candidate. It must not authorize, block, or parametrize exits, hedges, reconciliation, lockdown, or safe mode.

## Review Checklist

Reviewers should verify:

```text
All required states are present.
Every state has inbound and outbound transitions.
Illegal transitions and the negative transition matrix are explicit.
Every critical failure routes only to RECONCILING, EXIT_LOCKDOWN, or ERROR_SAFE_MODE.
ACK_UNKNOWN, partial fill, duplicated fill, stale book, REST 500/502, missing WebSocket event, book gap, ledger uncertainty, crash after ORDER_SENT, and crash after partial fill are covered.
No exit, hedge, or reconciliation transition depends on ML.
No transition reaches FLAT or IDLE without reconciled truth.
No order path reaches ENTRY_PENDING without durable ORDER_INTENT_CREATED and ORDER_SENT.
```
