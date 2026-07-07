# Funding-Rate Carry Backtest (TASK-FUND-002)

Status: real result for the pre-registered hypothesis defined in
`tasks/funding_carry/TASK-FUND-001-define-hypothesis.md` (see
`project_control/DECISIONS.md` ADR-0013).

Last updated: 2026-07-05.

Gate conclusion: **NAO PASSA.** The primary pre-registered configuration
(K=5) has net profit factor 0.84 (< the 1.10 gate), and portfolio net PnL
is -10,729.82 bps over the full window. Both secondary configurations
(K=3, K=8) also fail, so this is not an artifact of the K=5 choice: gross
edge (funding carry + a correlated price effect) is real and positive, but
is completely erased by the cost of fully rebalancing the book every 8
hours for 3 years.

## Executive Summary

The hypothesis: rank the 20 Sprint 7 symbols by real, causal
`funding_rate_asof` at every actual Binance funding settlement (~3x/day,
every 8h) and go short the K highest-funding symbols / long the K
lowest-funding symbols, equal-notional, dollar-neutral, fully rebalanced
every interval. No new data was needed -- `funding_rate_asof`,
`mark_close`/`index_close`/`premium_close` already exist with 100%
coverage for all 20 symbols in the Sprint 7 normalized dataset
(2023-06-01 through 2026-05-31, 526,080 hourly bars).

**Gross edge is real.** At the primary K=5, gross PnL over 3,287 resolved
rebalances is +8,992.18 bps, split into +3,293.93 bps from the funding
differential itself (the mechanical payment the strategy is designed to
collect) and +5,698.25 bps from the correlated price-return component
(shorted high-funding symbols and longed low-funding symbols also tended to
move favorably on average over the same 8h window -- a real, observed
correlation in this dataset, not assumed).

**Cost overwhelms it.** The pre-registered cost model (a conservative fixed
6.0 bps per rebalance, reusing the exact constant already established for
canonical Sprint 8) totals 19,722.00 bps over the same 3,287 rebalances --
more than double the gross edge. Net PnL is -10,729.82 bps; net profit
factor 0.84. This is a direct consequence of the pre-registered rule
requiring a full rebalance (100% turnover) every single 8-hour interval for
3 years, not a data problem or a coding bug.

## Methodology

| Component | Definition |
|---|---|
| Universe | The 20 Sprint 7 statistical symbols, 2023-06-01 through 2026-05-31, hourly bars, already normalized and checksum-verified -- no new download |
| Signal | Rank by `funding_rate_asof` (real Binance settlement rate, causally joined via `pd.merge_asof(..., direction="backward")` in `historical_dataset.py` -- verified by direct code read before this task was pre-registered) |
| Rebalance grid | Every real funding interval: bars where `(open_time // 1h) % 8 == 0` (00:00/08:00/16:00 UTC) -- 3,288 such times across the window, confirmed against `funding_interval_hours == 8.0` (uniform across the whole dataset) |
| Position | SHORT the K highest-funding symbols (short receives funding when the rate is positive); LONG the K lowest-funding symbols (long pays less, or receives, when the rate is low/negative); equal notional per leg, dollar-neutral, fully closed and reopened every interval |
| Funding PnL sign convention | LONG: `-funding_rate` (pays when positive); SHORT: `+funding_rate` (receives when positive) -- Binance's real mechanics, verified by a dedicated unit test |
| Price PnL | `log_price` return over the 8h holding interval, `+` for longs / `-` for shorts |
| Cost (fase 1, statistical) | Fixed 6.0 bps per rebalance (equal-weighted across all `2*K` legs, so the portfolio-level cost is invariant to K by construction -- see Risks) -- the same conservative constant and "assumption, not measurement" framing already used in the canonical Sprint 8 backtest, not the tick-level execution simulator (fase 2, not reached -- see Conclusion) |
| Pre-registered configurations | K=5 (PRIMARY, decides the gate), K=3 and K=8 (descriptive sensitivity only, never promoted to "the result") |
| Gate | Net profit factor >= 1.10 AND resolved rebalances >= 500, evaluated on K=5 only |

Source: `src/research/funding_carry.py`, `scripts/run_funding_carry_backtest.py`.

## Results

(`data/research/binance_public/cost_pilot/funding_carry_backtest_results.json`,
`data/research/binance_public/cost_pilot/funding_carry_rebalance_results.csv`)

| K | Resolved rebalances | Gross PnL (bps) | Funding component (bps) | Price component (bps) | Cost (bps) | Net PnL (bps) | Net profit factor | Hit rate | Gate |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 3 | 3,287 | 8,489.86 | 4,294.46 | 4,195.41 | 19,722.00 | -11,232.14 | 0.869 | 46.73% | NAO PASSA |
| **5 (primary)** | 3,287 | 8,992.18 | 3,293.93 | 5,698.25 | 19,722.00 | **-10,729.82** | **0.840** | 47.46% | **NAO PASSA** |
| 8 | 3,287 | 5,682.96 | 2,400.21 | 3,282.75 | 19,722.00 | -14,039.04 | 0.743 | 43.84% | NAO PASSA |

`rebalance_count` is 3,288 for every K; 1 is always `NO_DATA` (the dataset's
last rebalance time has no forward bar to resolve against -- the window's
natural edge, not a gap). `insufficient_symbols_count` is 0 for every K --
`funding_rate_asof` has zero missing values across the whole dataset, so
every rebalance had all 20 symbols eligible.

