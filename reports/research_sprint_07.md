# Research Sprint 7 Report

Status: final report for Sprint 7 technical base. Sprint 7 technical
implementation is complete (PASSA). Sprint 8 advancement gate: PASSA, SCOPED
to 31 candidate pairs with genuine verified cost evidence for June 2023
(ADR-0007 in `project_control/DECISIONS.md`). Failed ADAUSDT pairs and all
other months remain statistical-only.

Last updated: 2026-07-02.

Gate conclusion for Sprint 8: PARTIALLY PASSA -- scoped to the pairs and
evidence window actually verified. Not a full-window or full-universe PASS.

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

TASK-007-10 first probed the real Binance Public Data bookTicker archive
(monthly and daily, both S3 prefixes) for all 20 accepted symbols across the
full 2023-06 through 2026-05 window. Result: `SOURCE_INCOMPLETE_FAIL_CLOSED`.
Verified top-of-book/L2 coverage exists for only 11 of the 36 required months
(2023-06 through approximately 2024-04), identically for every symbol;
Binance does not publish bookTicker archives past that point for any of them.
This was independently verified against the live S3 endpoint (not a
pagination artifact) and independently re-reviewed by QA Agent.

Rather than stop there, ADR-0007 scoped the cost-gated PASS requirement to
whatever evidence window is actually verified, and required daily (not
monthly) bookTicker ingestion after a monthly-archive download attempt caused
an out-of-memory kill in this environment. The first real pilot covered 6
non-BTC/ETH top candidate symbols for June 2023 and proved 5 of 6 pairs. On
2026-07-02 the same pilot was expanded to all 15 symbols that appear in the 41
Sprint 7 candidate pairs. Before processing BTCUSDT/ETHUSDT, the daily runner
was hardened to stream-read ZIP members with numeric dtypes; the real run then
processed 450 daily Binance bookTicker ZIPs + .CHECKSUM files (17.98GB
compressed) without OOM.

The expanded gate used 10800 deduplicated hourly cost rows for June 2023. It
produced `cost_gated_pass=true`: 31 of 41 candidate pairs passed with genuine
verified cost evidence. The 10 failures all contain ADAUSDT and were correctly
blocked because ADAUSDT fails the symbol-level spread gate
(`WIDE_MEDIAN_SPREAD`, median spread 3.52bps > 3.0bps). Sprint 8 may open
scoped to those 31 verified pairs. Failed ADAUSDT pairs and any month outside
June 2023 remain statistical-only, not cost-gated. Broader claims require
repeating this same real-download process for more months, an alternative
verified source for 2024-05 through 2026-05, or reliance on the already-built
live Market Data Plane (Sprint 5/6 `BookFeatures`) once paper/live trading
exists.

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

The "Cost gate" column above reflects the full 2023-06 through 2026-05 claim,
which remains `false` (source incomplete for that full window). A separate,
narrower, genuinely verified claim exists for June 2023 only -- see below.

### Scoped Cost-Gated Pilot (June 2023, ADR-0007)

Per ADR-0007, real memory-safe pilots downloaded and checksum-verified daily
Binance bookTicker data inside June 2023. The first pilot covered 6
non-BTC/ETH top candidate symbols and proved the path. The expanded pilot
covered every symbol appearing in the 41 Sprint 7 candidate pairs:

```text
ADAUSDT, ARBUSDT, ATOMUSDT, AVAXUSDT, BTCUSDT, DOGEUSDT, DOTUSDT, ETCUSDT,
ETHUSDT, LINKUSDT, LTCUSDT, OPUSDT, SOLUSDT, UNIUSDT, XRPUSDT
```

Expanded pilot counts:

```text
450 daily Binance bookTicker ZIPs + .CHECKSUM files present.
17.98GB compressed archive bytes.
10827 raw hourly rows.
27 duplicate symbol-hours / 54 duplicate rows at day boundaries.
10800 deduplicated hourly rows used by the gate.
10800 June-2023 1h bars for the 15 symbols.
```

Cost gate result for all 41 candidate pairs:

```text
cost_gated_pass=true
pairs_passed=31
pairs_failed=10
symbol_count=15
normalized_cost_rows=10800
source_review.complete_for_window=true
```

Passed pairs:

```text
ARBUSDT/OPUSDT
BTCUSDT/ETHUSDT
ARBUSDT/ETHUSDT
ARBUSDT/ETCUSDT
ETCUSDT/ETHUSDT
ARBUSDT/DOTUSDT
ETHUSDT/LINKUSDT
AVAXUSDT/DOTUSDT
DOTUSDT/ETCUSDT
ATOMUSDT/DOTUSDT
DOTUSDT/LINKUSDT
ARBUSDT/LINKUSDT
AVAXUSDT/LINKUSDT
ARBUSDT/AVAXUSDT
ETCUSDT/LINKUSDT
AVAXUSDT/SOLUSDT
ETCUSDT/OPUSDT
ETHUSDT/SOLUSDT
DOGEUSDT/ETCUSDT
AVAXUSDT/ETHUSDT
DOGEUSDT/ETHUSDT
AVAXUSDT/ETCUSDT
DOTUSDT/ETHUSDT
ARBUSDT/ATOMUSDT
DOTUSDT/OPUSDT
ETHUSDT/OPUSDT
ETCUSDT/LTCUSDT
ETHUSDT/UNIUSDT
DOGEUSDT/DOTUSDT
BTCUSDT/SOLUSDT
ATOMUSDT/ETCUSDT
```

