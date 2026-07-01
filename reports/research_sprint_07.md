# Research Sprint 7 Report

Status: final report for Sprint 7 technical base. Sprint 7 technical
implementation is complete (PASSA). Sprint 8 advancement gate: NAO PASSA,
definitively, pending a PM/stakeholder policy decision (see Conclusion).

Last updated: 2026-07-01.

Gate conclusion for Sprint 8: NAO PASSA (definitive data-availability finding,
not a pending-execution gap).

## Executive Summary

Sprint 7 delivered the research base for pair selection, stationarity checks,
Kalman dynamic hedge ratio, OU estimation, half-life, and z-score. The modules
are implemented, reviewed, and covered by automated tests.

TASK-007-09 added the historical loader/normalizer path and executed the real
36 complete-month Binance USD-M dataset for 20 seed symbols. The run produced
526080 normalized 1h bars, 41 statistical candidate pairs, and 149 rejected
pairs. The follow-up research gate evaluated all 41 candidates with
stationarity, Kalman, OU, and rolling z-score diagnostics. TASK-007-09 passed
Market Data Agent and QA Agent review with no blocking findings and is DONE.

TASK-007-10 probed the real Binance Public Data bookTicker archive (monthly
and daily, both S3 prefixes) for all 20 accepted symbols across the full
2023-06 through 2026-05 window. The result is definitive:
`SOURCE_INCOMPLETE_FAIL_CLOSED`. Verified top-of-book/L2 coverage exists for
only 11 of the 36 required months (2023-06 through approximately 2024-04),
identically for every symbol; Binance does not publish bookTicker archives
past that point for any of them. This was independently verified against the
live S3 endpoint (not a pagination artifact) and independently re-reviewed by
QA Agent. `cost_gated_pass=false` for all 41 candidate pairs, unconditionally.
TASK-007-10 is DONE with this negative finding.

All 41 candidates remain statistical-only accepts, not cost-gated approvals.
This is no longer a pending-evidence gap: verified historical top-of-book/L2
execution-cost evidence does not exist on this source for this window. No
pair should advance to Sprint 8 as executable until the PM/stakeholder chooses
and executes one of the paths in the Conclusion section below.

## Dataset Contract

The minimum dataset is defined in `docs/historical_dataset.md`.

| Item | Definition |
|---|---|
| Venue | Binance USD-M Futures |
| Source | Binance Public Data archive at `https://data.binance.vision/` |
| Period | `2023-06-01T00:00:00Z <= open_time < 2026-06-01T00:00:00Z` |
| Complete months | 36, from 2023-06 through 2026-05 |
| Canonical frequency | `1h` UTC bars |
| Research price | `mark_close` preferred, traded `close` only as flagged fallback |
| Required sidecars | index price, premium index, and funding history |
| Conditional sidecar | verified historical top-of-book/L2 spread evidence |
| Checksums | required for every public archive zip |

Initial seed universe:

```text
BTCUSDT
ETHUSDT
BNBUSDT
SOLUSDT
XRPUSDT
ADAUSDT
DOGEUSDT
AVAXUSDT
LINKUSDT
LTCUSDT
BCHUSDT
DOTUSDT
TRXUSDT
ETCUSDT
UNIUSDT
ATOMUSDT
APTUSDT
ARBUSDT
OPUSDT
SUIUSDT
```

## Cleaning Summary

The canonical cleaning rules are defined in `docs/historical_dataset.md`.
Sprint 7 requires complete closed 1h bars keyed by `(symbol, open_time)` with UTC
millisecond timestamps. Raw archives must be preserved separately from
normalized data, and every archive zip must have a verified checksum before its
normalized rows are trusted.

Normalization rejects non-positive prices, negative volumes, negative trade
counts, non-finite numeric values, invalid OHLC rows, and disagreeing duplicate
bars. Exact duplicate rows may be deduplicated only when every field matches; if
duplicates disagree, the affected symbol/month is rejected until checksum and
archive version are manually reviewed.

Missing data must fail closed for research inputs. The pipeline builds an
expected 1h grid per symbol, rejects symbols with more than 1.0% missing bars or
any contiguous gap longer than 6 hours, rejects pairs with less than 99.0% joint
valid-bar coverage, and never forward-fills prices, returns, execution spreads,
or volume for stationarity, Kalman, OU, or z-score inputs.

Funding is joined using as-of semantics with `funding_time <= bar_close_time`; a
future funding event must never be attached to an earlier bar. `mark_close` is
the default statistical price, while traded `close` is allowed only as a flagged
fallback or robustness view. Optional execution-spread samples with invalid
bid/ask values are excluded from aggregates, and incomplete cost evidence cannot
satisfy a cost-gated PASS.

