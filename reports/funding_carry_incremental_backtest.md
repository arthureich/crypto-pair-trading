# Funding-Rate Carry: Incremental Rebalancing (TASK-FUND-003)

Status: real result for the pre-registered incremental (yield-threshold)
variant defined in
`tasks/funding_carry/TASK-FUND-003-incremental-rebalancing.md` (see
`project_control/DECISIONS.md` ADR-0013).

Last updated: 2026-07-05.

Gate conclusion: **NAO PASSA at the pre-registered primary K=5** -- net
profit factor 1.0904, a difference of only 0.0096 from the 1.10 threshold,
on 3,287 resolved rebalances (far above the 500 floor, so this is not an
underpowered-sample near-miss). Per the pre-registered rule, this decision
is binding; the fact that the secondary, descriptive-only K=3 configuration
clears the gate (profit factor 1.1356) is reported honestly below but is
**not** substituted for the primary result.

This is nonetheless the strongest result in the Funding Carry Signal
Iteration so far: incremental rebalancing turned TASK-FUND-002's deeply
negative result (net PnL -10,729.82 bps at K=5) into a positive one
(+5,620.99 bps at K=5) by cutting turnover-driven cost by over 99.8%
(19,722.00 bps -> 33.60 bps), while preserving most of the gross edge as a
*rate* (profit factor went from 0.840 to 0.9096-away-from-passing, i.e.
1.0904).

## Executive Summary

TASK-FUND-002 (fase 1) found real, positive gross edge in cross-sectional
funding-rate carry, but a 100%-turnover-every-8h rebalance rule made cost
(19,722.00 bps at K=5) more than double the gross edge (8,992.18 bps),
producing a deeply negative net result. This report tests the specific,
pre-approved fix: only replace a held leg when the funding-rate improvement
of the best available candidate exceeds `cost_bps_per_leg_roundtrip` (the
same 6.0 bps constant already pre-registered -- no new tunable parameter).

**Result: turnover collapses, edge survives, but falls just short of the
gate at the pre-registered K.**

| K | Resolved rebalances | Total swaps | Cost (bps) | Gross PnL (bps) | Net PnL (bps) | Net profit factor | Gate |
|---:|---:|---:|---:|---:|---:|---:|---|
| 3 | 3,287 | 53 | 53.00 | 11,343.18 | **11,290.18** | **1.1356** | PASSA (descriptive only) |
| **5 (primary)** | 3,287 | 56 | 33.60 | 5,654.59 | **5,620.99** | **1.0904** | **NAO PASSA** |
| 8 | 3,287 | 48 | 18.00 | 4,149.97 | 4,131.97 | 1.0856 | NAO PASSA |

At K=5, only 56 swap events occurred across 3,287 rebalances (about one
swap every 59 rebalances, aggregated across both sides) -- versus fase 1's
full turnover of `2*K=10` legs on *every single* rebalance. Cost dropped
from 19,722.00 bps to 33.60 bps (a 99.83% reduction). Every K shows the
same qualitative pattern: positive net PnL, profit factor in the
1.08-1.14 range, right at the edge of the pre-registered 1.10 gate.

## Methodology

| Component | Definition |
|---|---|
| Universe, signal, sign convention | Identical to TASK-FUND-002 (fase 1) -- same 20 symbols, same causal `funding_rate_asof`, same Binance funding-sign convention (independently adversarially reviewed this session, see `HANDOFFS.md`) |
| Retention rule | A held leg is kept unless a swap clears the yield threshold: `|funding_rate_asof(candidate) - funding_rate_asof(held)| * 10,000 > cost_bps_per_leg_roundtrip` (6.0 bps, the same constant, no new parameter) |
| Swap search | Greedy, per side, per interval: repeatedly compare the single worst-held leg against the single best available candidate in a pool fixed at the start of the interval, until no more profitable swap exists |
| Forced exits | A held leg that becomes ineligible (non-finite funding/price) is force-removed and its slot refilled unconditionally from the candidate pool (never subject to the yield threshold -- holding nothing is strictly worse than holding any real candidate); not exercised by the real 20-symbol dataset (0 ineligible observations), verified by a dedicated synthetic test |
| Capital allocation | Every held leg's target weight stays flat at `1/(2*K)`, identical every interval (no NAV-drift modeling, consistent with fase 1's own convention). A leg that is neither entered nor exited this interval has `Δweight = 0` -- no order, no cost, but it still earns its pro-rata funding+price PnL for the interval |
| Cost accounting | One swap (exit one leg + enter another) is charged exactly one `cost_bps_per_leg_roundtrip`-equivalent, weighted `1/(2*K)` -- an explicit modeling choice, not a measurement (see Risks) |
| Bootstrap | The first rebalance (or a hypothetical full wipeout, never triggered by real data) builds the book from scratch exactly like fase 1, at the same flat `cost_bps_per_leg_roundtrip` cost (`2*K` refills * `1/(2*K)` weight = the same constant) |
| Configuration | Same pre-registered grid as fase 1: K=5 (PRIMARY, decides the gate), K=3/K=8 (descriptive only) |
| Gate | Net profit factor >= 1.10 AND resolved rebalances >= 500, evaluated on K=5 only -- identical rule, not re-opened for this report |

Source: `src/research/funding_carry.py`
(`run_incremental_funding_carry_backtest`, `_refill_vacancies`,
`_apply_yield_threshold_swaps`),
`scripts/run_funding_carry_incremental_backtest.py`.

## Fase 1 vs Fase 2 (K=5, primary)

