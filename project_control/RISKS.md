# Risks

## Active Risk Register

| Risk | Severity | Owner | Mitigation | Status |
|---|---|---|---|---|
| Signal sends or implies direct order action | Critical | Architect Agent | Explicit SignalIntent-only interface | Open |
| Order sent without persisted event | Critical | Ledger Agent | Event-first execution contract | Open |
| ACK_UNKNOWN retried blindly | Critical | Execution / Risk Agent | Force reconciliation before retry | Open |
| Fill applied as blind delta | Critical | Ledger Agent | Cumulative executedQty reconciliation | Open |
| Stale or gapped book permits entry | High | Market Data Agent | Book health gate | Open |
| Model used for hard stop or hedge | Critical | Execution / Risk Agent | Deterministic exit invariant | Open |
| Recovery boots into trading before reconciliation | Critical | Ledger Agent | Safe mode boot protocol | Open |
| REST 5xx treated as no fill | Critical | Ledger Agent | Reconcile by order id and cumulative fills before assuming state | Open |
| Missing WebSocket event treated as no fill | Critical | Ledger Agent | REST reconciliation and cumulative executedQty checks | Open |
| Orphan order cancel treated as flat without requery | Critical | Ledger Agent | Safe orphan cancel requires cancel by exchange order id, then requery order/fill state and positions | Open |
| Safe mode permits non-risk-reducing action | Critical | Ledger Agent | Recovery protocol allows only cancellation, reconciliation, and proven risk reduction | Open |
| Recovery resumes without FLAT_RECONCILED or equivalent reconciled state | Critical | Ledger Agent | Normal resume requires zero ACK_UNKNOWN, applied cumulative fills, position match, orphan resolution, and persisted reconciled state | Open |
| Partial fill does not trigger hedge or lockdown | Critical | Execution / Risk Agent | Explicit PARTIALLY_FILLED and HEDGING_REQUIRED routes | Open |
| Ledger uncertainty permits new entry | Critical | Execution / Risk Agent | Fail-closed entry gate on ledger uncertainty | Open |
| Kill switch unavailable or fail-open | Critical | Execution / Risk Agent | Deterministic local kill switch and external heartbeat requirement | Open |
| Missing or stale risk input permits entry | Critical | Execution / Risk Agent | `docs/risk_limits.md` requires missing/stale risk inputs to fail closed | Open |
| Risk-reducing action increases exposure | Critical | Execution / Risk Agent | Stress-risk proof obligation: new stress risk must be lower than old stress risk | Open |
| Forbidden runtime configuration accepted | Critical | Execution / Risk Agent | Reject Cross Margin, Kelly, 10x, live multi-exchange, and leverage before Sprint 26 at config load and pre-order checks | Open |
| Daily loss or drawdown threshold unresolved before live mode | High | PM Agent | Mark as Sprint 1 gate unresolved; live entries fail closed until measurable thresholds are approved | Open |
| Scope drift across agents | Medium | PM Agent | Allowed-file lists and handoffs | Open |

## MVP Forbidden Items

```text
Cross Margin
Kelly sizing
10x leverage
leverage before Sprint 26
blind order retry
live multi-exchange
model-driven emergency exit
```