## Filters

Minimum symbol filters:

| Area | Threshold |
|---|---|
| History | `>= 26,000` valid 1h bars and `>= 99.0%` coverage |
| Gaps | no contiguous missing gap longer than `6h` |
| Liquidity | median quote volume `>= 1,000,000 USDT` per hour |
| Tail liquidity | p10 quote volume `>= 100,000 USDT` per hour |
| Trade count | median trades `>= 100` per hour |
| Spread | conditional: median `<= 3 bps`, p95 `<= 8 bps`, p99 `<= 15 bps` only with verified execution-cost evidence |
| Funding | median absolute funding `<= 3 bps`, p95 absolute `<= 15 bps` |

Minimum pair pre-filters:

| Area | Threshold |
|---|---|
| Joint history | `>= 99.0%` valid 1h bars |
| Combined median spread | conditional `<= 6 bps` if verified |
| Combined p95 spread | conditional `<= 10 bps` if verified |
| Conservative absolute funding carry | `<= 10 bps/day` |
| Rolling correlation | default minimum `>= 0.75`, shifted to avoid current-row look-ahead |

Execution-cost filters are conditional and fail closed for cost-gated claims.
If verified top-of-book/L2 evidence is incomplete or unavailable, the report may
show exploratory statistical candidates, but it cannot claim cost-gated PASS.

## Research Modules

Implemented source modules:

| Module | Purpose | Gate notes |
|---|---|---|
| `src/research/pair_selection.py` | Symbol filters, pair filters, deterministic ranking, rolling no-look-ahead correlation | Cost evidence fails closed when incomplete; p95/p99 spread require real tail or raw spread data |
| `src/research/stationarity.py` | ADF/KPSS wrappers, half-life, rolling correlation, spread stability, combined decisions | Rolling correlation is shifted one row; full-sample diagnostics are marked exploratory |
| `src/research/kalman.py` | Sequential beta_t, alpha_t, spread_t, innovation, covariance, instability flags | No backtest/live scope; arrays match input length |
| `src/research/ou.py` | OU theta/mu/sigma/half-life, rolling z-score, full-sample z-score | Sigma handles non-unit `dt`; rolling z-score is shifted one row |

## Notebooks

Created notebooks:

| Notebook | Purpose | Data used |
|---|---|---|
| `notebooks/01_pair_selection.ipynb` | Demonstrates pair selection tables and rejection reasons | deterministic synthetic normalized bars |
| `notebooks/02_kalman_ou.ipynb` | Demonstrates Kalman beta/alpha/spread plus OU and z-score diagnostics | deterministic synthetic pair and OU spread |

Both notebooks execute their code cells successfully in the current environment.
They intentionally save no outputs and do not replace automated tests.

## Candidate Results

Real Binance USD-M research result:

| Scope | Approved pairs | Rejected pairs | Status |
|---|---:|---:|---|
| 2023-06 through 2026-05 historical dataset | 41 statistical-only, 0 cost-gated | 149 pair-selection rejects | COST_GATED_PASS_FALSE |

Dataset artifacts:

```text
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv
```

The 41 accepted pairs are statistical-only candidates. `cost_gated_pass=false`
for every pair, definitively: TASK-007-10 probed the real Binance Public Data
bookTicker source (monthly and daily archives) for all 20 accepted symbols
across the full window and found verified top-of-book/L2 coverage for only 11
of the 36 required months (2023-06 through approximately 2024-04), identically
for every symbol. Binance does not publish bookTicker archives past that point
for any of them. This is a real source limitation, independently verified
against the live S3 endpoint and re-verified by QA Agent — not a pending
check and not a code defect.

```text
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_execution_cost_source_review.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_execution_cost_gate.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_execution_cost_gate.csv
```

Top statistical candidates from the real run:

| Pair | Corr | Funding bps/day | OU half-life h | Latest z | Stationarity | Cost gate |
|---|---:|---:|---:|---:|---|---|
| `ARBUSDT/OPUSDT` | 0.843935 | 6.0000 | 1.9887 | 0.7693 | WARN | false |
| `BTCUSDT/ETHUSDT` | 0.829052 | 4.0707 | 0.8227 | -1.0531 | WARN | false |
| `ARBUSDT/ETHUSDT` | 0.815144 | 5.0808 | 0.8472 | 1.4426 | WARN | false |
| `ADAUSDT/DOTUSDT` | 0.812082 | 6.0000 | 1.8837 | -0.3626 | WARN | false |
| `ARBUSDT/ETCUSDT` | 0.811014 | 6.0000 | 1.5255 | 1.2917 | WARN | false |
| `ETCUSDT/ETHUSDT` | 0.806539 | 5.0808 | 0.7356 | 1.0044 | WARN | false |
| `ARBUSDT/DOTUSDT` | 0.795231 | 6.0000 | 1.9232 | 0.9324 | WARN | false |
| `ETHUSDT/LINKUSDT` | 0.794781 | 5.0808 | 1.7305 | -1.2722 | WARN | false |
| `AVAXUSDT/DOTUSDT` | 0.791653 | 6.0000 | 1.7933 | 0.4127 | WARN | false |
| `DOTUSDT/ETCUSDT` | 0.791625 | 6.0000 | 1.5057 | 0.8822 | WARN | false |