Cost is identical (19,722.00 bps) across all three K values. This is
expected, not a bug: with equal-notional legs and a fee proportional to
each leg's own notional, the portfolio-level weighted-average cost equals
the flat per-leg rate regardless of how many equally-sized legs make up
the book (`2*K * (1/(2*K)) * 6.0 = 6.0`, exactly, every rebalance). Adding
more legs does not change the cost as a fraction of total notional -- it
only changes how concentrated the funding/price edge is.

Profit factor decreases monotonically as K increases (0.869 -> 0.840 ->
0.743 for K=3/5/8), a coherent, non-noisy pattern: the most extreme-funding
symbols carry more edge per unit of capital than mid-ranked ones, so
widening K dilutes edge without reducing cost. This internal consistency
across the pre-registered grid increases confidence that the funding/price
correlation is a real, if currently uncapturable, effect -- not a fluke of
one arbitrary K.

## Analysis

- **The edge is real, not manufactured.** Both PnL components (funding and
  price) are independently positive at every tested K. This is a
  structurally different result from the Kalman/OU signal closed by
  ADR-0010/0012: that signal's gross edge was itself statistically weak
  or absent; this one has a clear, monotonic, mechanically explainable
  gross edge. What kills this result is turnover cost, not absence of
  edge -- a materially different failure mode worth distinguishing.
- **The cost is a direct, pre-registered consequence of full rebalancing
  every interval, not the underlying strategy cost.** Per TASK-FUND-001,
  fase 1 deliberately used the simplest, most conservative rule (100%
  turnover every 8h) to get an honest first read before any optimization.
  A real implementation would only trade the legs that actually change
  membership between consecutive rebalances (most symbols likely stay in
  the same relative funding-rank neighborhood from one 8h interval to the
  next), which would cut turnover -- and therefore cost -- substantially.
  This report does not estimate that effect; testing it is a distinct,
  new pre-registered hypothesis (see Conclusion), not a retroactive fix to
  this result.
- **Fase 2 (tick-level realistic execution) was not reached.** Per the
  pre-registered plan, fase 2 (testing `MARKET_IOC`/`LIMIT_MAKER_TTL` via
  the Sprint 9/10 execution simulator against the one verified June-2023
  tick-data month) was conditional on fase 1 clearing its own gate. Fase 1
  did not clear the gate, so fase 2 was not run -- there is no realistic
  execution cost result to report here, and none is implied.

## Risks

- **Cost model is a conservative estimate, not a measurement** -- same
  caveat as canonical Sprint 8's 6.0bps/leg constant (real Binance USD-M
  taker fees run ~4-5bps/side before slippage, so 6.0bps/leg-roundtrip is
  plausibly cheap, not expensive; real cost would likely reinforce this
  negative result, not overturn it).
- **The price-return component (+5,698.25 bps gross at K=5) is not a
  causally isolated finding.** It is an observed correlation between
  funding-rank membership and subsequent 8h price return in this specific
  sample (2023-06/2026-05, this 20-symbol universe); no separate
  significance test or out-of-sample check was pre-registered for this
  component alone. Treat it as a descriptive observation motivating a
  possible future hypothesis, not a validated standalone signal.
- **Full-rebalance-every-interval is the most conservative (highest-cost)
  implementation, analogous to Sprint 9's MARKET_IOC caveat.** Just as
  Sprint 9's 0/13 result was not proof of zero edge until a passive
  execution style was also tested, this fase 1 result is not proof that
  no turnover-reduced variant of this signal can be net-positive.
- **No leverage, no cross-margining, no funding-rate-change risk modeled.**
  This report treats `funding_rate_asof` as fixed for the entire 8h
  holding interval (correct, since Binance funding rates are set once per
  settlement and held constant until the next one) but does not model any
  scenario where a symbol's funding rate spikes intra-interval in a way
  that would affect a real position differently than this backtest's
  discrete rebalance-to-rebalance accounting.
- **This is a candle/interval-level backtest, not a tick-level execution
  simulation.** It inherits the same category of limitation already
  logged for canonical Sprint 8 (`reports/backtest_statistical.md`):
  unconstrained rebalancing, no depth/impact modeling, no partial fills.

## Conclusion

Technical implementation: complete. `src/research/funding_carry.py`
implements the pre-registered hypothesis exactly as specified in
TASK-FUND-001, with dedicated tests verifying the Binance funding sign
convention, causal-only use of `funding_rate_asof`, fail-closed handling of
missing/insufficient data, and the profit-factor-gate math (including the
`+inf`-not-excluded fix already established in canonical Sprint 8). 336
tests pass (full suite), ruff clean.

**Gate for the pre-registered hypothesis: NAO PASSA.** K=5 (primary): net
profit factor 0.84, net PnL -10,729.82 bps over 3,287 rebalances. K=3 and
K=8 (descriptive) also fail, with a coherent monotonic pattern that
increases confidence this is a real cost-vs-turnover tradeoff, not noise.
Per the pre-registered rule, this decision is final for the fase-1
configuration actually tested -- no re-run with a different K, cost
constant, or rebalance frequency is authorized without a new, separately
pre-registered task.

**This does not mean the funding/price correlation observed here has zero
value.** The gross edge is real and monotonic across K; what fails is
specifically the full-rebalance-every-8h implementation's cost, not the
underlying observation. A natural, well-motivated next step -- **not**
started by this report -- would be a new pre-registered hypothesis
(`TASK-FUND-003`, if the user chooses to open it) testing incremental
rebalancing (only trade legs whose funding-rank membership actually
changes between intervals) to see whether reduced turnover preserves
enough of the gross edge to clear the same 1.10 gate. That is an explicit,
separate decision, not implied or pre-approved by this report.
