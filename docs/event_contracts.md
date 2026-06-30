# Event Contracts Specification

Status: Sprint 1 draft for review.

Owner: Ledger Agent.

## Purpose

This document defines the P0 Ledger events required before live execution implementation. The goal is to make order, fill, uncertainty, recovery, safe-mode, risk-reducing, and kill-switch behavior auditable and idempotent.

Ledger is the transactional truth. Process memory, WebSocket deltas, dashboard state, notebooks, and ML output are never order or fill truth.

## Core Invariants

```text
No order is sent without persisted ORDER_INTENT_CREATED and ORDER_SENT.
ORDER_SENT is a durable pre-side-effect send attempt, not exchange confirmation.
ORDER_SENT means the system durably recorded that it is about to attempt an exchange send.
Exchange confirmation requires ORDER_ACKED or later reconciliation evidence.
Every order attempt uses deterministic clientOrderId.
ACK_UNKNOWN is never resolved by blind retry.
ACK_UNKNOWN resolves only through reconciliation by clientOrderId, exchange_order_id when known, and cumulative fills.
No new slice may be created on the same leg while a previous slice is uncertain.
Fill reconciliation uses cumulative executedQty.
delta_fill = max(0, exchange_cum_qty - ledger_cum_qty).
Duplicate idempotency keys must not duplicate Ledger state.
```

## Event Envelope

Every P0 event and Sprint 1 audit event uses this envelope:

| Field | Required | Meaning |
|---|---:|---|
| `event_id` | Yes | Globally unique event identifier assigned before append. |
| `event_type` | Yes | One of the event names in this document. |
| `schema_version` | Yes | Contract version, starting at `event.v0.1`. |
| `aggregate_type` | Yes | `trade`, `order`, `leg`, `recovery_run`, `risk_mode`, or `kill_switch`. |
| `aggregate_id` | Yes | Stable aggregate identifier such as `trade_id`, `client_order_id`, or `recovery_run_id`. |
| `sequence` | Yes | Monotonic sequence per aggregate. |
| `occurred_at` | Yes | UTC event time assigned by the producer at durable write boundary. |
| `producer` | Yes | Component that produced the event. |
| `consumer` | Yes | Primary component expected to react to or derive state from the event. |
| `idempotency_key` | Yes | Deterministic duplicate-suppression key for the semantic event. |
| `correlation_id` | Yes | Identifier linking the event to the broader signal, trade, or recovery workflow. |
| `causation_id` | No | Prior `event_id` or command id that caused this event. |
| `payload` | Yes | Event-specific required fields. |
| `raw_payload_ref` | No | Pointer to immutable exchange or system raw evidence. |

Append rules:

```text
Ledger append is durable before side effects that depend on the event.
Ledger append is single-writer for a given aggregate sequence.
The same idempotency_key returns the existing event or no-ops; it must not create a second state transition.
Required field changes require ADR and migration plan.
```

## clientOrderId Contract

Every exchange-facing order path must carry a deterministic `clientOrderId`. The value is generated before `ORDER_INTENT_CREATED`, stored in Ledger, and reused after restart.

Required properties:

```text
deterministic
versioned
stable after restart
unique by venue/account/strategy/trade/leg/phase/symbol/attempt or slice
bounded to the venue client-order-id length and charset
reconstructable from Ledger intent fields without process memory
```

Canonical inputs:

| Input | Required | Notes |
|---|---:|---|
| `id_version` | Yes | Starts at `coid.v1`; any algorithm change requires ADR. |
| `venue` | Yes | Exchange venue code. |
| `account_id` | Yes | Exchange account or subaccount scope. |
| `strategy_id` | Yes | Strategy namespace. |
| `trade_id` | Yes | Stable trade lifecycle id. |
| `leg` | Yes | `A`, `B`, or explicit hedge leg. |
| `phase` | Yes | `ENTRY`, `EXIT`, `HEDGE`, `RISK_REDUCE`, or `CANCEL_REPLACE`. |
| `symbol` | Yes | Venue symbol. |
| `attempt` | Conditional | Required for one-shot attempts. |
| `slice_id` | Conditional | Required for sliced orders. |

