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
| LocalOrderBook snapshot/diff gate correction | unit | 5 | market_data | passed | sim |
| BookFeatures book_age_ms/in_sync gate correction | unit | 6 | features | passed | sim |
| Book stale bloqueia entrada | execution | 6 | execution risk gate | pending | sim |
| Pair selection rejects insufficient data | unit | 7 | research | passed | sim |
| Pair selection rejects low correlation | unit | 7 | research | passed | sim |
| Pair selection ranks candidates by score | unit | 7 | research | passed | sim |
| ADF/KPSS wrappers return standardized results | unit | 7 | research | passed | sim |
| Preliminary half-life is calculated | unit | 7 | research | passed | sim |
| Kalman recovers synthetic beta | unit | 7 | research | passed | sim |
| Kalman spread length matches input series | unit | 7 | research | passed | sim |
| Kalman flags unstable beta | unit | 7 | research | passed | sim |
| OU estimates positive theta for mean-reverting synthetic series | unit | 7 | research | passed | sim |
| OU rejects or warns theta <= 0 | unit | 7 | research | passed | sim |
| Rolling z-score avoids look-ahead | unit | 7 | research | passed | sim |
| Rolling correlation avoids look-ahead | unit | 7 | research | passed | sim |
| Pair selection execution cost filters fail closed | unit | 7 | research | passed | sim |
| OU sigma respects non-unit dt | unit | 7 | research | passed | sim |
| Historical dataset checksum parser/verifier | unit | 7 | research | passed | sim |
| Historical dataset normalizer no-forward-fill gaps | unit | 7 | research | passed | sim |
| Historical dataset archive plan feeds pair selection | integration | 7 | research | passed | sim |
| Sprint 7 historical runner local no-download smoke | integration | 7 | research | passed | sim |
| Sprint 7 historical runner real one-month smoke | integration | 7 | research | passed | nao |
| Sprint 7 full Binance USD-M dataset normalization | integration | 7 | research | passed | sim |
| Sprint 7 real statistical research gate | integration | 7 | research | passed | sim |
| Historical dataset headerless Binance CSV preserves first row | unit | 7 | research | passed | sim |
| Historical dataset checksum mismatch rejected before normalization | unit | 7 | research | passed | sim |
| Execution-cost evidence book-ticker normalization/hourly schema | unit | 7 | research | passed | sim |
| Execution-cost gate forces cost_gated_pass=false when source incomplete | unit | 7 | research | passed | sim |
| Sprint 7 historical execution-cost evidence source review | documentation review | 7 | market_data | passed (SOURCE_INCOMPLETE_FAIL_CLOSED, verified against live source) | sim |
| Sprint 7 cost-gated execution-cost evidence | integration | 7 | research/market_data | passed (definitive: cost_gated_pass=false for all 41 pairs, evidence source incomplete) | sim |
| TASK-007-09 Market Data Agent review | documentation review | 7 | market_data | passed (2 P3, non-blocking) | sim |
| TASK-007-09 QA Agent fail-closed review | documentation review | 7 | research | passed (2 P2 + 1 P3, non-blocking) | sim |
| TASK-007-10 QA Agent independent re-review (S3 pagination, no-default-approve) | documentation review | 7 | research/market_data | passed (1 P2, non-blocking) | sim |
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

## Sprint 5/6 Gate Correction Checks

```text
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_book_builder.py tests/test_book_health.py tests/test_execution_features.py tests/test_slippage_estimator.py --basetemp=pytest_temp_run_s5s6_gate_fix -o cache_dir=pytest_temp_run_s5s6_gate_fix/.pytest_cache
Result: passed, 47 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_s5s6_gate_fix_all -o cache_dir=pytest_temp_run_s5s6_gate_fix_all/.pytest_cache
Result: passed, 140 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check .
Result: passed.

Covered LocalOrderBook/BookBuilder snapshot application, in-sequence diff
application, old update discard, gap invalidation, zero-quantity level removal,
best bid/ask, book_age_ms, in_sync/valid/needs_resync, stale detection, empty
book invalidation, explicit BookExecutionFeatures book_age_ms/in_sync, feature
cache fail-closed behavior, and no DataFrame/Pandas hot path in market-data,
feature, slippage, or cache modules.
```