Failed pairs:

```text
ADAUSDT/DOTUSDT
ADAUSDT/AVAXUSDT
ADAUSDT/ETCUSDT
ADAUSDT/LINKUSDT
ADAUSDT/DOGEUSDT
ADAUSDT/ETHUSDT
ADAUSDT/ARBUSDT
ADAUSDT/XRPUSDT
ADAUSDT/ATOMUSDT
ADAUSDT/SOLUSDT
```

All failures are expected and conservative: ADAUSDT fails the symbol-level
gate with `WIDE_MEDIAN_SPREAD` (median spread 3.52bps > 3.0bps). Pair-level
metrics are preserved in
`data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.csv`.

Initial pilot artifacts:

```text
data/research/binance_public/cost_pilot/pilot_202306_hourly_cost.csv
data/research/binance_public/cost_pilot/pilot_202306_bars.csv
data/research/binance_public/cost_pilot/pilot_202306_summary.json
data/research/binance_public/cost_pilot/pilot_202306_source_review.json
data/research/binance_public/cost_pilot/pilot_202306_execution_cost_gate.json
data/research/binance_public/cost_pilot/pilot_202306_execution_cost_gate.csv
```

Expanded artifacts:

```text
data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost_raw.csv
data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost.csv
data/research/binance_public/cost_pilot/all_candidates_202306_duplicate_hours.csv
data/research/binance_public/cost_pilot/all_candidates_202306_bars.csv
data/research/binance_public/cost_pilot/all_candidates_202306_summary.json
data/research/binance_public/cost_pilot/all_candidates_202306_archive_manifest.csv
data/research/binance_public/cost_pilot/all_candidates_202306_manifest.json
data/research/binance_public/cost_pilot/all_candidates_202306_source_review.json
data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.json
data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.csv
```

This is a genuine, checksum-verified result, not a fabricated or sampled-away
approximation. It is scoped strictly to June 2023 and must not be read as
validating the full 36-month window or months outside this evidence set.

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

Scoped cost-gated pilot (ADR-0007):
A first attempt to download one MONTH of bookTicker for one symbol (ETCUSDT)
was OOM-killed (exit 137). Rewrote to use DAILY bookTicker archives, verified
safe with one real symbol-day, then ran for real:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_execution_cost_download.py --symbols ARBUSDT OPUSDT ADAUSDT DOTUSDT ETCUSDT AVAXUSDT --start-month 2023-06 --end-month-exclusive 2023-07 --data-root data/research/binance_public/cost_pilot/raw --dataset-version sprint7_cost_pilot_202306 --output-hourly-csv data/research/binance_public/cost_pilot/pilot_202306_hourly_cost.csv
Result: passed. 180 symbol-days downloaded, checksum-verified, normalized,
and aggregated with no errors. 4326 hourly cost rows written.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_execution_cost_evidence.py --bars-csv data/research/binance_public/cost_pilot/pilot_202306_bars.csv --summary-json data/research/binance_public/cost_pilot/pilot_202306_summary.json --cost-hourly-csv data/research/binance_public/cost_pilot/pilot_202306_hourly_cost.csv --probe-binance-source --start-month 2023-06 --end-month-exclusive 2023-07 --output-json data/research/binance_public/cost_pilot/pilot_202306_execution_cost_gate.json --output-csv data/research/binance_public/cost_pilot/pilot_202306_execution_cost_gate.csv
Result: passed. cost_gated_pass=true; 5 of 6 pairs pass; ADAUSDT/DOTUSDT
correctly rejected.

Expanded all-candidate June-2023 cost gate:
The runner was first hardened to stream-read daily ZIP members instead of
loading the whole decompressed member into bytes. Then the 9 missing symbols
for the 41-candidate universe were downloaded and verified:
ATOMUSDT, BTCUSDT, DOGEUSDT, ETHUSDT, LINKUSDT, LTCUSDT, SOLUSDT, UNIUSDT,
XRPUSDT. This completed all 15 symbols used by the 41 candidate pairs.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_execution_cost_download.py --symbols ATOMUSDT BTCUSDT DOGEUSDT ETHUSDT LINKUSDT LTCUSDT SOLUSDT UNIUSDT XRPUSDT --start-month 2023-06 --end-month-exclusive 2023-07 --data-root data/research/binance_public/cost_pilot/raw --dataset-version sprint7_cost_all_candidates_202306 --output-hourly-csv data/research/binance_public/cost_pilot/missing_candidates_202306_hourly_cost.csv --timeout-seconds 120
Result: passed. 270 additional symbol-days downloaded, checksum-verified,
normalized, and aggregated with no OOM. BTCUSDT and ETHUSDT large days passed
(BTCUSDT 2023-06-14: 28,328,075 raw rows; ETHUSDT 2023-06-14: 22,467,809 raw
rows).