Format:

```text
clientOrderId = coid.v1:{venue}:{account_id}:{strategy_id}:{trade_id}:{leg}:{phase}:{symbol}:{attempt_or_slice}
```

If a venue requires a shorter string, the canonical input string is hashed with a versioned, documented algorithm. The full canonical inputs and the short venue id are both persisted. A restart must regenerate the same short value for the same canonical inputs.

Slice safety:

```text
A slice is uncertain after ORDER_SENT until ORDER_ACKED, ORDER_ACK_UNKNOWN resolution, FILL_RECONCILED, PARTIAL_FILL_RECONCILED, cancel reconciliation, or FLAT_RECONCILED proves its state.
No new slice may be created on the same leg while a previous slice is uncertain.
Replacing a slice requires the previous slice to be reconciled or explicitly routed through risk-reducing recovery rules.
```

## P0 Lifecycle Events

### TRADE_INTENT_CREATED

Purpose: records Execution acceptance of an advisory `SignalIntent` into a durable trade lifecycle candidate before any order intent exists.

Producer: Execution Plane.

Consumer: Ledger Plane, Recovery Component.

Required fields:

```text
trade_id
strategy_id
signal_id
pair_id
venue
account_id
leg_a_symbol
leg_b_symbol
side_a
side_b
target_notional
created_at
```

Idempotency key:

```text
TRADE_INTENT_CREATED:{strategy_id}:{signal_id}:{pair_id}:{venue}:{account_id}
```

Ordering:

```text
Must precede ORDER_INTENT_CREATED for every order in the trade lifecycle.
Does not authorize exchange side effects by itself.
```

### ORDER_INTENT_CREATED

Purpose: records the exact order intent and deterministic `clientOrderId` before a send attempt can be persisted or attempted.

Producer: Execution Plane.

Consumer: Ledger Plane, Recovery Component.

Required fields:

```text
order_intent_id
trade_id
strategy_id
venue
account_id
symbol
leg
phase
side
order_type
quantity
client_order_id
client_order_id_version
attempt
slice_id
created_at
```

Idempotency key:

```text
ORDER_INTENT_CREATED:{venue}:{account_id}:{strategy_id}:{trade_id}:{leg}:{phase}:{symbol}:{attempt_or_slice}
```

Ordering:

```text
Must follow TRADE_INTENT_CREATED for strategy entries.
Must precede ORDER_SENT.
Must be durable before any exchange send, cancel-replace, hedge, exit, or risk-reducing order attempt.
```

### ORDER_SENT

Purpose: records a durable pre-side-effect send attempt. It is the final Ledger write before Execution calls an exchange trading endpoint.

Producer: Execution Plane.

Consumer: Ledger Plane, Recovery Component.

Required fields:

```text
order_sent_id
order_intent_id
trade_id
venue
account_id
symbol
leg
phase
client_order_id
send_attempt
side_effect_type
send_started_at
```

Idempotency key:

```text
ORDER_SENT:{client_order_id}:{send_attempt}:{side_effect_type}
```

Ordering:

```text
Must follow durable ORDER_INTENT_CREATED for the same client_order_id.
Must be persisted before the exchange trading endpoint is called.
Does not mean the exchange accepted, acknowledged, placed, rejected, canceled, replaced, or filled the order.
```

Crash behavior:

```text
After restart, ORDER_SENT without ORDER_ACKED, ORDER_ACK_UNKNOWN resolution, or reconciled terminal order state is uncertain and must route to reconciliation.
```

### ORDER_ACKED

Purpose: records exchange acknowledgement that the order exists or that a requested order-side-effect was accepted by the venue.

Producer: Execution Plane or Reconciliation.

Consumer: Ledger Plane, Execution Plane, Recovery Component.

Required fields:

```text
order_acked_id
order_intent_id
trade_id
venue
account_id
symbol
client_order_id
exchange_order_id
ack_status
ack_received_at
```

