# Historical Dataset Minimum - Sprint 7

Status: defined for TASK-007-01.

Owner: Quant Research Agent.

Reviewer: Market Data Agent.

Last updated: 2026-06-30.

## Purpose

This document defines the minimum historical dataset for Sprint 7 pair
selection, stationarity checks, Kalman beta/alpha/spread, and OU estimation.
It is a research-data contract only. It does not download data, implement an
exchange client, define a backtest, or permit paper/live trading.

## Scope

The dataset covers single-venue crypto USD-M futures research on Binance. It
must contain closed historical bars, mark price bars, index/premium sidecars,
and funding history. Historical executable-spread evidence is required only
when a complete and checksumed source exists for the full analysis window; if it
is unavailable, cost-gated promotion must fail closed and the report must label
the candidate set as statistical-only.

The dataset must not be used as live truth. Signal, Execution, Ledger, and
Recovery boundaries remain governed by `docs/architecture.md`,
`project_control/INTERFACES.md`, and `docs/risk_limits.md`.

## Recommended Source

Primary source:

- Binance Public Data archive: `https://data.binance.vision/`
- Public data documentation repository:
  `https://github.com/binance/binance-public-data`

Required archive families:

| Data type | Binance public data path pattern | Minimum use |
|---|---|---|
| OHLCV futures klines | `data/futures/um/monthly/klines/{SYMBOL}/1h/` | canonical hourly traded-price bars |
| Mark price klines | `data/futures/um/monthly/markPriceKlines/{SYMBOL}/1h/` | canonical hourly research price when present |
| Index price klines | `data/futures/um/monthly/indexPriceKlines/{SYMBOL}/1h/` | index-price reference sidecar |
| Premium index klines | `data/futures/um/monthly/premiumIndexKlines/{SYMBOL}/1h/` | premium/reference dislocation sidecar |
| Funding rates | `data/futures/um/monthly/fundingRate/{SYMBOL}/` | event-time funding sidecar |

Optional execution-cost evidence:

| Data type | Requirement | Minimum use |
|---|---|---|
| Historical top-of-book or L2 spread | Must have complete coverage, immutable source paths, timestamps, and checksums/provenance for the full analysis window | bid/ask cost screen before any cost-gated Sprint 7 PASS |

Binance Public Data does not provide a verified complete `bookTicker` archive
for the full Sprint 7 window. Therefore `bookTicker` must not be treated as a
required public-archive family for this sprint. If a future task supplies a
complete historical `bookTicker`/L2 source, it must record the exact source
paths and checksums before spread thresholds can be enforced.

Fallback source for gaps, not a client implementation in this task:

- USD-M futures kline market data endpoint:
  `https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data`
- USD-M futures mark price kline endpoint:
  `https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price-Kline-Candlestick-Data`
- USD-M futures funding history endpoint:
  `https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History`

Every archive zip must have its `.CHECKSUM` verified before normalized data is
trusted. If archive files are later replaced by Binance, the dataset version
must record the old and new checksum and the affected symbols/months.

## Initial Symbol Universe

Seed universe for the first Sprint 7 research pass:

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

Universe rules:

- Include USD-M USDT perpetual futures only.
- Exclude COIN-M futures, delivery/quarterly contracts, spot symbols,
  leveraged tokens, options, and multi-exchange synthetic symbols.
- Confirm each symbol exists for the target window before research uses it.
- Treat the seed list as candidates only; symbols failing history, liquidity,
  spread, or funding filters are rejected before pair generation.
- If a future run selects symbols dynamically by volume or market cap, that
  selection must be frozen using only data available before the evaluation
  window starts.

## Minimum Period

Fixed Sprint 7 minimum window:

```text
start_time_utc = 2023-06-01T00:00:00Z
end_time_utc_exclusive = 2026-06-01T00:00:00Z
complete_months = 36
last_complete_month = 2026-05
expected_1h_bars_per_symbol = 26,304
```

For future reruns, use the latest 36 complete UTC calendar months, excluding
the current incomplete UTC month and excluding any month whose public archive
checksum is missing.

Optional holdout:

```text
holdout_start_utc = 2026-06-01T00:00:00Z
holdout_end_utc_exclusive = 2026-06-30T00:00:00Z
```