| Metric | Fase 1 (full rebalance) | Fase 2 (incremental) | Delta |
|---|---:|---:|---:|
| Gross PnL (bps) | 8,992.18 | 5,654.59 | -3,337.59 |
| Cost (bps) | 19,722.00 | 33.60 | **-19,688.40 (-99.83%)** |
| Net PnL (bps) | -10,729.82 | **+5,620.99** | **+16,350.81** |
| Net profit factor | 0.840 | 0.9096 → **1.0904** | +0.2504 (in profit-factor units, not a percentage) |
| Gate | NAO PASSA | NAO PASSA (0.0096 short) | -- |

Gross edge itself is *lower* in fase 2 (5,654.59 vs 8,992.18 bps) -- this is
expected, not a contradiction: fase 1 always holds the exact current
top-K/bottom-K, capturing every momentary extreme; fase 2 deliberately
tolerates holding a slightly-less-extreme leg when swapping would not clear
the cost bar, so it captures a smaller fraction of each moment's most
extreme differential in exchange for avoiding turnover cost almost
entirely. The trade dominates in this dataset: net PnL improves by
16,350.81 bps despite giving up 3,337.59 bps of gross edge.

## Analysis

- **The gap to the gate is small and not a power problem.** 1.0904 vs 1.10
  is a 0.87% relative shortfall, on 3,287 resolved rebalances (6.57x the
  pre-registered 500-rebalance floor). This is not the TASK-SIG-003-style
  situation of a real effect drowned by an underpowered sample -- the
  sample here is large and the result is a genuine, precise near-miss.
- **K=3 passing does not change the K=5 decision.** Per the pre-registered
  rule (this project's standing discipline since TASK-SIG-003 Run 1),
  K=3/K=8 are descriptive sensitivity checks, fixed *before* running, not
  a menu to pick the best result from after seeing outcomes. Reporting
  K=3's 1.1356 here is required for transparency, not as grounds to
  reclassify the gate decision.
- **The pattern (K=3 > K=5 > K=8 in profit factor) is monotonic, same as
  fase 1** -- tighter K concentrates capital on the most extreme, most
  persistently mispriced legs, consistent with a real, structural effect
  rather than noise. This reinforces (does not, by itself, overturn) the
  K=5 gate outcome.
- **The core mechanism worked exactly as designed.** The pre-registered
  hypothesis was specifically that turnover, not lack of edge, was fase
  1's problem. This report confirms that mechanism quantitatively: a
  99.83% cost reduction at K=5, with gross edge surviving well enough to
  turn a deeply negative result into a small positive one. That the result
  still falls just short of a fairly strict, pre-existing 1.10 threshold
  is a genuine, informative finding about the strategy's current edge
  margin -- not evidence the incremental-rebalancing idea was wrong.

## Risks

- **The "one swap = one full round-trip cost" convention is an explicit
  modeling choice, not a measurement.** A swap (exit one leg, enter
  another) could plausibly cost less than a fresh full round-trip if, for
  example, exit and entry orders are placed with correlated timing or
  favorable queue position -- this report does not attempt that level of
  execution-cost modeling (that would be fase 2 of TASK-FUND-002's
  original two-phase plan: tick-level realistic execution, not reached
  here either, for the same reason -- the statistical gate did not clear).
  If anything, this is likely conservative (biased toward higher cost),
  consistent with this project's "err conservative" convention elsewhere.
- **No parameter beyond K was varied, by design** -- this report does not
  search over TTL-like thresholds, alternate cost constants, or partial
  (fractional) rebalancing schemes. Per this project's discipline, any of
  those would be a new, separately pre-registered hypothesis, not a
  retroactive adjustment to try to clear the K=5 gate.
- **Bootstrap cost (one-time, first interval only) is a small fraction of
  total cost and does not materially affect the multi-year result** (33.60
  bps total cost at K=5 across the whole window; the one-time bootstrap
  contributes 6.0 bps of that, about 18%).
- Inherits the same fase-1 caveats: the price-return correlation component
  has no separate significance test; this is a candle/interval-level
  backtest, not tick-level execution; no leverage/cross-margin modeled.

## Conclusion

Technical implementation: complete. `run_incremental_funding_carry_backtest`
reuses the same independently-verified sign convention and PnL formula as
fase 1 (via a shared helper), adds the pre-registered yield-threshold
retention rule and unconditional forced-exit refill, and is covered by 6
new tests (bootstrap-equivalence, hold-below-threshold, swap-above-threshold,
forced-exit-refill, causal-independence-from-forward-price, and
cross-compatibility with the existing summarizer). 342 tests pass (full
suite), ruff clean.

**Gate for the pre-registered hypothesis at K=5 (primary): NAO PASSA** --
profit factor 1.0904 vs the 1.10 threshold, on 3,287 resolved rebalances.
This is a precise, well-powered near-miss, not an underpowered or noisy
result, and it followed a fix (incremental rebalancing) that worked
exactly as intended: cost fell 99.83% and net PnL flipped from -10,729.82
to +5,620.99 bps. K=3 (1.1356) passes but is descriptive-only per the
pre-registered rule and is not substituted for K=5.

Per this project's standing discipline (ADR-0010), this specific
pre-registered configuration does not get re-run with a different K,
threshold, or cost constant after seeing this result. Any further
iteration on this exact mechanism -- e.g., a dedicated, separately
pre-registered test of whether K=4 (between the tested K=3 and K=5) also
clears the gate, or of partial/fractional position sizing -- is a new
task requiring the user's explicit decision, not an automatic next step
implied by how close this result came.
