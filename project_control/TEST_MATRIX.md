# TEST_MATRIX

## Categories

```text
unit
integration
backtest
execution
recovery
chaos
financial stress
live readiness
documentation review
```

## Matrix

| Teste | Tipo | Sprint | Modulo | Status | Obrigatorio para gate |
|---|---|---:|---|---|---|
| Architecture forbids Signal/ML order paths | documentation review | 1 | architecture | passed | sim |
| State machine contains all required states | documentation review | 1 | execution | passed | sim |
| State machine critical failures route only to safe states | documentation review | 1 | execution/recovery | passed | sim |
| Negative transition matrix exists | documentation review | 1 | execution | passed | sim |
| P0 event contracts documented | documentation review | 1 | ledger | passed | sim |
| Risk limits define fail-closed behavior | documentation review | 1 | risk | passed | sim |
| Risk forbidden configurations documented | documentation review | 1 | risk | passed | sim |
| Risk entry blockers documented | documentation review | 1 | risk | passed | sim |
| Risk kill-switch triggers have owner threshold action | documentation review | 1 | risk/execution | passed | sim |
| Risk-reducing proof obligation documented | documentation review | 1 | risk/execution | passed | sim |
| Recovery boot blocks new entries | documentation review | 1 | recovery | passed | sim |
| Recovery safe mode allowed actions documented | documentation review | 1 | recovery | passed | sim |
| Recovery ACK_UNKNOWN resolution documented | documentation review | 1 | recovery/ledger | passed | sim |
| Recovery orphan order handling documented | documentation review | 1 | recovery/ledger | passed | sim |
| Recovery REST 5xx and WebSocket missing event fail closed | documentation review | 1 | recovery | passed | sim |
| Recovery cumulative executedQty reconciliation documented | documentation review | 1 | recovery/ledger | passed | sim |
| Recovery resume requires FLAT_RECONCILED or equivalent reconciled state | documentation review | 1 | recovery/ledger | passed | sim |
| SQLite WAL bootstrap migration applies required tables | integration | 2 | ledger | passed | sim |
| EventStore append-only persistence and idempotency | unit | 2 | ledger | passed | sim |
| EventStore sequence gap and failed append rollback | chaos | 2 | ledger | passed | sim |
| EventStore trade event and open position rebuild reads | unit | 2 | ledger | passed | sim |
| Order cannot be sent before persisted event | unit | 2 | ledger/execution | pending | sim |
| Fill duplicado nao duplica posicao | integration | 3 | ledger/reconciliation | passed | sim |
| ACK_UNKNOWN forca reconciliacao | integration | 3 | execution/ledger | passed | sim |
| Crash apos ORDER_SENT | chaos | 4 | recovery | passed | sim |
| Partial fill enters hedge or lockdown route | integration | 4 | execution/recovery | passed | sim |
| Book gap invalida book | unit | 5 | market_data | passed | sim |
| Book stale invalida entry eligibility | unit | 5 | market_data | passed | sim |
| Snapshot mismatch/incomplete exige resync | unit | 5 | market_data | passed | sim |
| Execution spread/depth/imbalance features | unit | 6 | features | passed | sim |
| Slippage estimator detects cost and insufficient liquidity | unit | 6 | execution | passed | sim |
| Feature cache freshness fails closed | unit | 6 | market_data | passed | sim |
| Book stale bloqueia entrada | execution | 6 | execution risk gate | pending | sim |
| Backtest sem look-ahead bias | backtest | 8 | backtest | pending | sim |
| Kill switch trigger fails closed | live readiness | 14 | execution | pending | sim |

## Sprint 1 Review Checks