The June 2026 holdout may be used only when complete daily archives and
checksums exist for every required family. It is not part of the minimum
dataset contract and cannot be counted toward the 36 complete-month history
gate.

Minimum history gate per symbol:

- At least 36 complete months targeted for the canonical dataset.
- At least 26,000 valid 1h bars inside the Sprint 7 window.
- At least 99.0% of expected 1h bars present after cleaning.
- No single missing-data gap longer than 6 hours.
- Mark, index, and premium kline sidecars must each cover at least 99.0% of the
  symbol's eligible hourly bars.
- Funding sidecars must cover at least 99.0% of expected funding events.
- Historical executable-spread coverage is optional for statistical research,
  but mandatory for a cost-gated Sprint 7 PASS.

## Frequency

Canonical research frequency:

- `1h` UTC bars keyed by `open_time`.
- Pair selection, stationarity, Kalman, OU, half-life, and z-score use this
  `1h` grid unless a later task explicitly adds a separate robustness view.

Sidecar frequencies:

- Funding is event-time data keyed by `funding_time`; it is joined to hourly
  bars using as-of rules.
- Mark, index, and premium sidecars use the same `1h` UTC bar grid.
- Optional historical top-of-book or L2 evidence is sampled or aggregated into
  hourly fields such as median and p95 spread only after coverage/provenance is
  verified.

Optional robustness frequencies:

- `5m` bars may be added later for sensitivity analysis only.
- Daily bars may be used in reports only; they are not the canonical Sprint 7
  model input.

## Required Fields

Required identity and provenance fields:

| Field | Meaning |
|---|---|
| `venue` | `BINANCE` |
| `market_type` | `USD_M_FUTURES` |
| `contract_type` | `PERPETUAL` |
| `symbol` | Exchange symbol, for example `BTCUSDT` |
| `base_asset` | Base asset parsed from exchange metadata |
| `quote_asset` | `USDT` |
| `interval` | Canonical value `1h` |
| `open_time` | Bar open timestamp in UTC milliseconds |
| `close_time` | Bar close timestamp in UTC milliseconds |
| `source_path` | Public archive object path or documented fallback source |
| `source_checksum` | Verified checksum for archive files |
| `dataset_version` | Immutable local dataset version identifier |
| `normalized_at` | UTC timestamp when normalization was produced |

Required OHLCV fields:

| Field | Meaning |
|---|---|
| `open` | Traded-price open |
| `high` | Traded-price high |
| `low` | Traded-price low |
| `close` | Traded-price close |
| `volume_base` | Base asset volume |
| `quote_volume` | Quote asset volume |
| `number_of_trades` | Exchange-reported trade count |
| `taker_buy_base_volume` | Taker buy base volume |
| `taker_buy_quote_volume` | Taker buy quote volume |

Required mark price fields:

| Field | Meaning |
|---|---|
| `mark_open` | Mark price open |
| `mark_high` | Mark price high |
| `mark_low` | Mark price low |
| `mark_close` | Mark price close |
| `price_for_research` | `mark_close` when present, otherwise `close` with a quality flag |

Required index/premium fields:

| Field | Meaning |
|---|---|
| `index_open` | Index price open |
| `index_high` | Index price high |
| `index_low` | Index price low |
| `index_close` | Index price close |
| `premium_open` | Premium index open |
| `premium_high` | Premium index high |
| `premium_low` | Premium index low |
| `premium_close` | Premium index close |

Required funding fields:

| Field | Meaning |
|---|---|
| `funding_time` | Native funding event timestamp |
| `funding_rate` | Funding rate at `funding_time` |
| `funding_mark_price` | Mark price attached to the funding event, if present |
| `funding_rate_asof` | Most recent funding rate with `funding_time <= bar_close_time` |

Optional execution-cost fields:

| Field | Meaning |
|---|---|
| `best_bid` | Top bid from verified historical top-of-book/L2 source |
| `best_ask` | Top ask from verified historical top-of-book/L2 source |
| `mid_price` | `(best_bid + best_ask) / 2` |
| `spread_bps` | `(best_ask - best_bid) / mid_price * 10000` |
| `spread_sample_count_1h` | Count of valid spread samples in the hour |
| `median_spread_bps_1h` | Median hourly spread |
| `p95_spread_bps_1h` | p95 hourly spread |
| `p99_spread_bps_1h` | p99 hourly spread |
| `execution_cost_quality` | `VERIFIED`, `UNAVAILABLE`, or `INCOMPLETE` |