## Sprint 7 Research Base Checks

```text
Required commands:
pytest tests/test_pair_selection.py
pytest tests/test_stationarity.py
pytest tests/test_kalman.py
pytest tests/test_ou.py

Result:
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py --basetemp=pytest_temp_run_sprint7_final_core -o cache_dir=pytest_temp_run_sprint7_final_core/.pytest_cache
passed, 31 tests.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_final_all -o cache_dir=pytest_temp_run_sprint7_final_all/.pytest_cache
passed, 171 tests.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check src/research tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py
passed.

UV_CACHE_DIR=.uv-cache uv run python -c "<execute code cells for notebooks/01_pair_selection.ipynb and notebooks/02_kalman_ou.ipynb>"
passed, both notebook code-cell checks ok.

Required coverage:
pair selection rejects insufficient data and low correlation;
pair selection ranks candidates by score;
ADF/KPSS wrappers return standardized results;
preliminary half-life is calculated;
Kalman recovers approximate beta on synthetic data;
Kalman spread_t length matches input;
Kalman flags unstable beta;
OU estimates positive theta on mean-reverting synthetic data;
OU rejects or warns theta <= 0;
rolling z-score avoids look-ahead;
rolling correlation avoids look-ahead;
execution-cost filters fail closed when quality/tail evidence is incomplete;
OU sigma scales correctly for non-unit dt;
functions do not rely on mutable global DataFrame state.
```

## Sprint 7 Historical Loader Checks

```text
Required commands:
pytest tests/test_historical_dataset.py
pytest tests/test_pair_selection.py

Result:
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_focus -o cache_dir=pytest_temp_run_task00709_focus/.pytest_cache
passed, 21 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_gate_focus -o cache_dir=pytest_temp_run_task00709_gate_focus/.pytest_cache
passed, 22 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_real_gate_all -o cache_dir=pytest_temp_run_sprint7_real_gate_all/.pytest_cache
passed, 182 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py
passed.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py scripts/run_sprint7_research_gate.py
passed.

Real smoke:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT --start-month 2023-06 --end-month-exclusive 2023-07 --dataset-version sprint7_real_smoke_202306_btcusdt --data-root /tmp/crypto_pair_trading_sprint7_real_smoke --correlation-window 2
passed.
Downloaded and checksumed the 5 required Binance Public Data families for
BTCUSDT 2023-06, wrote 720 normalized bars plus header to
/tmp/crypto_pair_trading_sprint7_real_smoke/normalized/sprint7_real_smoke_202306_btcusdt_bars.csv,
and accepted BTCUSDT in the one-symbol statistical smoke summary.

Full real dataset:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT AVAXUSDT LINKUSDT LTCUSDT BCHUSDT DOTUSDT TRXUSDT ETCUSDT UNIUSDT ATOMUSDT APTUSDT ARBUSDT OPUSDT SUIUSDT --start-month 2023-06 --end-month-exclusive 2026-06 --dataset-version sprint7_binance_usdm_202306_202605 --data-root data/research/binance_public --correlation-window 168 --download-workers 12
passed.
Downloaded and checksumed Binance Public Data archives, wrote 526080 normalized
bars plus header, accepted 20 symbols, produced 41 statistical candidate pairs,
and rejected 149 pairs by pair-selection filters.

Real statistical research gate:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_research_gate.py --bars-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv --summary-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json --output-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json --output-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv
passed.
Evaluated 41 candidate pairs; 41 statistical-only accepts; 0 statistical
rejects; cost_gated_pass=false because verified historical top-of-book/L2
execution-cost evidence is unavailable.

Required coverage:
deterministic Binance Public Data archive paths;
SHA256 checksum parsing and exact verification, including sha256sum binary marker;
checksum mismatch blocks normalization before CSV parsing;
headerless public-data ZIPs preserve the first data row;
kline, mark, index, premium, and funding normalization;
funding joined as-of without future events;
missing hourly gaps do not forward-fill returns;
normalized archive plan feeds select_pairs;
runner script executes local no-download smoke and writes normalized CSV/summary.

Limit:
real statistical gate is complete, but cost-gated Sprint 7 PASS is blocked by
missing verified historical execution-cost evidence and pending Market Data
Agent + QA Agent review.
```
