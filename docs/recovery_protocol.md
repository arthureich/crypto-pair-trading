# Recovery Protocol Specification

Status: Sprint 1 draft for QA / Chaos Testing review.

Owner: Ledger Agent.

## Purpose

This document defines recovery boot, safe mode, reconciliation order, `ACK_UNKNOWN` resolution, orphan order handling, residual exposure handling, and resume criteria for the crypto futures pairs trading system.

Recovery is safety-critical. The system never boots into normal trading before reconciliation. Process memory, missing responses, missing WebSocket events, or a successful cancel request are never proof that no fill happened.

## Core Invariants

```text
System never boots into normal trading before reconciliation.
Recovery boot starts with normal entries blocked.
Safe mode permits only cancellation, reconciliation, and risk reduction.
Ledger is the transactional truth for orders, fills, positions, and uncertainty.
Exchange snapshots are required to reconcile Ledger truth after crash or uncertainty.
ACK_UNKNOWN is resolved before retry, new slice, or normal resume.
Fill reconciliation uses cumulative executedQty.
Never assume no fill because cancel, REST, or WebSocket response is missing.
REST 5xx or timeout means the exchange side effect is unknown until reconciled.
WebSocket missing event means uncertainty, not zero fill.
Recovery cannot create new strategy entries.
Normal resume requires zero unresolved ACK_UNKNOWN and persisted reconciled state.
```

## Recovery Boot Sequence

Recovery boot is mandatory on process start, crash restart, operator-initiated recovery, unresolved `ORDER_ACK_UNKNOWN`, open order mismatch, position mismatch, REST 5xx, timeout, WebSocket missing event, or any Ledger uncertainty.

Boot sequence:

```text
1. Persist RECOVERY_BOOT_STARTED before any normal trading action.
2. Block new SignalIntent acceptance and all new strategy entries.
3. Enter RECONCILING or ERROR_SAFE_MODE according to docs/state_machine.md.
4. Rebuild trade, order, fill, position, and uncertainty state from Ledger events.
5. Query exchange open orders, order details, cumulative executedQty, recent fills/trades, balances, and positions.
6. Compare exchange state against Ledger-derived state by venue, account, symbol, clientOrderId, and exchange order id.
7. Resolve ACK_UNKNOWN, orphan orders, cumulative fills, residual exposure, and position mismatches.
8. Persist reconciliation evidence through Ledger events and RECONCILIATION_COMPLETED.
9. Remain in safe mode if any required query is incomplete, stale, contradictory, timed out, or returned REST 5xx.
10. Permit normal trading only after the resume criteria in this document are all satisfied.
```

No step may use pre-crash process memory as order, fill, or position truth.

## Safe Mode Rules

Safe mode is the fail-closed operating mode used when recovery cannot prove normal trading is safe.

Allowed actions in safe mode:

```text
cancel open orders
cancel orphan orders by exchange order id
requery order state after cancellation
requery fill state after cancellation
reconcile orders
reconcile cumulative executedQty
reconcile positions
apply cumulative fill deltas to Ledger
place reduce_only risk-reducing exits when supported and bounded by reconciled exposure
place deterministic hedge only when it strictly lowers stress risk
enter EXIT_LOCKDOWN
enter ERROR_SAFE_MODE
alert operator
```

Forbidden actions in safe mode:

```text
new strategy entry
new same-leg slice over uncertain state
blind retry after ACK_UNKNOWN
position-increasing order
gross-notional-increasing order
normal cancel-replace for entry continuation
assuming REST 5xx means no order or no fill
assuming timeout means no order or no fill
assuming WebSocket missing event means no order or no fill
using ML to authorize exits, hedges, reconciliation, or emergency behavior
resuming normal trading without persisted reconciled state
```

Safe mode may perform risk reduction only when the action is deterministic, ML-independent, bounded by reconciled exposure, and satisfies the risk-reducing proof obligation in `docs/risk_limits.md`.

## Reconciliation Order

Recovery reconciles in an order that prevents hidden fills from being missed:

