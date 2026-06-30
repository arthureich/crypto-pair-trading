# Risk Limits Specification

Status: Sprint 1 draft for QA / Chaos Testing review.

Owner: Execution / Risk Agent.

## Purpose

This document defines MVP risk limits, forbidden configurations, entry blockers, kill-switch triggers, fail-closed behavior, and risk-reducing mode rules for the crypto futures pairs trading system.

Risk policy is safety-critical. If Risk cannot prove a condition is safe, the system must reject new entries, block exposure increases, enter risk-reducing mode, or enter safe mode according to `docs/state_machine.md`.

## Core Invariants

```text
Ledger is the source of truth for orders, fills, positions, and uncertainty.
Missing risk input fails closed.
Stale risk input fails closed.
ACK_UNKNOWN blocks new entries and blind retry.
Ledger uncertainty blocks new entries.
Stale book blocks new entries.
Risk-reducing behavior cannot increase exposure.
Risk-reducing behavior must prove new stress risk is lower than old stress risk before action.
Execution exits, hedges, reconciliation, lockdown, and safe mode must not depend on ML.
```

## Forbidden Configurations

The following configurations are forbidden in MVP and must be rejected at configuration load, risk gate evaluation, and pre-order checks:

| Forbidden item | Detection rule | Required action |
|---|---|---|
| Cross Margin | `margin_mode` is `cross`, `CROSS`, or venue-equivalent | Reject config, block trading, alert operator |
| Kelly | sizing policy name, mode, or formula contains Kelly sizing | Reject config, block entries, require ADR before reconsideration |
| 10x | requested or effective leverage is `10x` or greater | Reject config, block trading, alert operator |
| live multi-exchange | live mode has more than one exchange venue enabled for trading endpoints | Reject config, block trading, require ADR and later sprint approval |
| leverage before Sprint 26 | requested or effective leverage is greater than `1.0x` before Sprint 26 | Reject config, block trading, alert operator |

Deployment gates:

```text
Only isolated margin is allowed.
Any leverage before Sprint 26 is forbidden.
Cross Margin is forbidden.
Kelly sizing is forbidden.
10x leverage is forbidden.
Live multi-exchange trading is forbidden.
Paper multi-exchange research is allowed only when it cannot call live trading endpoints.
```

## MVP Exposure Limits

These limits are intentionally conservative and testable. They apply after all forbidden configuration checks and before any `ORDER_INTENT_CREATED` event.

| Limit | Threshold | Scope | Action on breach |
|---|---:|---|---|
| Per-trade gross notional | min(`100 USDT`, `0.50%` of reconciled account equity) | trade lifecycle | Reject entry |
| Total open gross notional | min(`300 USDT`, `1.50%` of reconciled account equity) | account and strategy | Block new entries |
| Per-leg notional imbalance after entry | `<= 2.0%` of intended paired notional or `<= 5 USDT`, whichever is larger | trade lifecycle | Route to `HEDGING_REQUIRED` or reject entry before send |
| Max open live strategy trades | `1` | account and strategy | Block new entries |
| Max same-pair active lifecycle | `1` | pair and venue | Block duplicate entry |
| Max entry slippage estimate | `5 bps` per leg | symbol and intended size | Reject entry |
| Max combined entry spread | `8 bps` across both legs | pair | Reject entry |
| Max book age | `250 ms` | symbol | Block entry |
| Min book depth within 10 bps | `2x` intended leg notional | symbol | Reject entry |
| Max unresolved order uncertainty | `0` | account and strategy | Block entries |
| Max unresolved position uncertainty | `0` | account and strategy | Block entries |
| Max daily realized loss | Sprint 1 gate unresolved: must be set before live trading | account and strategy | Until resolved, live entries fail closed |
| Max drawdown from session high-water mark | Sprint 1 gate unresolved: must be set before live trading | account and strategy | Until resolved, live entries fail closed |

Unresolved Sprint 1 gate items are not permission gaps. They are live-readiness blockers. Until a numeric threshold is approved, live entries must fail closed.

## Required Risk Inputs

Risk evaluation requires all inputs below to be present, fresh, and internally consistent:

| Input | Freshness or validity threshold | Missing/stale action |
|---|---|---|
| Ledger-derived open orders | current through latest committed Ledger sequence | Block entries; enter `RECONCILING` if inconsistent |
| Ledger-derived positions | current through latest committed Ledger sequence | Block entries; enter `RECONCILING` if inconsistent |
| ACK_UNKNOWN count | must equal `0` for entries | Block entries and reconciliation-first handling |
| Account equity snapshot | age `<= 5 s` and reconciled with venue snapshot | Block entries |
| Per-symbol `BookFeatures` | `book_age_ms <= 250` and `in_sync = true` | Block entries |
| Estimated slippage | computed for intended order size on both legs | Reject or block entry |
| Margin mode | must prove isolated margin | Block trading if missing or not isolated |
| Leverage setting | must prove `<= 1.0x` before Sprint 26 | Block trading if missing or above threshold |
| Kill-switch heartbeat state | heartbeat age must be within configured threshold | Block new entries; trigger kill switch if threshold breached |
| Configuration version | signed or approved config version known to runtime | Block trading |