Idempotency key:

```text
ORDER_ACKED:{venue}:{account_id}:{client_order_id}:{exchange_order_id}:{ack_status}
```

Ordering:

```text
Must follow ORDER_SENT.
May be produced from direct exchange response or reconciliation snapshot.
Does not by itself prove fill quantity; fills still require cumulative executedQty reconciliation.
```

### ORDER_ACK_UNKNOWN

Purpose: records that a send, cancel, replace, hedge, exit, or risk-reducing side effect may have reached the exchange, but the system cannot prove the outcome.

Producer: Execution Plane or Recovery Component.

Consumer: Ledger Plane, Execution Plane, Recovery Component, operators.

Required fields:

```text
order_ack_unknown_id
order_intent_id
trade_id
venue
account_id
symbol
leg
phase
client_order_id
exchange_order_id
unknown_reason
first_unknown_at
last_observed_at
```

Idempotency key:

```text
ORDER_ACK_UNKNOWN:{venue}:{account_id}:{client_order_id}:{unknown_reason}
```

Ordering:

```text
Must follow ORDER_SENT.
Blocks blind retry.
Blocks new same-leg slice while uncertain.
Routes the lifecycle to RECONCILING, EXIT_LOCKDOWN, or ERROR_SAFE_MODE according to the state machine.
```

Resolution:

```text
ACK_UNKNOWN resolves only through reconciliation by clientOrderId, exchange_order_id when available, and cumulative fills.
If reconciliation finds the order by clientOrderId, Ledger records ORDER_ACKED or terminal reconciled state.
If reconciliation finds the order only by exchange_order_id, Ledger links exchange_order_id back to the client_order_id before advancing state.
If reconciliation finds cumulative executedQty greater than Ledger cumulative quantity, Ledger records PARTIAL_FILL_RECONCILED or FILL_RECONCILED using delta_fill = max(0, exchange_cum_qty - ledger_cum_qty).
If exchange and Ledger prove no open order and zero cumulative fill, the uncertainty can close without retry.
No blind retry is allowed from ORDER_ACK_UNKNOWN.
```

### PARTIAL_FILL_RECONCILED

Purpose: records a reconciled cumulative fill that is greater than Ledger quantity but less than the intended order quantity.

Producer: Reconciliation.

Consumer: Ledger Plane, Execution Plane, Recovery Component.

Required fields:

```text
fill_event_id
trade_id
venue
account_id
symbol
leg
phase
client_order_id
exchange_order_id
order_quantity
exchange_cum_qty
ledger_cum_qty
delta_fill
avg_price
reconciled_at
```

Idempotency key:

```text
PARTIAL_FILL_RECONCILED:{venue}:{account_id}:{client_order_id}:{exchange_order_id}:{exchange_cum_qty}
```

Fill math:

```text
Fill reconciliation uses cumulative executedQty from the exchange.
exchange_cum_qty maps to exchange cumulative executedQty for this order.
ledger_cum_qty is the Ledger cumulative quantity already applied for this order.
delta_fill = max(0, exchange_cum_qty - ledger_cum_qty).
If delta_fill is zero, Ledger must not increase position.
```

Ordering:

```text
Must follow ORDER_SENT.
May occur before ORDER_ACKED if reconciliation observes cumulative executedQty before durable ACK.
May route to HEDGE_REQUIRED, EXIT_LOCKDOWN, RECONCILING, or PARTIALLY_FILLED state depending on exposure.
```

### FILL_RECONCILED

Purpose: records a reconciled cumulative fill that completes the intended quantity for the order or closes the order's fill accounting.

Producer: Reconciliation.

Consumer: Ledger Plane, Execution Plane, Recovery Component.

Required fields:

```text
fill_event_id
trade_id
venue
account_id
symbol
leg
phase
client_order_id
exchange_order_id
order_quantity
exchange_cum_qty
ledger_cum_qty
delta_fill
avg_price
reconciled_at
terminal_order_status
```