```text
1. Ledger event history and latest committed sequence.
2. Unresolved ORDER_ACK_UNKNOWN aggregates.
3. Exchange open orders by account, symbol, clientOrderId, and exchange order id.
4. Exchange order detail for every Ledger live or uncertain order.
5. Exchange fill/trade history for every relevant clientOrderId and exchange order id.
6. Cumulative executedQty for every order.
7. Exchange position snapshot by symbol.
8. Ledger-derived position by symbol.
9. Orphan orders found on exchange but absent or unresolved in Ledger.
10. Residual exposure and hedge or risk-reduction needs.
```

Fill application must use cumulative exchange quantity:

```text
exchange_cum_qty = exchange cumulative executedQty for the order
ledger_cum_qty = Ledger cumulative quantity already applied for that order
delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)
```

`delta_fill` is the only quantity that may change Ledger position for a reconciliation observation. Duplicate cumulative observations are idempotent. If exchange cumulative executedQty is lower than Ledger cumulative quantity, Recovery must keep the system in `RECONCILING` or `ERROR_SAFE_MODE` until the inconsistency is resolved.

## ACK_UNKNOWN Resolution

`ACK_UNKNOWN` means a send, cancel, replace, hedge, exit, or risk-reducing side effect may have reached the exchange, but the system cannot prove the result.

Resolution requirements:

```text
Resolve by clientOrderId whenever possible.
Use exchange order id when known or discovered.
Check open order state, terminal order state, cumulative executedQty, fills/trades, and position impact.
Persist ORDER_ACKED if the order is found and acknowledgement was missing.
Persist PARTIAL_FILL_RECONCILED or FILL_RECONCILED when cumulative executedQty proves a fill.
Persist reconciled terminal state only when exchange evidence is complete.
Keep ACK_UNKNOWN unresolved when exchange evidence is incomplete, timed out, contradictory, or unavailable.
```

`ACK_UNKNOWN` resolution paths:

| Evidence | Required result |
|---|---|
| Order found by `clientOrderId`, still open, zero cumulative executedQty | Persist `ORDER_ACKED`; keep lifecycle pending and reconciled as open. |
| Order found by `clientOrderId`, cumulative executedQty greater than Ledger quantity | Persist `ORDER_ACKED` if missing and apply cumulative fill reconciliation. |
| Order found by exchange order id only | Link exchange order id to `clientOrderId`, then reconcile cumulative fills and status. |
| No open order, terminal order state found, zero cumulative executedQty, complete exchange evidence | Close uncertainty without retry and persist reconciled terminal evidence. |
| No open order, but order detail/fill pages are incomplete | Keep `ACK_UNKNOWN`; remain in safe mode. |
| REST 5xx, timeout, missing pages, WebSocket missing event, or position mismatch | Keep `ACK_UNKNOWN`; remain in safe mode or `ERROR_SAFE_MODE`. |

Blind retry is forbidden. A retry or new slice is allowed only after reconciliation proves the prior side effect did not create a live order or fill, or after explicit risk-reducing recovery rules select a different bounded action.

## Orphan Order Handling

An orphan order is any exchange order that Recovery cannot match to a complete, current Ledger lifecycle state.

Examples:

```text
exchange open order exists with no matching Ledger order intent
exchange open order exists with matching clientOrderId but unresolved Ledger state
exchange order id exists but clientOrderId is missing, truncated, or not linked in Ledger
exchange reports order or fill history that Ledger has not applied
Ledger believes an order is terminal but exchange reports it open
```

Orphan order handling starts in safe mode. Recovery must never assume an orphan is harmless.

Safe orphan cancel protocol:

```text
1. Persist safe-mode and reconciliation evidence for the orphan.
2. If the orphan has an exchange order id, cancel by exchange order id.
3. If the venue requires symbol/account scope, include the exact exchange symbol and account.
4. After cancel attempt, requery order state by exchange order id.
5. Requery fill/trade state and cumulative executedQty for the same order.
6. Requery position state for affected symbols.
7. Apply any newly proven cumulative fills to Ledger.
8. Persist terminal order or remaining uncertainty evidence.
```