Fail-closed rule:

```text
Missing input = unsafe.
Stale input = unsafe.
Contradictory input = unsafe.
Unknown input provenance = unsafe.
Unsafe means no new entry, no exposure increase, and no normal-mode resume.
```

## Entry Blockers

The Risk Gate must return `BLOCK` or `REJECT` before any entry order intent when one or more blockers exists.

| Blocker | Required detection | Action |
|---|---|---|
| stale book | `book_age_ms > 250`, `in_sync = false`, sequence gap, snapshot mismatch, or missing `BookFeatures` | Block entry; request market-data resync |
| ledger uncertainty | Ledger cannot derive exactly one current order and position truth | Block entry; route to `RECONCILING` |
| ACK_UNKNOWN | any unresolved `ORDER_ACK_UNKNOWN` for account, strategy, trade, pair, or same leg | Block entry; reconciliation required |
| live order exists | exchange or Ledger shows open order for same pair lifecycle | Block duplicate entry |
| position exists | exchange or Ledger shows open position for same pair lifecycle | Block duplicate entry unless deterministic risk reduction |
| unresolved partial fill | cumulative executedQty proves partial exposure that is not fully hedged or bounded | Block entry; route to `HEDGING_REQUIRED` or `EXIT_LOCKDOWN` |
| account equity stale | equity snapshot age `> 5 s` or venue snapshot incomplete | Block entry |
| forbidden configuration | Cross Margin, Kelly, 10x, live multi-exchange, or leverage before Sprint 26 | Reject configuration and block trading |
| slippage breach | per-leg estimated slippage `> 5 bps` | Reject entry |
| spread breach | combined pair spread `> 8 bps` | Reject entry |
| insufficient depth | depth within 10 bps is less than `2x` intended leg notional | Reject entry |
| recovery active | `RECOVERY_BOOT_STARTED`, `RECONCILING`, `ERROR_SAFE_MODE`, or unresolved recovery snapshot exists | Block entry |
| kill switch active | `KILL_SWITCH_TRIGGERED` unresolved or external heartbeat unsafe | Block entry and stay fail-closed |

Entry blockers are evaluated before `TRADE_INTENT_CREATED` where possible and again before `ORDER_INTENT_CREATED`. If a blocker appears after `ORDER_SENT`, the lifecycle follows recovery, hedge, lockdown, or safe-mode routing instead of continuing entry.

## Kill-Switch Triggers

Kill-switch behavior has two layers:

```text
Execution/Risk local kill switch blocks new entries and coordinates safe mode.
External Dead Man Switch runs independently and can alert, cancel open orders, and trigger predefined risk-reducing liquidation.
```

Every trigger must emit or require audit evidence through `KILL_SWITCH_TRIGGERED`, `SAFE_MODE_ENTERED`, `RISK_REDUCING_MODE_ENTERED`, or related recovery events.

| Trigger | Owner | Threshold | Required action |
|---|---|---|---|
| main process heartbeat missing | External Dead Man Switch | heartbeat age `> 3000 ms` | Emit `KILL_SWITCH_TRIGGERED`, alert operator, cancel open orders, block new entries |
| risk evaluation heartbeat missing | Execution / Risk Agent | no successful risk gate health update for `> 2000 ms` | Enter safe mode, block entries, alert operator |
| Ledger write unavailable | Ledger Agent | any failed required pre-side-effect Ledger append | Block exchange side effects, enter `ERROR_SAFE_MODE` if active lifecycle cannot continue safely |
| unresolved ACK_UNKNOWN | Execution / Risk Agent | any `ACK_UNKNOWN` unresolved for `> 30 s` | Enter `RECONCILING`; if still unresolved after `120 s`, enter `ERROR_SAFE_MODE` and alert |
| stale market data during entry candidate | Market Data Agent | any leg `book_age_ms > 250` or `in_sync = false` | Block entry and request resync |
| stale market data with active exposure | Execution / Risk Agent | both legs stale or unsafely priced for `> 2000 ms` | Enter `EXIT_LOCKDOWN` or `ERROR_SAFE_MODE`; only bounded risk reduction allowed |
| account equity stale | Execution / Risk Agent | snapshot age `> 5 s` | Block entries; alert if stale for `> 60 s` |
| position mismatch | Ledger Agent | Ledger position differs from exchange snapshot by any nonzero quantity | Enter `RECONCILING`; block entries; alert if unresolved after `120 s` |
| open order mismatch | Ledger Agent | exchange open order not represented in Ledger, or Ledger live order missing from exchange snapshot without terminal proof | Enter `RECONCILING`; block entries |
| realized daily loss threshold unavailable | Execution / Risk Agent | threshold not configured before live mode | Fail closed: live entries disabled |
| realized daily loss breach | Execution / Risk Agent | Sprint 1 gate unresolved numeric threshold | When resolved, block entries and enter risk-reducing mode |
| drawdown threshold unavailable | Execution / Risk Agent | threshold not configured before live mode | Fail closed: live entries disabled |
| forbidden configuration detected at runtime | Execution / Risk Agent | Cross Margin, Kelly, 10x, live multi-exchange, or leverage before Sprint 26 | Block trading, enter safe mode, alert operator |
| kill-switch audit event cannot be persisted | Ledger Agent | required audit event append fails | Continue external protective action, alert operator, keep normal trading disabled |