Required derived research fields:

| Field | Meaning |
|---|---|
| `log_price` | Natural log of `price_for_research` |
| `return_1h` | `log_price_t - log_price_t_minus_1` |
| `is_complete_bar` | True only for closed, valid 1h bars |
| `quality_flags` | Set of cleaning/provenance warnings |

## Cleaning Rules

Timestamp rules:

- Treat all exchange timestamps as UTC.
- Store timestamps as integer milliseconds and expose UTC datetimes only as a
  derived presentation field.
- The canonical index is `(symbol, open_time)`.
- Keep only complete bars with `close_time > open_time`.

Schema and type rules:

- Parse numeric fields as exact decimal strings first, then convert to numeric
  research arrays after validation.
- Reject rows with non-positive prices, negative volumes, negative trade
  counts, or non-finite numeric values.
- Reject rows where `high < max(open, close)`, `low > min(open, close)`, or
  `high < low`.
- Preserve raw archives separately from normalized data.

Duplicate and ordering rules:

- Sort by `(symbol, open_time)`.
- Dedupe exact duplicate bars only when every field matches.
- If duplicate bars disagree, reject the affected symbol/month until the source
  checksum and archive version are manually reviewed.

Gap rules:

- Build an expected 1h grid for every symbol from the first valid bar in the
  target window.
- Do not forward-fill prices, returns, execution spreads, or volume for stationarity,
  Kalman, OU, or z-score inputs.
- Pair-level calculations may use only timestamps where both legs have valid,
  real bars.
- Reject a symbol when missing bars exceed 1.0% of expected bars or any
  contiguous gap exceeds 6 hours.
- Reject a pair when joint valid bars cover less than 99.0% of the pair window.

Outlier rules:

- Mark `abs(return_1h) > 0.25` as `extreme_return_flag`.
- Do not silently delete extreme returns; they require review or a documented
  pair rejection reason.
- When optional execution-spread evidence exists, mark samples with
  `best_bid <= 0`, `best_ask <= 0`, or `best_ask < best_bid` as invalid and
  exclude them from spread aggregates.

Funding alignment rules:

- Join funding using `funding_time <= bar_close_time`.
- Never attach a future funding event to an earlier bar.
- If funding is missing for more than 1.0% of expected funding events inside a
  symbol window, reject the symbol for funding-aware pair selection.

Price selection rules:

- Use `mark_close` as the default statistical price.
- Use traded `close` only as a fallback or robustness view, with
  `quality_flags` marking the fallback.
- Liquidity filters always use traded quote volume, trade count, and optional
  verified execution-spread evidence, not mark price alone.

## Minimum Filters

Symbol-level history filters:

| Filter | Minimum threshold | Reject reason |
|---|---:|---|
| Valid 1h bars | `>= 26,000` | `INSUFFICIENT_HISTORY` |
| 1h coverage | `>= 99.0%` | `HISTORY_GAPS` |
| Longest missing gap | `<= 6h` | `LONG_HISTORY_GAP` |
| Funding event coverage | `>= 99.0%` expected events | `FUNDING_GAPS` |
| Mark/index/premium coverage | `>= 99.0%` expected bars | `REFERENCE_PRICE_GAPS` |

Symbol-level liquidity filters:

| Filter | Minimum threshold | Reject reason |
|---|---:|---|
| Median quote volume per 1h | `>= 1,000,000 USDT` | `LOW_MEDIAN_VOLUME` |
| p10 quote volume per 1h | `>= 100,000 USDT` | `LOW_TAIL_VOLUME` |
| Nonzero quote-volume bars | `>= 99.0%` | `VOLUME_GAPS` |
| Median trades per 1h | `>= 100` | `LOW_TRADE_COUNT` |

Conditional symbol-level execution-spread filters:

| Filter | Maximum threshold | Reject reason |
|---|---:|---|
| Median spread | `<= 3 bps` | `WIDE_MEDIAN_SPREAD` |
| p95 spread | `<= 8 bps` | `WIDE_P95_SPREAD` |
| p99 spread | `<= 15 bps` | `WIDE_P99_SPREAD` |