If cancel by exchange order id returns success, Recovery still must requery order state and fill state. A cancel response does not prove zero fill. If the cancel response is missing, REST 5xx, timeout, contradictory, or the WebSocket cancel event is missing, Recovery keeps the system in safe mode.

If an orphan has no usable exchange order id, Recovery must query by account, symbol, time window, clientOrderId when available, and exchange order lists. If the orphan cannot be uniquely identified, automated normal resume is forbidden and operator review is required.

## Residual Exposure Handling

Residual exposure exists when exchange and Ledger prove nonzero position, partial paired exposure, or unmatched leg quantity after reconciliation.

Rules:

```text
Residual exposure blocks new entries.
Residual exposure routes to HEDGING_REQUIRED, EXIT_LOCKDOWN, RECONCILING, or ERROR_SAFE_MODE.
Risk reduction must be bounded by reconciled exchange and Ledger position quantity.
Reduce-only must be used when supported by the venue.
If reduce_only is unavailable, order quantity must not exceed reconciled open exposure.
Hedges and exits must be deterministic and ML-independent.
If stress risk cannot be proven lower after the action, the action is forbidden.
```

Recovery must not continue normal entry sequencing while residual exposure is unresolved.

## REST And WebSocket Failures

REST 5xx, REST timeout, partial REST page, missing order-detail page, missing fill page, WebSocket missing event, stale WebSocket stream, and sequence gaps are uncertainty sources.

Required behavior:

```text
Do not assume the exchange side effect failed.
Do not assume no order exists.
Do not assume no fill exists.
Do not advance to FLAT, IDLE, or POSITION_OPEN from missing evidence.
Keep normal entries blocked.
Remain in RECONCILING, EXIT_LOCKDOWN, or ERROR_SAFE_MODE.
Alert operator when automated evidence remains incomplete beyond configured threshold.
```

WebSocket data may accelerate detection, but it is not sufficient by itself to prove absence of a fill. Missing WebSocket event requires REST and Ledger reconciliation; missing REST evidence keeps the system in safe mode.

## Resume Normal Criteria

Normal trading may resume only when all criteria are true and persisted:

```text
RECOVERY_BOOT_STARTED exists for the recovery run.
RECONCILIATION_COMPLETED exists with decision allowing resume.
zero unresolved ACK_UNKNOWN
all cumulative executedQty observations have been applied idempotently
exchange and Ledger positions match by symbol and account
exchange and Ledger open orders match at zero or known allowed state
all orphan orders are resolved
all residual exposure is resolved or deliberately represented in reconciled state
no REST 5xx, timeout, missing page, or WebSocket missing event remains relevant to unresolved state
no Ledger uncertainty remains
no kill-switch trigger remains unresolved
no forbidden configuration is active
FLAT_RECONCILED or equivalent reconciled state is persisted before normal resume
SAFE_MODE_EXITED is persisted when safe mode was entered
operator approval exists when ERROR_SAFE_MODE required manual review
```

`FLAT_RECONCILED` is the preferred resume evidence for a lifecycle that should be flat. If the system resumes with an intentionally open reconciled position, the equivalent reconciled state must prove zero `ACK_UNKNOWN`, applied cumulative fills, matching Ledger and exchange positions, resolved orphan orders, and no unresolved uncertainty.

## Review Checklist

```text
Recovery boot blocks normal trading before reconciliation.
Safe mode permits only cancellation, reconciliation, and risk reduction.
Cumulative executedQty reconciliation is required.
ACK_UNKNOWN resolution is specified.
Orphan order handling is specified.
Safe orphan cancel means cancel by exchange order id, then requery order/fill state.
REST 5xx or timeout during orphan handling keeps system in safe mode.
Missing WebSocket event never proves no fill.
Cancel response never proves no fill.
Normal resume requires zero ACK_UNKNOWN, cumulative fills applied, matching exchange and Ledger positions, resolved orphan orders, and FLAT_RECONCILED or equivalent persisted reconciled state.
```
