# INTERFACES

Status: Sprint 1 contract baseline.

Any contract change requires an ADR in `project_control/DECISIONS.md`.

## Plane Boundaries

### Signal Plane to Execution Plane

Signal Plane emits only `SignalIntent`.

Signal Plane must not:

```text
send orders
cancel orders
replace orders
modify positions
write live order state
trigger emergency exit
call exchange trading endpoints
```

### Execution Plane to Ledger Plane

Execution requests durable writes before external side effects.

Required invariant:

```text
No order is sent before ORDER_INTENT_CREATED and ORDER_SENT are persisted.
ORDER_SENT means a durable pre-side-effect send attempt record, not exchange confirmation.
```

### Ledger Plane to Recovery

Ledger exposes event history, open orders, open positions, reconciliation runs, and cumulative fill state. Recovery rebuilds from persisted events and exchange snapshots, never from process memory.

### Market Data Plane to Execution Plane

Market Data exposes `BookFeatures` and health flags. Entry is blocked when book data is stale, out of sync, too shallow, or too expensive to execute.

### ML Component to Signal Plane

ML exposes `ModelPrediction` only to Signal. ML must not affect deterministic exits, hedges, recovery, reconciliation, hard stops, or emergency liquidation.

### Recovery Component to Ledger and Execution

Recovery blocks new entries during boot and uncertainty. It coordinates reconciliation and risk-reducing actions, but cannot create new strategy entries.

Detailed recovery boot, safe mode, `ACK_UNKNOWN` resolution, orphan order handling, safe orphan cancel, REST 5xx and timeout behavior, WebSocket missing event handling, cumulative `executedQty` reconciliation, and normal resume criteria are specified in `docs/recovery_protocol.md`.

### External Dead Man Switch to Exchange and Operators

The External Dead Man Switch is outside the main trading process and must not depend on Signal, ML, dashboard, notebooks, or in-process scheduler health. It may alert, cancel open orders, and trigger predefined risk-reducing liquidation when heartbeat is missing.

## Contract: SignalIntent

## Version

v0.1

## Producer

Signal Plane

## Consumer

Execution Plane

## Required Fields

```text
signal_id
pair_id
leg_a_symbol
leg_b_symbol
side_a
side_b
target_notional
z_score
half_life
beta
expected_edge_bps
created_at
expires_at
barrier_policy_id
```

## Optional Fields

```text
model_version
model_prediction_id
regime_id
notes
```

## Validation Rules

```text
SignalIntent is advisory only.
expires_at must be greater than created_at.
target_notional must be positive and still subject to RiskGateResult.
side_a and side_b must describe a paired long/short relationship.
```

## Compatibility

Additive optional fields are compatible. Required field changes require ADR.

## Example

```text
SignalIntent(signal_id=S-20260628-000001, pair_id=BTC-ETH, target_notional=100)
```

## Contract: BarrierPolicy

## Version

v0.1

## Producer

Signal Plane

## Consumer

Execution Plane

## Required Fields

```text
barrier_policy_id
profit_barrier_bps
stop_barrier_bps
vertical_barrier_seconds
created_at
```

## Optional Fields

```text
max_holding_seconds
soft_stop_bps
regime_id
```

## Validation Rules

```text
Hard stop must be deterministic and ML-independent.
vertical_barrier_seconds must be positive.
Execution may tighten or reject policy through risk limits.
```

## Compatibility

Changing barrier semantics requires ADR.

## Example

```text
BarrierPolicy(id=BP-001, profit=35bps, stop=20bps, vertical=1800s)
```

## Contract: OrderIntent

## Version

v0.1

## Producer

Execution Plane

## Consumer

Ledger Plane

## Required Fields

```text
order_intent_id
trade_id
venue
account_id
symbol
leg
phase
side
order_type
quantity
client_order_id
created_at
```

## Optional Fields

```text
limit_price
reduce_only
time_in_force
parent_signal_id
```

## Validation Rules

```text
client_order_id must be deterministic.
quantity must be positive.
reduce_only must be true for risk-reducing exits when supported.
No exchange send before durable ORDER_INTENT_CREATED and ORDER_SENT.
```

## Compatibility

Required field changes require ADR.

## Example

```text
OrderIntent(trade=T-000001, leg=A, phase=ENTRY, client_order_id=PKF-20260628-000001-A-ENTRY-001)
```

## Contract: OrderEvent

## Version

v0.1

## Producer

Execution Plane, Ledger Plane, Reconciliation

## Consumer

Ledger Plane, Recovery Component

## Required Fields

```text
event_id
event_type
trade_id
client_order_id
event_time
idempotency_key
```

## Optional Fields

```text
exchange_order_id
status
reason
raw_payload_ref
```

## Validation Rules

```text
ORDER_SENT is durable pre-side-effect send attempt record.
ORDER_ACK_UNKNOWN blocks blind retry.
Duplicate idempotency_key must not duplicate state.
```

## Compatibility

New event types require TASK-003 update and may require ADR.

## Example

```text
OrderEvent(type=ORDER_ACK_UNKNOWN, client_order_id=PKF-20260628-000001-A-ENTRY-001)
```

## Contract: FillEvent

## Version

v0.1

## Producer

Reconciliation

## Consumer

Ledger Plane, Execution Plane

## Required Fields

```text
fill_event_id
trade_id
client_order_id
exchange_order_id
symbol
executed_qty_cumulative
ledger_qty_before
delta_fill
event_time
idempotency_key
```

## Optional Fields

```text
avg_price
fee
fee_asset
liquidity_flag
raw_payload_ref
```

## Validation Rules

```text
delta_fill = max(0, executed_qty_cumulative - ledger_qty_before)
No blind delta fills.
Duplicate cumulative observations are idempotent.
```

