# Sprint 9 Executable Backtest Report

Status: final report for Sprint 9 (Backtest executável com simulação de ordens, per `project_control/ROADMAP.md`).

Last updated: 2026-07-02.

Gate conclusion for Sprint 10: NAO PASSA for the roadmap's "PnL líquido ainda
é positivo em cenário conservador" criterion -- 0 of the 13 Sprint 8
backtest-approved pairs are net-profitable once entry and exit are simulated
against real tick-level order book data with aggressive (MARKET/IOC)
execution on both legs. This is a genuine, reviewed, reproducible result, not
a placeholder. It does not mean the underlying statistical edge is proven to
be zero -- see Conclusion for the specific next step needed before drawing
that stronger claim.

## Executive Summary

Sprint 8 approved 13 pairs based on an idealized fill assumption: every
signal fills 100% of both legs at the next bar's close, with cost
approximated from median historical spread. Sprint 9 replaces that
idealization with a real fill simulation: `src/backtest/fill_model.py`
consumes real, checksum-verified top-of-book quotes (best bid/ask + quantity
at that single level, from the same June-2023 tick data already downloaded
for Sprint 7/8) and applies latency, partial fills, and ACK_UNKNOWN
uncertainty; `src/backtest/execution_simulator.py` simulates a full
round-trip (entry + exit) per signal with beta-weighted sizing and explicit
leg-fill-mismatch detection; `src/backtest/replay_engine.py` replays the
exact same causal signals already reviewed in Sprint 8 against this
realistic fill model, using a memory-bounded day cache after an earlier
whole-month load caused an out-of-memory kill in this environment.

**A real bug was found and fixed during development.** Manually inspecting
one simulated trade, a partially-filled leg's `average_price` came back as
`None` even though it had a real, non-zero fill. Root cause:
`estimate_slippage` (Sprint 6, already reviewed) nulls its own
`average_price`/`slippage_bps` fields whenever an order does not fill 100%
of the requested quantity, even when a genuine partial fill occurred with
real `spent_notional` recorded. The execution simulator used
`average_price is None` as its signal for "this leg did nothing," so a
partially-filled leg's real, non-zero PnL was silently zeroed instead of
computed -- in roughly 40-50% of simulated trades, since illiquidity at
level 1 caused frequent partial fills. Fixed in
`fill_model.py::_realized_price_and_slippage` by computing the VWAP directly
from `spent_notional / filled_quantity` (always populated by
`estimate_slippage` regardless of success) instead of trusting the nulled
`average_price`. Independently re-verified by QA Agent: the math is correct,
`simulate_limit_fill` never had this bug, and the corrected result becoming
*more* negative (not less) is exactly what the bug's mechanics predict.

A second real gap was found by Market Data Agent review: the replay engine
computed a SHA256 checksum for provenance labeling but never actually
compared it against the recorded checksum sidecar before trusting the data
-- fail-open, not fail-closed, inconsistent with the pattern already
established in Sprint 7/8. Fixed by calling `verify_checksum_file` before
reading each archive.

**Corrected, reviewed, final result**: 247 signals, 239 executed trades
across the 13 pairs, **0 of 13 pairs net-profitable**, portfolio
`total_net_pnl_quote = -$2266.27`. 70 of 239 trades (29%) show a
leg-fill-mismatch (the two legs filled to meaningfully different
proportions), and a combined 11,470.92 units of position quantity across all
trades were never closed out by the paired exit order -- a real, previously
invisible "naked leg" exposure that is not marked to market in the reported
PnL (see Risks).

## Methodology