Generated all-candidate artifacts:
Result: 450 daily archives present, 17.98GB compressed, 10827 raw hourly rows,
27 duplicate symbol-hours isolated, 10800 deduplicated hourly rows, 10800 bars.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_execution_cost_evidence.py --bars-csv data/research/binance_public/cost_pilot/all_candidates_202306_bars.csv --summary-json data/research/binance_public/cost_pilot/all_candidates_202306_summary.json --cost-hourly-csv data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost.csv --source-review-json data/research/binance_public/cost_pilot/all_candidates_202306_source_review.json --output-json data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.json --output-csv data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.csv
Result: passed. cost_gated_pass=true; 31 of 41 pairs pass; 10 ADAUSDT pairs
correctly rejected.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 190 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research scripts tests
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_sprint8_gate_expand -o cache_dir=pytest_temp_sprint8_gate_expand/.pytest_cache
Result: passed, 190 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src tests scripts
Result: passed.

git diff --check
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
QA Agent independently re-reviewed TASK-007-10 source-incomplete finding (S3
pagination risk, no-default-approve on missing evidence): PASSA, confirmed
PM's finding, 1 P2 finding (add pagination handling as future hardening).
Market Data Agent reviewed the new daily bookTicker download code and the
additive BOOK_TICKER enum change: PASSA, 1 P3 finding (non-blocking:
normalize_symbol_archive_files has no explicit guard against BOOK_TICKER
misuse via the kline-oriented path, not exercised by the code actually used).
QA Agent forensically re-verified the scoped pilot result: recomputed
statistics from the raw CSV, hand-verified SHA256 checksums of downloaded
archives against Binance's .CHECKSUM files, unzipped and inspected real tick
prices, checked git history for threshold tampering (none found), and
confirmed the source-review probe is genuinely scope-sensitive (returns false
for the full 36-month window, true for the scoped 1-month pilot). Verdict:
PASSA, result is genuine; found one non-blocking data-quality note (12 of
4326 rows are duplicate hours at day-boundary stitching, not materially
affecting reported medians).
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
- Genuine cost-gated PASS for 31 candidate pairs rests on a single verified
  month (June 2023), not a multi-year sample; spread regimes can differ
  across market conditions not covered by this pilot.
- Daily bookTicker archive stitching produces a small number of duplicate
  hourly rows at day boundaries (27 duplicate symbol-hours / 54 duplicate
  rows out of 10827 raw hourly rows in the expanded pilot); the gate uses the
  explicit deduplicated 10800-row hourly-cost file and preserves duplicates
  for audit.
- A monthly bookTicker download for a single mid-cap symbol caused an
  out-of-memory kill in this environment; any future extension of this pilot
  must keep using the daily, one-symbol-day-at-a-time ingestion path from
  ADR-0007, never a whole-month load.

## Conclusion

Technical implementation: PASSA for the Sprint 7 statistical research base,
historical loader path, and execution-cost evidence pipeline. TASK-007-09 and
TASK-007-10 both passed Market Data Agent + QA Agent review and are DONE.

Sprint 8 advancement gate: PARTIALLY PASSA, per ADR-0007. Binance Public Data
does not publish verified top-of-book/L2 (bookTicker) archives past
approximately 2024-04 for any of the 20 Sprint 7 symbols, so the full 2023-06
through 2026-05 window cannot be cost-gated from this source -- that finding
still stands. But rather than leaving the gate as a binary block, a real,
checksum-verified pilot produced genuine cost-gated evidence for a bounded
scope: 31 of 41 candidate pairs pass with real spread evidence for June 2023.
The 10 failed pairs all contain ADAUSDT and remain blocked by ADAUSDT
`WIDE_MEDIAN_SPREAD` (3.52bps > 3.0bps).

Sprint 8 may open, SCOPED to those 31 pairs and explicitly labeled as backed
by one verified month, not a multi-year backtest validation. Failed ADAUSDT
pairs and any month outside this pilot remain statistical-only and blocked
from cost-gated claims. Extending coverage further requires one of:

1. Repeating this same real-download-and-verify process (daily bookTicker,
   memory-bounded) for more of the verified ~11-month sub-period and/or the
   additional months inside the verified ~11-month sub-period.
2. Locating and verifying an alternative top-of-book/L2 source (for example a
   paid tick-data vendor) for the 2024-05 through 2026-05 gap, which has no
   bookTicker coverage on Binance Public Data at all.
3. Relying on the already-built live Market Data Plane (Sprint 5/6
   `BookFeatures`, `spread_bps`, `depth_5bps`/`depth_10bps`) as the source of
   forward execution-cost evidence once paper/live trading exists, per
   ADR-0007.

Do not present any pair or window outside the 31 passed pairs and verified
June-2023 window as cost-gated. Opening and scoping Sprint 8 itself (its
objective, deliverables, and task breakdown) is separate planning work, not
yet done, and should be confirmed with the user before proceeding.