## Risk-Reducing Mode

Risk-reducing mode allows only actions that reduce, freeze, or reconcile exposure. It cannot create new strategy entries and cannot increase stress risk.

Allowed actions:

```text
cancel open orders
reconcile open orders
reconcile positions
place reduce_only exits when supported by venue
place deterministic hedge only when it lowers stress risk
flatten known exposure when Ledger and exchange snapshots identify the quantity
enter EXIT_LOCKDOWN
enter ERROR_SAFE_MODE
alert operator
```

Forbidden actions in risk-reducing mode:

```text
new strategy entry
same-leg uncertain slice
increase gross notional
increase net directional exposure
increase worst-case stress loss
use ML to authorize or parametrize emergency behavior
blind retry after ACK_UNKNOWN
assume REST 5xx means no fill
assume missing WebSocket event means no fill
```

Proof obligation:

```text
Before a risk-reducing order is sent, Execution must compute old_stress_risk and new_stress_risk.
new_stress_risk must be strictly lower than old_stress_risk.
If new_stress_risk cannot be computed, the action is not proven risk-reducing and must fail closed.
If reduce_only is supported by the venue, risk-reducing orders must set reduce_only = true.
If reduce_only is unavailable, quantity must be bounded by reconciled open exposure and must not exceed that exposure.
```

Sprint 1 stress-risk formula:

```text
stress_risk = gross_open_notional
            + abs(net_base_delta_notional)
            + unresolved_order_notional
            + unresolved_position_notional
```

This formula is intentionally simple for Sprint 1. A future replacement must be measurable, monotonic for exposure increases, and approved through ADR before implementation.

## Escalation Behavior

| Condition | Immediate mode | Escalation |
|---|---|---|
| entry blocker only, no active exposure | normal mode with entry blocked | remain blocked until input is fresh and safe |
| uncertainty with active order | `RECONCILING` | `ERROR_SAFE_MODE` if unresolved beyond trigger threshold |
| partial exposure imbalance | `HEDGING_REQUIRED` or `EXIT_LOCKDOWN` | `ERROR_SAFE_MODE` if hedge/reduction cannot prove lower stress risk |
| forbidden runtime configuration | `ERROR_SAFE_MODE` | operator approval and corrected config required before resume |
| kill switch active | safe mode or risk-reducing mode | normal trading resumes only after audit evidence and reconciled truth |
| missing daily loss or drawdown thresholds in live mode | fail-closed live entry block | PM/QA must resolve Sprint 1 gate item before live readiness |

Resume requirements:

```text
No ACK_UNKNOWN remains.
No Ledger uncertainty remains.
No stale required risk input remains.
No kill-switch trigger remains unresolved.
No forbidden configuration is present.
Ledger and exchange agree on open orders and positions.
Operator approval exists where safe mode was entered.
```

## Review Checklist

```text
Forbidden configurations are explicit: Cross Margin, Kelly, 10x, live multi-exchange, leverage before Sprint 26.
Entry blockers include stale book, ledger uncertainty, and ACK_UNKNOWN.
Kill-switch triggers list owner, threshold, and action.
Missing or stale risk inputs fail closed.
Thresholds are measurable or marked as unresolved Sprint 1 gate items.
Risk-reducing behavior cannot increase exposure.
Risk-reducing behavior includes proof obligation: new stress risk must be lower than old stress risk.
No risk-reducing action depends on ML.
Unresolved daily loss and drawdown thresholds block live readiness until resolved.
```