| Component | Definition |
|---|---|
| Fill source | Real, checksum-verified top-of-book quotes (best bid/ask + quantity at level 1 only) from `data/research/binance_public/cost_pilot/raw/` -- no depth beyond level 1 is fabricated anywhere |
| Signal | The exact same causal signals already generated and reviewed in Sprint 8 (`generate_pair_signal_intents`), filtered to the same walk-forward test windows -- Sprint 9 changes execution realism only, not signal generation |
| Order type | MARKET_IOC (aggressive, crosses the spread) on both entry and exit, for both legs -- see Risks for why this is a conservative upper bound on execution cost, not the only viable execution style |
| Latency | 250ms fixed offset: the execution quote is the earliest quote at or after `decision_time + latency_ms` |
| ACK_UNKNOWN | 2% rate, deterministic per `order_id` (SHA256-hash-based, not global RNG state); reuses the real `evaluate_ack_guard`/`AckGuardOrderStatus` from Sprint 3 -- an ACK_UNKNOWN entry leg genuinely delays the paired exit order until reconciliation would complete, mirroring the real "same-leg-uncertain-slice-blocked" rule |
| Holding period | 1 hour, unchanged from Sprint 8, to isolate execution realism as the only variable under test |
| Position sizing | Leg A: `target_notional / reference_price`; Leg B: `abs(beta) * target_notional / reference_price`, consistent with the beta-weighted spread the signal was generated from |
| PnL | Computed from `min(entry.filled_quantity, exit.filled_quantity)` per leg -- i.e., only the quantity actually closed, not the quantity intended |
| Memory safety | Bounded FIFO day-cache (max 4 unique symbol-days resident at once); a prior attempt to load a full month of tick data at once caused an OOM kill |

Source: `src/backtest/fill_model.py`, `src/backtest/execution_simulator.py`,
`src/backtest/replay_engine.py`, `scripts/run_sprint9_replay.py`.

## Results

Aggregate (`data/research/binance_public/cost_pilot/sprint9_replay_results.json`):

| Metric | Value |
|---|---:|
| Pairs evaluated | 13 |
| Pairs realistic-net-positive | **0** |
| Total signals | 247 |
| Total executed trades | 239 |
| Total net PnL (quote) | **-$2266.27** |
| Total leg-fill-mismatch trades | 70 / 239 (29%) |
| Total partially-filled entry legs | 75 |
| Total partially-filled exit legs | 76 |
| Total ACK_UNKNOWN entry legs | 6 |
| Total no-quote entry legs | 16 |
| Total unclosed residual quantity (all trades, both legs) | 11,470.92 units |
| `portfolio_gate_pass` | false |

Per-pair comparison against the Sprint 8 idealized result
(`data/research/binance_public/cost_pilot/sprint9_replay_pair_results.csv`
vs `sprint8_backtest_results.json`):

| Pair | Sprint 8 idealized (bps) | Sprint 9 realistic (quote) | Trades | Leg mismatch | Unclosed residual qty |
|---|---:|---:|---:|---:|---:|
| ETHUSDT/OPUSDT | 246.58 | -111.60 | 13 | 1 | 416.26 |
| AVAXUSDT/SOLUSDT | 19.99 | -128.66 | 18 | 8 | 108.65 |
| AVAXUSDT/ETHUSDT | 398.77 | -134.46 | 17 | 6 | 122.01 |
| DOGEUSDT/ETHUSDT | 270.80 | -138.84 | 10 | 0 | 0.03 |
| ETHUSDT/UNIUSDT | 143.39 | -152.59 | 20 | 1 | 67.45 |
| ARBUSDT/ETHUSDT | 88.29 | -166.82 | 13 | 4 | 1203.42 |
| ETCUSDT/LTCUSDT | 542.58 | -169.91 | 24 | 8 | 190.96 |
| ARBUSDT/DOTUSDT | 169.95 | -188.67 | 18 | 6 | 1541.51 |
| ARBUSDT/LINKUSDT | 31.80 | -194.23 | 21 | 3 | 2092.47 |
| ARBUSDT/OPUSDT | 331.87 | -194.59 | 20 | 8 | 3101.63 |
| ARBUSDT/AVAXUSDT | 456.59 | -199.29 | 17 | 6 | 2246.25 |
| DOGEUSDT/ETCUSDT | 50.54 | -218.78 | 26 | 9 | 212.73 |
| ETCUSDT/ETHUSDT | 25.09 | -267.82 | 22 | 10 | 167.53 |

Every one of the 13 pairs -- including `ETCUSDT/LTCUSDT` and
`ARBUSDT/AVAXUSDT`, Sprint 8's two strongest idealized performers at 542.58
and 456.59 bps respectively -- flips to net negative once real fills,
latency, and partial-fill mechanics are applied. There is no partial
survivor: the flip is universal across the 13-pair universe.