Idempotency key:

```text
FILL_RECONCILED:{venue}:{account_id}:{client_order_id}:{exchange_order_id}:{exchange_cum_qty}:{terminal_order_status}
```

Fill math:

```text
Fill reconciliation uses cumulative executedQty from the exchange.
exchange_cum_qty maps to exchange cumulative executedQty for this order.
ledger_cum_qty is the Ledger cumulative quantity already applied for this order.
delta_fill = max(0, exchange_cum_qty - ledger_cum_qty).
Duplicate cumulative observations are idempotent and must not double-count fills.
```

Ordering:

```text
Must follow ORDER_SENT.
May follow PARTIAL_FILL_RECONCILED for the same client_order_id.
May occur before ORDER_ACKED if reconciliation observes terminal cumulative executedQty first.
Must not advance to FLAT unless all related orders and positions are reconciled.
```

### HEDGE_REQUIRED

Purpose: records that reconciled exposure is materially unbalanced and requires deterministic hedge or risk reduction.

Producer: Execution Plane or Recovery Component from Ledger state.

Consumer: Ledger Plane, Execution Plane, Recovery Component.

Required fields:

```text
hedge_required_id
trade_id
venue
account_id
imbalanced_leg
symbol
known_position_qty
target_position_qty
imbalance_qty
reason
detected_at
```

Idempotency key:

```text
HEDGE_REQUIRED:{trade_id}:{venue}:{account_id}:{imbalanced_leg}:{symbol}:{known_position_qty}:{target_position_qty}
```

Ordering:

```text
Must be based on Ledger and reconciliation truth, not ML output.
Must not be emitted from WebSocket-only blind deltas.
Can lead to deterministic hedge, risk-reducing action, EXIT_LOCKDOWN, or ERROR_SAFE_MODE.
```

### EXIT_LOCKDOWN

Purpose: records that normal non-risk-reducing actions are frozen while the system reduces, reconciles, or freezes exposure under explicit safety rules.

Producer: Execution Plane or Recovery Component.

Consumer: Ledger Plane, Execution Plane, Recovery Component, operators.

Required fields:

```text
exit_lockdown_id
trade_id
venue
account_id
reason
source_state
allowed_actions
entered_at
```

Idempotency key:

```text
EXIT_LOCKDOWN:{trade_id}:{venue}:{account_id}:{reason}:{source_state}
```

Ordering:

```text
May follow ACK_UNKNOWN, partial fill uncertainty, stale book during active exposure, REST 5xx, missing WebSocket event, book gap, ledger uncertainty, or crash recovery.
Blocks new entries and normal entry continuation.
Allows only deterministic risk-reducing or reconciliation actions.
```

### FLAT_RECONCILED

Purpose: records that Ledger and exchange reconciliation agree there are no open orders and no open position for the lifecycle.

Producer: Reconciliation or Recovery Component.

Consumer: Ledger Plane, Execution Plane, Recovery Component.

Required fields:

```text
flat_reconciled_id
trade_id
venue
account_id
open_orders_count
position_qty_by_symbol
unresolved_orders_count
unresolved_positions_count
reconciled_at
evidence_ref
```

Idempotency key:

```text
FLAT_RECONCILED:{trade_id}:{venue}:{account_id}:{reconciled_at}:{evidence_ref}
```

Ordering:

```text
May follow ENTRY_PENDING, EXIT_PENDING, EXIT_LOCKDOWN, or RECONCILING only when exchange and Ledger agree.
Must not be emitted while live orders, open positions, ACK_UNKNOWN, or Ledger uncertainty exists.
Permits transition to FLAT and later IDLE according to the state machine.
```

## Sprint 1 Audit Events

These events are documented now because recovery, safe mode, risk-reducing mode, and kill switch actions must leave audit evidence even before implementation.

### RECOVERY_BOOT_STARTED

Purpose: records the start of boot-time or runtime recovery and blocks normal entries until recovery completes.

Producer: Recovery Component.

Consumer: Ledger Plane, Execution Plane, operators.

