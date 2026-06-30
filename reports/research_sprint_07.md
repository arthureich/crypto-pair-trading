# Research Sprint 7 Report

Status: final report for Sprint 7 technical base.

Last updated: 2026-06-30.

Gate conclusion for Sprint 8: NAO PASSA.

## Executive Summary

Sprint 7 delivered the research base for pair selection, stationarity checks,
Kalman dynamic hedge ratio, OU estimation, half-life, and z-score. The modules
are implemented, reviewed, and covered by automated tests.

The Sprint 8 advancement gate does not pass yet because no real 36 complete
month Binance USD-M historical dataset was downloaded, checksumed, normalized,
or run through the research pipeline. The notebooks include deterministic
synthetic smoke examples only. They prove the workflow shape, not market edge.

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
| 2023-06 through 2026-05 historical dataset | 0 | not evaluated | DATASET_NOT_RUN |

All real-market pair decisions are deferred and treated as not approved for the
Sprint 8 gate because the required dataset has not been run. No pair should be
advanced to backtest or Sprint 8 from synthetic notebook evidence.

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
| 2023-06 through 2026-05 historical dataset | not evaluated | not evaluated | DATASET_NOT_RUN |

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
```

Reviews:

```text
Market Data Agent passed TASK-007-01 after dataset contract corrections.
Backtest Agent re-review passed TASK-007-02/TASK-007-04/TASK-007-05 after no-look-ahead and cost-evidence fixes.
QA Agent re-review passed TASK-007-03/TASK-007-04/TASK-007-05 after OU sigma dt fix.
```

## Risks

- Synthetic examples can make the pipeline look more mature than the market
  evidence. They are smoke tests only.
- The seed universe is biased toward symbols known to be liquid on 2026-06-30;
  walk-forward evaluation must freeze universe formation inside each window.
- Full-sample diagnostics are exploratory and must not be used as online signal
  truth.
- Funding and execution costs can dominate statistical mean reversion.
- Verified historical execution-spread evidence is still conditional; without it,
  cost-gated PASS must fail closed.
- Kalman/OU parameters can be unstable under regime shifts or poorly chosen
  noise assumptions.

## Conclusion

Technical implementation: PASSA.

Sprint 8 advancement gate: NAO PASSA.

Required next step: run the documented 36 complete-month historical dataset
through the research pipeline, produce real approved/rejected pair tables, and
only then repeat the Sprint 7 gate decision. Do not start Sprint 8 from the
synthetic notebook examples.