These filters are mandatory only when `execution_cost_quality = VERIFIED`.
When verified spread evidence is unavailable or incomplete, set
`execution_cost_quality` to `UNAVAILABLE` or `INCOMPLETE`; do not estimate
bid/ask cost from OHLCV. Such candidates may continue as statistical research
candidates but cannot satisfy a cost-gated Sprint 7 PASS.

Symbol-level funding filters:

| Filter | Maximum threshold | Reject reason |
|---|---:|---|
| Median absolute funding per event | `<= 3 bps` | `HIGH_MEDIAN_FUNDING` |
| p95 absolute funding per event | `<= 15 bps` | `HIGH_TAIL_FUNDING` |
| Missing funding events | `<= 1.0%` | `FUNDING_GAPS` |

Pair-level pre-filters before statistical ranking:

| Filter | Threshold | Reject reason |
|---|---:|---|
| Joint valid 1h coverage | `>= 99.0%` | `PAIR_HISTORY_GAPS` |
| Combined median spread, if verified | `<= 6 bps` | `PAIR_WIDE_MEDIAN_SPREAD` |
| Combined p95 spread, if verified | `<= 10 bps` | `PAIR_WIDE_TAIL_SPREAD` |
| Conservative absolute funding carry | `<= 10 bps/day` | `PAIR_HIGH_FUNDING_CARRY` |

Funding carry formula:

```text
funding_events_per_day = observed_median_events_per_day, default 3
symbol_abs_funding_bps_per_day =
    median(abs(funding_rate_asof)) * 10000 * funding_events_per_day
pair_conservative_abs_funding_bps_per_day =
    symbol_abs_funding_bps_per_day_leg_a + symbol_abs_funding_bps_per_day_leg_b
```

This pre-filter is intentionally direction-agnostic because pair direction and
beta are not known yet. Later Kalman/OU research may report signed estimated
carry for a proposed long/short orientation, but the pre-filter uses the
conservative absolute sum.

These research filters do not relax live risk limits. Any future live entry
still must pass `docs/risk_limits.md`, including the maximum combined entry
spread and slippage/depth checks.

## Look-Ahead Controls

The following rules are mandatory:

- Full-sample rankings are exploratory only and must be labeled as such in
  notebooks and reports.
- Any rolling correlation, beta, z-score, mean, standard deviation, OU estimate,
  or stationarity feature used for simulated decisions must be computed from
  data available strictly before the decision timestamp.
- A signal evaluated at bar `t` may use bar `t` values only if the decision time
  is after `close_time_t`; otherwise it must use data through `t-1`.
- Funding joins must be as-of joins using `funding_time <= decision_time`.
- Optional execution-spread joins must use bid/ask observations with exchange
  timestamps `<= decision_time`.
- Universe selection by trailing liquidity must be computed inside each
  formation window and frozen before evaluation; do not select winners using
  future volume, future listing survival, or final-period availability.
- Normalization parameters, missing-data decisions, and pair rejections must be
  fit or decided inside the formation window for any backtest or walk-forward
  evaluation.
- Delisted or renamed symbols must not be silently excluded from historical
  evaluation if they were eligible at the formation date.

## Known Risks

- The seed universe is biased toward symbols known to be liquid on
  2026-06-30; later work must address survivorship bias for walk-forward
  evaluation.
- Binance archive files can be corrected after publication; checksum and
  dataset versioning are mandatory.
- OHLCV, mark, index, and premium bars cannot prove executable spread or depth.
  Cost-gated promotion requires separate verified top-of-book/L2 evidence.
- Public historical top-of-book coverage may be unavailable for the full window;
  in that case Sprint 7 can produce statistical candidates but must not claim
  spread/cost acceptance.
- Single-venue research may overfit to Binance microstructure and funding
  mechanics.
- Funding can dominate statistical mean reversion even when price spread looks
  stationary.

## Ready Checklist

- Initial symbols are listed.
- Source, period, and frequency are defined.
- OHLCV, mark price, index price, premium index, and funding sidecars are
  defined.
- Required fields are listed.
- Cleaning and gap rules are documented.
- Liquidity, conditional spread, funding, and history filters are measurable.
- Look-ahead risk is explicitly documented.
- No data was downloaded and no exchange client was implemented in this task.