Synthetic pair-selection smoke example:

| Pair / symbol | Status | Metrics / reasons |
|---|---|---|
| `BTCUSDT/ETHUSDT` | synthetic candidate | rolling correlation score `0.998467` |
| `BTCUSDT/SOLUSDT` | synthetic rejected pair | `LOW_CORRELATION` |
| `ETHUSDT/SOLUSDT` | synthetic rejected pair | `LOW_CORRELATION` |
| `WEAKUSDT` | synthetic rejected symbol | `LOW_MEDIAN_VOLUME`, `LOW_TAIL_VOLUME`, `VOLUME_GAPS`, `LOW_TRADE_COUNT`, `HIGH_MEDIAN_FUNDING` |

These rows are smoke-test examples only.

## Kalman And OU Results

Real market Kalman/OU result:

| Scope | beta_t / spread_t | OU result | Status |
|---|---|---|---|
| 2023-06 through 2026-05 historical dataset | 41 evaluated, 0 beta-unstable flags | 41 mean-reverting OU fits, half-life range 0.7356h to 2.2430h | STATISTICAL_ONLY |

Stationarity was `WARN` for all 41 accepted statistical candidates, mostly
because historical z-score outliers exceeded the stability threshold. These
warnings do not reject the pairs statistically, but they reinforce that the
result is exploratory and not an execution-ready approval.

Synthetic Kalman/OU smoke example from `notebooks/02_kalman_ou.ipynb`:

| Metric | Value |
|---|---:|
| stationarity status | `ACCEPT` |
| ADF p-value | `0.000978` |
| KPSS p-value | `0.100000` |
| preliminary half-life | `4.354773` |
| OU status | `MEAN_REVERTING` |
| OU theta | `0.173365` |
| OU mu | `-0.090181` |
| OU sigma | `0.188887` |
| OU half-life | `3.998190` |
| latest rolling z-score | `1.409530` |
| z-score look-ahead safe | `True` |
| Kalman beta unstable | `False` |

## Verification

Automated checks:

```text
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py --basetemp=pytest_temp_run_sprint7_final_core -o cache_dir=pytest_temp_run_sprint7_final_core/.pytest_cache
Result: passed, 31 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_final_all -o cache_dir=pytest_temp_run_sprint7_final_all/.pytest_cache
Result: passed, 171 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check src/research tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py
Result: passed.

Notebook code-cell execution check:
notebooks/01_pair_selection.ipynb: code cells ok.
notebooks/02_kalman_ou.ipynb: code cells ok.

TASK-007-09 loader checks:
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_focus -o cache_dir=pytest_temp_run_task00709_focus/.pytest_cache
Result: passed, 21 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_gate_focus -o cache_dir=pytest_temp_run_task00709_gate_focus/.pytest_cache
Result: passed, 22 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_real_gate_all -o cache_dir=pytest_temp_run_sprint7_real_gate_all/.pytest_cache
Result: passed, 182 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py scripts/run_sprint7_research_gate.py
Result: passed.

Real loader smoke:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT --start-month 2023-06 --end-month-exclusive 2023-07 --dataset-version sprint7_real_smoke_202306_btcusdt --data-root /tmp/crypto_pair_trading_sprint7_real_smoke --correlation-window 2
Result: passed. BTCUSDT 2023-06 downloaded, checksumed, normalized, and accepted
as a one-symbol statistical smoke. No candidate pairs are possible with one
symbol.

Full real dataset:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT AVAXUSDT LINKUSDT LTCUSDT BCHUSDT DOTUSDT TRXUSDT ETCUSDT UNIUSDT ATOMUSDT APTUSDT ARBUSDT OPUSDT SUIUSDT --start-month 2023-06 --end-month-exclusive 2026-06 --dataset-version sprint7_binance_usdm_202306_202605 --data-root data/research/binance_public --correlation-window 168 --download-workers 12
Result: passed. Output contains 526080 normalized bars, 20 accepted symbols,
41 statistical candidate pairs, and 149 rejected pairs.

Real statistical research gate:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_research_gate.py --bars-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv --summary-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json --output-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json --output-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv
Result: passed. Evaluated 41 candidate pairs; 41 statistical-only accepts;
0 statistical rejects; cost_gated_pass=false.

Real execution-cost evidence source review and gate (TASK-007-10):
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_execution_cost_evidence.py -q
Result: passed, 4 tests.
Live probe against s3-ap-northeast-1.amazonaws.com/data.binance.vision bookTicker
monthly and daily prefixes for all 20 accepted symbols, full 2023-06 through
2026-05 window.
Result: SOURCE_INCOMPLETE_FAIL_CLOSED. Verified coverage 11 of 36 months
(30.56%) identically for all 20 symbols; cost_gated_pass=false for all 41
candidate pairs.
PM independently re-queried the live S3 endpoint directly via curl for
BTCUSDT: monthly prefix KeyCount=24 MaxKeys=1000 IsTruncated=false (last
archive 2024-04); daily prefix KeyCount=640 MaxKeys=1000 IsTruncated=false
(last archive 2024-03-30). Confirms the coverage gap is real, not a
pagination artifact.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 186 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/execution_cost_evidence.py tests/test_execution_cost_evidence.py scripts/run_sprint7_execution_cost_evidence.py
Result: passed.
```