Required fields:

```text
recovery_run_id
started_at
trigger
last_ledger_sequence
process_start_id
normal_entries_blocked
```

Idempotency key:

```text
RECOVERY_BOOT_STARTED:{recovery_run_id}:{process_start_id}:{trigger}
```

### RECONCILIATION_COMPLETED

Purpose: records the result of a reconciliation run across Ledger state and exchange snapshots.

Producer: Recovery Component or Reconciliation.

Consumer: Ledger Plane, Execution Plane, operators.

Required fields:

```text
recovery_run_id
completed_at
decision
orders_checked
positions_checked
unresolved_orders_count
unresolved_positions_count
safe_mode_required
evidence_ref
```

Idempotency key:

```text
RECONCILIATION_COMPLETED:{recovery_run_id}:{decision}:{completed_at}
```

### SAFE_MODE_ENTERED

Purpose: records fail-closed entry into safe mode when automated recovery cannot prove normal operation is safe.

Producer: Recovery Component or Execution Plane.

Consumer: Ledger Plane, Execution Plane, operators, External Dead Man Switch observer when applicable.

Required fields:

```text
safe_mode_event_id
entered_at
reason
source_state
blocked_actions
allowed_risk_reducing_actions
operator_required
```

Idempotency key:

```text
SAFE_MODE_ENTERED:{reason}:{source_state}:{entered_at}
```

### SAFE_MODE_EXITED

Purpose: records operator-approved exit from safe mode after reconciled truth proves it is safe.

Producer: Recovery Component.

Consumer: Ledger Plane, Execution Plane, operators.

Required fields:

```text
safe_mode_exit_id
exited_at
operator_approval_id
recovery_run_id
flat_reconciled_id
remaining_uncertainty_count
resume_scope
```

Idempotency key:

```text
SAFE_MODE_EXITED:{operator_approval_id}:{recovery_run_id}:{flat_reconciled_id}
```

### RISK_REDUCING_MODE_ENTERED

Purpose: records that the system may continue only actions that reduce or freeze risk.

Producer: Execution Plane or Recovery Component.

Consumer: Ledger Plane, Execution Plane, operators.

Required fields:

```text
risk_reducing_mode_id
entered_at
reason
scope
blocked_actions
allowed_actions
max_additional_exposure
```

Idempotency key:

```text
RISK_REDUCING_MODE_ENTERED:{scope}:{reason}:{entered_at}
```

### KILL_SWITCH_TRIGGERED

Purpose: records that the External Dead Man Switch observed a trigger and started predefined risk-reducing action or alerting.

Producer: External Dead Man Switch.

Consumer: Ledger Plane, operators, Recovery Component.

Required fields:

```text
kill_switch_event_id
triggered_at
trigger
heartbeat_age_ms
observed_process_id
actions_requested
operator_alert_id
evidence_ref
```

Idempotency key:

```text
KILL_SWITCH_TRIGGERED:{trigger}:{observed_process_id}:{triggered_at}
```

Boundary:

```text
The External Dead Man Switch is independent from the main trading process.
The event documents external action; it must not depend on Signal, ML, dashboard, notebooks, or in-process scheduler health.
```

## Ordering Expectations

Order send sequence:

```text
TRADE_INTENT_CREATED
ORDER_INTENT_CREATED
ORDER_SENT
exchange trading endpoint side effect
ORDER_ACKED or ORDER_ACK_UNKNOWN or reconciliation event
PARTIAL_FILL_RECONCILED or FILL_RECONCILED when cumulative executedQty changes
FLAT_RECONCILED only when all orders and positions are closed and reconciled
```

Recovery sequence:

```text
RECOVERY_BOOT_STARTED
reconcile Ledger event history with exchange open orders, order details, trades, and positions
ORDER_ACKED, PARTIAL_FILL_RECONCILED, FILL_RECONCILED, EXIT_LOCKDOWN, HEDGE_REQUIRED, or FLAT_RECONCILED as evidence requires
RECONCILIATION_COMPLETED
SAFE_MODE_ENTERED if unresolved uncertainty remains beyond automated confidence
SAFE_MODE_EXITED only after operator approval and reconciled truth
```