Full per-pair results:
`data/research/binance_public/cost_pilot/sprint9_replay_pair_results.csv`.

## Verification

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 242 tests (14 fill_model.py tests, 9 execution_simulator.py
tests, 7 replay_engine.py tests, 4 sprint9_chaos.py tests, plus all prior
sprint suites).

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src scripts tests
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint9_replay.py
Result: passed. 13 pairs, 239 executed trades, 0 net-positive, portfolio
-$2266.27. Real network access: none (all data already downloaded and
checksum-verified in Sprint 7/8).
```

Formal reviews (per `project_control/CURRENT_SPRINT.md`'s Sprint 9 reviewer
list):

```text
Backtest Agent: MUDANCAS SOLICITADAS on report communication, not code.
Findings: (1) MARKET_IOC on both legs needs an explicit "upper-bound cost
scenario" caveat so the 0/13 result is not read as a definitive verdict on
the strategy itself (addressed in this report's Risks/Conclusion); (2) the
aggregate summary counted partially-filled ENTRY legs but not EXIT legs,
making residual/unclosed exposure invisible -- fixed by adding
partially_filled_exit_leg_count and unclosed_residual_quantity to the
summary. Confirmed the 0/13 result is plausible given typical Sprint 8 gross
edge (~10-30bps/trade) versus the cost of crossing the spread 4 times
(2 legs x entry+exit) with partial fills in ~40-50% of trades. 29 tests
passed at review time.

QA Agent: PASSA. Independently re-derived the partial-fill bug fix's math:
spent_notional/filled_quantity is provably the correct VWAP (matches
estimate_slippage's own success-path formula), confirmed simulate_limit_fill
never had this bug (it always computed average_price from its own locally
accumulated filled_notional/filled_quantity), confirmed filled_quantity==0
still correctly yields average_price=None everywhere, and found no other
instance of the "is None from another module as a proxy for nothing
happened" bug pattern in the reviewed files. Confirmed the corrected result
becoming more negative (not less) is exactly consistent with the bug's
mechanics -- restoring real PnL to previously-zeroed partial legs could only
push an already-negative distribution further negative, not produce an
artificial improvement. One P3: simulate_limit_fill hardcodes
slippage_bps=0.0 regardless of reference_price, an inconsistent metric
definition versus MARKET orders (not a hidden-PnL bug, logged as technical
debt).

Market Data Agent: MUDANCAS SOLICITADAS, now addressed. P1 (fixed): checksum
was computed but never verified against the recorded sidecar before use --
fail-open, not fail-closed. Fixed by calling verify_checksum_file before
reading each archive, with new regression tests for both the
missing-sidecar and checksum-mismatch cases. Confirmed level-1-only
consumption with no fabricated depth anywhere in the reviewed code. P3:
"realistic execution" should be qualified as "against real level-1 quotes,
with modeled (not measured) latency and ACK_UNKNOWN assumptions" -- avoid
implying this replicates the exchange's actual matching engine (reflected
in this report's language).

Execution / Risk Agent (consultative, forward-looking to Sprint 10): 250ms
latency is a reasonable floor but optimistic as a fixed single value (no
jitter, no volatility-dependent spikes, no rate-limit backoff modeled) --
should be calibrated to a p50/p95/p99 distribution before use in a real
Risk Gate. The 2% ACK_UNKNOWN rate is mechanically correct but an
uncalibrated assumption, not a measurement -- stated explicitly here.
Confirmed in code that execution_simulator.py calls only
simulate_market_fill, never simulate_limit_fill, despite the latter existing
and being tested -- the roadmap's Sprint 9 promise to test "IOC vs. maker
não preenchido" was only partially delivered (IOC yes, maker no) and this is
logged as an explicit gap, not left implicit. Leg risk / unclosed residual
exposure is assessed as a first-class, serious risk equivalent to a real
"naked leg" in production, requiring a Hedge Engine, Barrier Manager, or
forced Emergency Exit before any real-capital promotion. Explicit
recommendation: do not conclude "the strategy has no edge" from this 0/13
result alone -- test at least one passive/maker execution variant
(simulate_limit_fill is already implemented and tested, just not wired into
the real runner) before drawing that stronger conclusion.
```

## Risks

- **All-IOC execution is the most expensive scenario tested, not the only
  one.** Every entry and exit crosses the spread on both legs. A real
  execution strategy could use passive/maker orders (`simulate_limit_fill`
  already exists and is tested) to reduce cost, especially on exit. The
  0/13 result should be read as "the strategy is not profitable under
  maximally aggressive execution," not "the strategy has zero statistical
  edge" -- these are different claims, and only the first one is
  established here.
- **Unclosed residual exposure ("naked leg") is not marked to market.**
  11,470.92 units of position quantity across all trades were opened by an
  entry fill but never closed by the paired exit fill within the measured
  window. The reported net PnL only reflects the quantity that actually
  closed; the residual is neither realized nor valued, meaning both the
  true risk and the true (positive or negative) PnL of this backtest are
  understated, not overstated. In a live system this is exactly the
  scenario a Hedge Engine, Barrier Manager, or forced Emergency Exit exists
  to resolve (see `project_control/ROADMAP.md` Sprints 21-22); none of
  those exist yet, so this remains an open, first-class risk, not a
  footnote.
- **Latency (250ms) and ACK_UNKNOWN rate (2%) are modeled assumptions, not
  measurements.** No real production telemetry exists yet to calibrate
  either. Do not treat these as validated inputs for the Execution Risk
  Gate (Sprint 10) without recalibration against real order-placement data.
- **No passive/maker execution variant was tested in the real runner.**
  `simulate_limit_fill` exists and is unit-tested but `execution_simulator.py`
  never calls it. This is required to distinguish "execution too
  conservative" from "no statistical edge" per Execution/Risk Agent's
  explicit recommendation.
- **`simulate_limit_fill`'s slippage_bps is always 0.0 regardless of
  reference price**, an inconsistent metric definition versus MARKET orders
  (QA Agent P3). Low severity, but would confuse any slippage-by-order-type
  analysis built on top of this later.
- This report is scoped to June 2023 and the same 13 pairs Sprint 8
  approved. It inherits every limitation already logged for that window in
  `reports/sprint_08_backtest.md` and `reports/research_sprint_07.md`
  (single-month evidence, no p95/p99 cost sensitivity, Binance bookTicker
  unavailable for most of the original 36-month window).

## Conclusion

Technical implementation: PASSA. `fill_model.py`, `execution_simulator.py`,
and `replay_engine.py` are implemented, formally reviewed by Backtest
Agent, QA Agent, Market Data Agent, and Execution/Risk Agent, and covered by
34 new automated tests (14 + 9 + 7 + 4 across the four new test files). Both
findings that emerged from review (the partial-fill PnL bug and the
unverified-checksum gap) were fixed and independently re-confirmed correct,
not left as known issues.

Sprint 10 gate for "PnL líquido ainda é positivo em cenário conservador":
**NAO PASSA**. 0 of the 13 Sprint 8 backtest-approved pairs are net-profitable
under real tick-level execution with aggressive IOC orders on both legs of
both entry and exit; portfolio net PnL is -$2266.27. This is a genuine,
reviewed, reproducible result -- not a placeholder or an artifact of the
bug that was found and fixed (the bug fix made the result *more* negative,
and QA Agent confirmed this direction is exactly what correcting the bug
predicts).

This does **not** mean the underlying pair-trading statistical edge is
proven to be zero. Per Execution/Risk Agent's explicit recommendation, the
required next step before drawing that stronger conclusion is to test at
least one passive/maker execution variant using `simulate_limit_fill`
(already implemented, tested, just not wired into the real runner) to
separate "the signal has no edge" from "all-aggressive execution is too
expensive for this edge to survive." Do not proceed to Sprint 10 (Execution
Risk Gate) or any paper/live trading work with the current 13-pair universe
as if it had a demonstrated edge -- it does not, under the execution
assumptions tested so far.