```text
docs/architecture.md defines every plane and forbidden dependency.
docs/state_machine.md defines inbound and outbound transitions for all required states.
docs/state_machine.md contains a negative transition matrix.
docs/state_machine.md maps each critical failure to RECONCILING, EXIT_LOCKDOWN, or ERROR_SAFE_MODE.
docs/event_contracts.md defines P0 events and idempotency keys.
docs/risk_limits.md defines MVP forbidden items and kill conditions.
docs/risk_limits.md documents Cross Margin, Kelly, 10x, live multi-exchange, and leverage before Sprint 26 as forbidden configurations.
docs/risk_limits.md documents stale book, ledger uncertainty, and ACK_UNKNOWN as entry blockers.
docs/risk_limits.md documents kill-switch triggers with owner, threshold, and action.
docs/risk_limits.md documents fail-closed behavior for missing or stale risk inputs.
docs/risk_limits.md documents that risk-reducing behavior cannot increase exposure and must prove new stress risk is lower than old stress risk.
docs/recovery_protocol.md defines recovery boot and reconciliation-first normal-entry blocking.
docs/recovery_protocol.md defines safe mode allowed actions as cancellation, reconciliation, and risk reduction only.
docs/recovery_protocol.md defines ACK_UNKNOWN resolution, orphan order handling, safe orphan cancel, REST 5xx, WebSocket missing event, cumulative executedQty, and FLAT_RECONCILED resume requirements.
```

## Sprint 2 Ledger Checks

```text
pytest tests/test_event_store.py
Result: passed, 7 tests.

Covered bootstrap migration, WAL, foreign_keys, required tables, EventStore append persistence, append-only events trigger behavior, duplicate idempotency no-op/readback, sequence gap rejection, failed append rollback, trade event loading, and open position loading.
```

## Sprint 3 Integration Checks

```text
pytest tests/test_client_order_id.py tests/test_idempotency.py tests/test_cumulative_reconciliation.py tests/test_ack_guard.py
Result: passed, 57 tests.

pytest tests
Result: passed, 64 tests.

Covered deterministic clientOrderId flowing into ORDER_INTENT_CREATED and ORDER_SENT idempotency keys, attempt/slice idempotency key domain separation, duplicate cumulative fill observations producing zero additional delta and stable idempotency keys, unresolved ORDER_SENT/ACK_UNKNOWN blocking blind retry and same-leg slices, and resolved no-order/no-fill retry only from explicit same-scope state.
```

## Sprint 4 Recovery Checks

```text
pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py tests/test_partial_fill_route.py --basetemp=pytest_temp_run_s4d -o cache_dir=pytest_temp_run_s4d/.pytest_cache
Result: passed, 29 tests.

pytest tests --basetemp=pytest_temp_run_all5 -o cache_dir=pytest_temp_run_all5/.pytest_cache
Result: passed, 93 tests.

Covered crash after durable ORDER_SENT routing to unresolved recovery state, recovery boot blocking normal entries until reconciled truth exists, and partial fill routing to HEDGING_REQUIRED only with risk-reducing proof or EXIT_LOCKDOWN otherwise.
```

## Sprint 5 Market Data Book Health Checks

```text
pytest tests/test_book_health.py
Result: passed, 20 tests.

pytest tests
Result: initial run hit a Windows permission error removing the default pytest_temp directory before EventStore tests.

pytest tests --basetemp=pytest_temp_run_s5_gate_all -o cache_dir=pytest_temp_run_s5_gate_all/.pytest_cache
Result: passed, 113 tests.

ruff check src\market_data tests\test_book_health.py
Result: passed.

Covered L2 update dataclass/model, book health status/reason enums, healthy in-sequence updates, sequence gap invalidation and entry blocking, stale book entry blocking, snapshot mismatch/incomplete snapshot resync, missing snapshot sequence resync, and healthy in-sequence no-resync behavior.
```

## Sprint 6 Execution Features and Slippage Checks

```text
pytest tests/test_execution_features.py
Result: passed, 10 tests.

pytest tests/test_slippage_estimator.py
Result: passed, 7 tests.

pytest tests --basetemp=pytest_temp_run_s6_p1_all -o cache_dir=pytest_temp_run_s6_p1_all/.pytest_cache
Result: passed, 130 tests.

ruff check src\features src\execution\slippage_estimator.py src\market_data\feature_cache.py tests\test_execution_features.py tests\test_slippage_estimator.py
Result: passed.

Covered BookExecutionFeatures model construction, spread_bps, mid_price, 5bps/10bps bid and ask depth, deterministic imbalance, zero-quantity level filtering, malformed book fail-closed behavior, rolling 1s/5s volatility without future data, stale/invalid/resync-required fail-closed usability, buy ask-side slippage, sell bid-side slippage, invalid-request handling, insufficient-liquidity failure reason, and FeatureCache stale fail-closed behavior.
```