Reviews:

```text
Market Data Agent passed TASK-007-01 after dataset contract corrections.
Backtest Agent re-review passed TASK-007-02/TASK-007-04/TASK-007-05 after no-look-ahead and cost-evidence fixes.
QA Agent re-review passed TASK-007-03/TASK-007-04/TASK-007-05 after OU sigma dt fix.
Market Data Agent reviewed TASK-007-09: PASSA, 2 P3 findings (non-blocking).
QA Agent reviewed TASK-007-09 fail-closed behavior: PASSA, 2 P2 + 1 P3
findings (non-blocking, no P1).
QA Agent independently re-reviewed TASK-007-10 (S3 pagination risk,
no-default-approve on missing evidence): PASSA, confirmed PM's finding,
1 P2 finding (add pagination handling as future hardening).
```

## Risks

- Synthetic examples can make the pipeline look more mature than the market
  evidence. They are smoke tests only.
- The seed universe is biased toward symbols known to be liquid on 2026-06-30;
  walk-forward evaluation must freeze universe formation inside each window.
- Full-sample diagnostics are exploratory and must not be used as online signal
  truth.
- Funding and execution costs can dominate statistical mean reversion.
- Verified historical execution-spread evidence does not exist for the full
  Sprint 7 window on Binance Public Data (only 11 of 36 months); cost-gated
  PASS fails closed permanently for this source and window, not conditionally.
- Kalman/OU parameters can be unstable under regime shifts or poorly chosen
  noise assumptions.
- `_fetch_s3_objects`/`parse_s3_list_objects` do not handle S3 pagination;
  harmless for the current probe (KeyCount well below MaxKeys=1000) but
  should be hardened before relying on this probe at larger scale.
- `download_archives`/`_download_archive` (the real-network download path in
  `historical_dataset.py`) has no test coverage, mocked or otherwise; safe for
  offline CI but its error handling is unverified.

## Conclusion

Technical implementation: PASSA for the Sprint 7 statistical research base,
historical loader path, and execution-cost evidence probe. TASK-007-09 and
TASK-007-10 both passed Market Data Agent + QA Agent review and are DONE.

Sprint 8 advancement gate: NAO PASSA, definitively. This is a data-availability
finding, not a pending-execution gap: Binance Public Data does not publish
verified top-of-book/L2 (bookTicker) archives past approximately 2024-04 for
any of the 20 Sprint 7 symbols, so complete coverage of the required 2023-06
through 2026-05 window cannot be produced from this source.

Required next step: a PM/stakeholder decision among the following paths, each
requiring an ADR entry in `DECISIONS.md` before Sprint 8 opens:

1. Locate and verify an alternative top-of-book/L2 source (for example a paid
   tick-data vendor) with full coverage of the 2023-06 through 2026-05 window,
   then rerun the cost gate.
2. Shrink the Sprint 7 research window to the verified ~11-month sub-period
   (2023-06 through approximately 2024-04) and rerun the full statistical and
   cost gate on that sub-window only.
3. Redefine cost-gated PASS policy (for example: require verified
   execution-cost evidence collected forward from live market data instead of
   retroactive historical top-of-book coverage for the full backtest window).
4. Keep Sprint 8 blocked indefinitely until (1) or (3) is resolved.

Do not start Sprint 8 from statistical-only candidates.