## Compatibility

Changing fill math requires ADR.

## Example

```text
FillEvent(cum=0.05, ledger_before=0.03, delta=0.02)
```

## Contract: RiskGateResult

## Version

v0.1

## Producer

Execution / Risk Agent

## Consumer

Execution Plane

## Required Fields

```text
risk_gate_result_id
signal_id
decision
reasons
evaluated_at
```

## Optional Fields

```text
max_notional
estimated_slippage_bps
book_age_ms
ledger_uncertainty_flag
```

## Validation Rules

```text
decision must be APPROVE, REJECT, or BLOCK.
Book stale blocks entry.
Ledger uncertainty blocks entry.
ACK_UNKNOWN blocks entry.
```

## Compatibility

New decision values require ADR.

## Example

```text
RiskGateResult(decision=BLOCK, reasons=[LEDGER_UNCERTAIN])
```

## Contract: ExecutionCommand

## Version

v0.1

## Producer

Execution Plane, Recovery Component

## Consumer

Execution Plane order control

## Required Fields

```text
command_id
command_type
trade_id
reason
created_at
```

## Optional Fields

```text
client_order_id
symbol
quantity
reduce_only
limit_price
```

## Validation Rules

```text
Risk-reducing commands must not increase stress risk.
Commands from Recovery cannot create new strategy entries.
Exit, hedge, and recovery commands must be ML-independent.
```

## Compatibility

New command types require ADR when they affect order lifecycle.

## Example

```text
ExecutionCommand(type=ENTER_SAFE_MODE, reason=ACK_UNKNOWN_UNRESOLVED)
```

## Contract: LedgerEvent

## Version

v0.1

## Producer

Ledger Plane clients through Ledger API

## Consumer

Ledger Plane, Recovery Component, audit tools

## Required Fields

```text
event_id
event_type
aggregate_id
sequence
occurred_at
payload
idempotency_key
schema_version
```

## Optional Fields

```text
correlation_id
causation_id
raw_payload_ref
```

## Validation Rules

```text
Append-only.
Single writer.
Sequence must be monotonic per aggregate.
Duplicate idempotency_key must not duplicate state.
```

## Compatibility

Schema changes require ADR and migration plan.

## Example

```text
LedgerEvent(type=ORDER_SENT, aggregate=T-000001, sequence=3)
```

## Contract: RecoverySnapshot

## Version

v0.1

## Producer

Recovery Component

## Consumer

Ledger Plane, Execution Plane

## Required Fields

```text
recovery_snapshot_id
started_at
ledger_state_hash
exchange_open_orders
exchange_positions
unresolved_orders
unresolved_positions
decision
```

## Optional Fields

```text
completed_at
safe_mode_reason
operator_note
```

## Validation Rules

```text
Normal trading cannot resume with unresolved ACK_UNKNOWN.
Normal trading cannot resume if ledger and exchange positions differ.
REST 5xx or timeout keeps recovery unresolved.
```

## Compatibility

Recovery decision semantics require ADR if changed.

## Example

```text
RecoverySnapshot(decision=SAFE_MODE, unresolved_orders=1)
```

## Contract: ModelPrediction

## Version

v0.1

## Producer

ML Component

## Consumer

Signal Plane

## Required Fields

```text
model_prediction_id
model_version
signal_id
p_fill
p_profit_given_fill
calibration_method
predicted_at
```

## Optional Fields

```text
feature_set_version
confidence
explanation_ref
```

## Validation Rules

```text
ModelPrediction is advisory.
It cannot drive exits, hedges, reconciliation, or emergency behavior.
p_fill and p_profit_given_fill must be in [0, 1].
```

## Compatibility

Model schema or calibration changes require model registry record; live control changes require ADR.

## Example

```text
ModelPrediction(model=v1, p_fill=0.62, p_profit_given_fill=0.54)
```

## Contract: BookFeatures

## Version

v0.1

## Producer

Market Data Plane

## Consumer

Signal Plane, Execution Plane

## Required Fields

```text
symbol
best_bid
best_ask
book_age_ms
in_sync
spread_bps
depth_5bps
depth_10bps
estimated_slippage_bps
observed_at
```

## Optional Fields

```text
order_book_imbalance
volatility_1s
volatility_5s
source_sequence
```

## Validation Rules

```text
in_sync false blocks entry.
book_age_ms above threshold blocks entry.
BookFeatures cannot create fill or position truth.
```

## Compatibility

Additive optional fields are compatible. Required health semantics require ADR.

## Example

```text
BookFeatures(symbol=BTCUSDT, in_sync=true, book_age_ms=42, spread_bps=1.1)
```

## P0 Events

Detailed payload, producer, consumer, idempotency, ordering, `clientOrderId`, ACK_UNKNOWN, no blind retry, no uncertain same-leg slice, and cumulative `executedQty` reconciliation semantics are specified in `docs/event_contracts.md`.

```text
TRADE_INTENT_CREATED
ORDER_INTENT_CREATED
ORDER_SENT
ORDER_ACKED
ORDER_ACK_UNKNOWN
PARTIAL_FILL_RECONCILED
FILL_RECONCILED
HEDGE_REQUIRED
EXIT_LOCKDOWN
FLAT_RECONCILED
```

## Sprint 1 Audit Events To Specify

These Sprint 1 audit events are specified in `docs/event_contracts.md`. Recovery, safe mode, risk-reducing mode, and kill switch actions must emit audit evidence before normal operation can resume or operators can close the incident.

```text
RECOVERY_BOOT_STARTED
RECONCILIATION_COMPLETED
SAFE_MODE_ENTERED
SAFE_MODE_EXITED
RISK_REDUCING_MODE_ENTERED
KILL_SWITCH_TRIGGERED
```