Forbidden orderings:

```text
ORDER_SENT before ORDER_INTENT_CREATED.
Exchange send before ORDER_SENT is durable.
ORDER_ACKED before ORDER_SENT.
Blind retry after ORDER_ACK_UNKNOWN.
New same-leg slice while previous slice is uncertain.
FLAT_RECONCILED while ACK_UNKNOWN, live order, open position, or Ledger uncertainty exists.
FILL_RECONCILED from WebSocket-only blind delta without cumulative executedQty reconciliation.
```

## ACK_UNKNOWN Reconciliation Algorithm

An `ORDER_ACK_UNKNOWN` aggregate remains uncertain until reconciliation proves one of the terminal paths.

Required lookup keys:

```text
clientOrderId
exchange_order_id when known
venue
account_id
symbol
cumulative executedQty
```

Resolution paths:

| Evidence | Required Ledger result |
|---|---|
| Order found by `clientOrderId`, no fill, still open | Record `ORDER_ACKED`; keep lifecycle pending. |
| Order found by `clientOrderId`, partial cumulative executedQty | Record `ORDER_ACKED` when missing and `PARTIAL_FILL_RECONCILED`. |
| Order found by `clientOrderId`, terminal cumulative executedQty | Record `ORDER_ACKED` when missing and `FILL_RECONCILED`. |
| Order found by `exchange_order_id` only | Link `exchange_order_id` to `client_order_id`, then reconcile cumulative fills. |
| No order, no open order, zero cumulative fill, exchange snapshot is complete | Close uncertainty through reconciliation without retry. |
| Snapshot incomplete, REST 5xx, timeout, missing pages, or mismatched position | Keep `ACK_UNKNOWN`; enter or remain in `RECONCILING`, `EXIT_LOCKDOWN`, or `ERROR_SAFE_MODE`. |

No blind retry rule:

```text
The system must not send another order with the same intent, same leg, or replacement slice merely because ACK_UNKNOWN exists.
Retry is permitted only after reconciliation proves the previous side effect did not create a live order or fill, or after explicit risk-reducing recovery rules choose a different bounded action.
```

## Fill Reconciliation Semantics

The Ledger applies fills only from cumulative exchange truth.

Required cumulative fields:

```text
exchange_cum_qty
ledger_cum_qty
delta_fill
```

Formula:

```text
delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)
```

Rules:

```text
exchange_cum_qty is the exchange cumulative executedQty for a clientOrderId or exchange_order_id.
ledger_cum_qty is the cumulative quantity Ledger has already applied for the same order.
delta_fill is the only quantity that may change Ledger position for the reconciliation observation.
Repeated observations of the same exchange_cum_qty are idempotent.
Lower exchange_cum_qty than ledger_cum_qty is an inconsistency and routes to RECONCILING or ERROR_SAFE_MODE; it must not create a negative fill.
Fees, average price, and liquidity flags may be updated only when tied to the same cumulative fill evidence.
```

## Review Checklist

```text
Each P0 event has purpose, required fields, idempotency key, producer, and consumer.
ORDER_SENT is durable pre-side-effect send attempt, not exchange confirmation.
No order is sent without persisted ORDER_INTENT_CREATED and ORDER_SENT.
clientOrderId is deterministic, versioned, stable after restart, and unique by venue/account/strategy/trade/leg/phase/symbol/attempt or slice.
Fill reconciliation uses cumulative executedQty.
delta_fill = max(0, exchange_cum_qty - ledger_cum_qty).
ACK_UNKNOWN resolves only through reconciliation by clientOrderId, exchange_order_id, and cumulative fills.
No blind retry is allowed after ACK_UNKNOWN.
No new slice may be created on the same leg while a previous slice is uncertain.
Recovery, safe mode, risk-reducing mode, and kill switch audit events are documented.
```
