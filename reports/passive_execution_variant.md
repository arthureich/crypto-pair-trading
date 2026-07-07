# Passive/Maker Execution Variant (Sprint 10, Block 1)

Status: real result for the first block of Sprint 10 ("Passive/Maker
Execution Variant + Execution Risk Gate prep"), per
`project_control/DECISIONS.md` ADR-0011.

Last updated: 2026-07-05.

Gate conclusion: **the roadmap's "PnL líquido ainda é positivo em cenário
conservador" criterion remains NAO PASSA.** 0 of the 13 Sprint 8
backtest-approved pairs are net-profitable under `LIMIT_MAKER_TTL`, exactly
as under Sprint 9's `MARKET_IOC`. Passive execution reduces the portfolio's
net loss by $260.35 (-$2266.27 → -$2005.91, about 11.5% less negative), but
does **not** flip a single pair to positive, and it increases total unclosed
residual exposure by 27% (11,470.92 → 14,565.31 units). This answers the
open question left by Sprint 9 (Execution/Risk Agent's recommendation): the
negative result is not simply an artifact of maximally aggressive execution
cost.

## Executive Summary

Sprint 9 (`reports/backtest_executable_v1.md`) tested only `MARKET_IOC`
(aggressive, crosses the spread) on both legs of both entry and exit --
explicitly flagged as the most expensive execution style tested, not proof
the strategy has zero edge. This report implements and runs the recommended
follow-up: `LIMIT_MAKER_TTL`, a resting order quoted at the touch (best bid
for a BUY, best ask for a SELL) that never crosses the spread at placement
and only fills if the market later crosses to it within a 60-second TTL.

Both execution styles were replayed against the exact same 13 Sprint 8
backtest-approved pairs, the exact same causal signals
(`generate_pair_signal_intents`, unchanged), and the exact same
checksum-verified June-2023 real tick-level bookTicker data already used in
Sprint 9. No signal-generation code changed. Before trusting the comparison,
the script reran `MARKET_IOC` through the new `ExecutionStyle`-aware code
path and confirmed it **exactly reproduces** the original Sprint 9 result
(all metric deltas 0, PnL delta 0.0) -- the refactor of
`execution_simulator.py`/`replay_engine.py` did not silently change the
existing baseline, it only added a new path alongside it.

**Result: still 0/13 pairs net-positive.** `LIMIT_MAKER_TTL` improves
portfolio net PnL by $260.35 (about 11.5% less negative than `MARKET_IOC`),
consistent with the Execution/Risk Agent's hypothesis that some of Sprint
9's loss was pure spread-crossing cost. But the improvement is not close to
flipping the portfolio, or even a single pair, to positive -- 11 of 13
pairs individually improve, while 2 pairs (`ETCUSDT/ETHUSDT`,
`ETCUSDT/LTCUSDT`) get *worse* under the passive style. Passive execution
also introduces a new, real cost: **65 entry legs (26% of all entry-leg
attempts) and 36 exit legs expired unfilled** within the 60-second TTL --
a failure mode `MARKET_IOC` cannot have by construction -- and total
unclosed residual ("naked leg") exposure across the portfolio is 27%
*higher* under the passive style, not lower.

## Methodology

| Component | Definition |
|---|---|
| Execution styles compared | `MARKET_IOC` (Sprint 9 baseline, rerun here as a regression check) vs. `LIMIT_MAKER_TTL` (new) |
| `LIMIT_MAKER_TTL` order placement | Best bid (BUY) / best ask (SELL) at the order's own decision time -- never crosses the spread at placement (enforced by `simulate_limit_fill`'s crossing check, independently of any test) |
| `LIMIT_MAKER_TTL` fill condition | Only fills if a *later* quote crosses back to the resting price before `limit_ttl_ms` elapses; otherwise EXPIRED (unfilled) or PARTIALLY_FILLED (residual) |
| `limit_ttl_ms` | 60,000 ms (60s) -- a documented assumption, not calibrated against real production order-placement/cancel-replace telemetry. Longer than `fill_model.py`'s own 5s unit-test default, chosen so passive orders get a realistic chance to trade through instead of trivially expiring almost every time. See Risks. |
| Signal source | Identical to Sprint 8/9: `generate_pair_signal_intents`, unchanged, same causal walk-forward test windows |
| Fill source | Same real, checksum-verified level-1 top-of-book quotes as Sprint 9 (`data/futures/um/daily/bookTicker/`, June 2023), re-downloaded for this session to `D:/CryptoPairTrading/cost_pilot_raw` (machine-local, gitignored, not committed -- same 330 symbol-days re-verified against the original checksums, not new data) |
| Latency / ACK_UNKNOWN / reconciliation | Unchanged from Sprint 9: 250ms latency, 2% ACK_UNKNOWN rate (deterministic per order_id, identical between both styles since the hash key is the same), 2,000ms reconciliation latency |
| Holding period | 1 hour, unchanged |
| Universe | The same 13 Sprint 8 backtest-approved pairs as Sprint 9 |
| Baseline reproduction check | `MARKET_IOC` rerun through the new `ExecutionStyle`-aware code compared against `sprint9_replay_results.json`: **PASS**, all deltas 0 |

Source: `src/backtest/fill_model.py` (`simulate_limit_fill` gained an
optional `reference_price` for slippage-metric consistency with
`MARKET_IOC` -- fixes a P3 QA finding from Sprint 9 review where
`slippage_bps` was hardcoded to `0.0` regardless of reference price),
`src/backtest/execution_simulator.py` (new `ExecutionStyle` enum and
per-leg dispatch), `src/backtest/replay_engine.py`
(`ReplayConfig.execution_style`), `scripts/run_sprint10_passive_execution_variant.py`.

## Results

Aggregate
(`data/research/binance_public/cost_pilot/sprint10_passive_execution_variant_results.json`):

| Metric | MARKET_IOC (baseline) | LIMIT_MAKER_TTL (passive) | Delta |
|---|---:|---:|---:|
| Pairs evaluated | 13 | 13 | 0 |
| Pairs realistic-net-positive | **0** | **0** | 0 |
| Total signals | 247 | 247 | 0 |
| Total executed trades | 239 | 230 | -9 |
| Total net PnL (quote) | -$2,266.27 | **-$2,005.91** | **+$260.35** |
| Total leg-fill-mismatch trades | 70 | 65 | -5 |
| Total unclosed residual quantity (units) | 11,470.92 | **14,565.31** | **+3,094.39 (+27%)** |
| Total entry legs EXPIRED (unfilled within TTL) | 0 (impossible by construction) | 65 | +65 |
| Total exit legs EXPIRED (unfilled within TTL) | 0 (impossible by construction) | 36 | +36 |
| `portfolio_gate_pass` | false | **false** | unchanged |

Per-pair comparison
(`data/research/binance_public/cost_pilot/sprint10_passive_execution_variant_pair_results.csv`):

| Pair | MARKET_IOC net PnL (quote) | LIMIT_MAKER_TTL net PnL (quote) | Delta | Entry EXPIRED (passive) | Exit EXPIRED (passive) | Residual delta |
|---|---:|---:|---:|---:|---:|---:|
| ARBUSDT/OPUSDT | -194.59 | -166.10 | +28.49 | 3 | 3 | -450.50 |
| ARBUSDT/ETHUSDT | -166.82 | -101.36 | +65.46 | 3 | 3 | +679.15 |
| ETCUSDT/ETHUSDT | -267.82 | -322.69 | **-54.87** | 6 | 1 | -166.76 |
| ARBUSDT/DOTUSDT | -188.67 | -159.51 | +29.16 | 6 | 5 | +1,579.51 |
| ARBUSDT/LINKUSDT | -194.23 | -134.33 | +59.90 | 5 | 5 | +2,497.12 |
| ARBUSDT/AVAXUSDT | -199.29 | -161.29 | +38.00 | 6 | 2 | -364.62 |
| AVAXUSDT/SOLUSDT | -128.66 | -82.23 | +46.43 | 4 | 4 | +222.51 |
| DOGEUSDT/ETCUSDT | -218.78 | -208.12 | +10.66 | 9 | 0 | -212.73 |
| AVAXUSDT/ETHUSDT | -134.46 | -118.84 | +15.62 | 4 | 2 | -44.75 |
| DOGEUSDT/ETHUSDT | -138.84 | -101.60 | +37.24 | 3 | 1 | +0.68 |
| ETHUSDT/OPUSDT | -111.60 | -86.99 | +24.61 | 2 | 2 | -415.09 |
| ETCUSDT/LTCUSDT | -169.91 | -248.66 | **-78.75** | 7 | 2 | -166.00 |
| ETHUSDT/UNIUSDT | -152.59 | -114.20 | +38.39 | 7 | 6 | -64.12 |

11 of 13 pairs improve (less negative) under passive execution; 2 pairs
(`ETCUSDT/ETHUSDT`, `ETCUSDT/LTCUSDT`, both involving ETCUSDT) get
measurably worse. Residual-exposure direction is even less uniform: 8 pairs
reduce their unclosed residual quantity under the passive style (in three
cases, `ETHUSDT/OPUSDT`, `DOGEUSDT/ETCUSDT`, `ARBUSDT/OPUSDT`, by hundreds
to low thousands of units), while `ARBUSDT/LINKUSDT` and `ARBUSDT/DOTUSDT`
alone add +2,497 and +1,580 units respectively -- most of the portfolio's
net +3,094 residual increase comes from these two ARBUSDT-heavy pairs.

## Analysis

- **The improvement is real but small relative to the gap.** $260.35 closes
  about 11.5% of the -$2,266.27 gap to breakeven. Even the single most
  improved pair (`ARBUSDT/ETHUSDT`, +$65.46) is nowhere near flipping to
  positive (-$101.36 remains deeply negative). This is consistent with
  Sprint 9's own diagnosis: gross edge per trade (Sprint 8's idealized
  10-30bps) is small relative to the total round-trip cost of 4
  spread-crossings (2 legs × entry+exit); removing some of that cost via
  passive quoting narrows the gap but does not close it.
- **Passive execution trades fill-cost for fill-*probability*.** 65 of the
  247×2=494 entry-leg attempts (about 13%) and 36 exit-leg attempts expired
  unfilled within 60 seconds -- a failure mode that is structurally
  impossible for `MARKET_IOC` (which always gets whatever level-1 liquidity
  exists at execution time, even if partial). This is exactly the roadmap's
  "maker não preenchido" (maker not filled) scenario the Sprint 9 report
  flagged as never having been tested in the real runner; it is now tested
  and quantified.
- **Naked-leg residual risk does not uniformly improve.** The Sprint 9
  report flagged unclosed residual exposure as a first-class risk requiring
  a future Hedge Engine/Barrier Manager/Emergency Exit before any
  real-capital promotion. This report shows that risk is *not* automatically
  reduced by using passive execution -- it went up 27% in aggregate, driven
  by a small number of pairs where an entry leg filled (crossed) but the
  paired exit leg then expired unfilled, leaving a real open position for
  longer than the aggressive style would have.
- **Two pairs get worse under passive execution.** `ETCUSDT/ETHUSDT` and
  `ETCUSDT/LTCUSDT` (both involving ETCUSDT) lose more money passively than
  aggressively. A plausible explanation, not confirmed by further analysis
  here (out of scope for this bounded check): ETCUSDT may have wider or
  less persistent spreads such that resting orders miss favorable moves
  more often than they capture the spread. This is reported descriptively,
  not as a causal claim requiring a new signal-side investigation.

## Risks

- **`limit_ttl_ms=60,000` is a documented assumption, not a measurement.**
  No real production order-placement/cancel-replace telemetry exists to
  calibrate how long a passive order should realistically rest before being
  canceled and replaced. A shorter TTL would show more EXPIRED outcomes and
  likely a smaller (or reversed) PnL improvement; a longer TTL would show
  fewer EXPIRED outcomes but exposes the strategy to more adverse-selection
  risk (the order sits resting through more market movement before either
  filling or expiring). This mirrors the same caveat already logged for
  Sprint 9's 250ms latency and 2% ACK_UNKNOWN rate.
- **Unclosed residual exposure is still not marked to market.** As in
  Sprint 9, the reported net PnL only reflects quantity that actually
  closed; the residual (now larger in aggregate under the passive style)
  is neither realized nor valued. This report's finding that residual
  exposure increased under the passive style makes this risk *more*
  relevant to Sprint 10's eventual Execution Risk Gate work, not less.
- **This does not test adverse selection or opportunity cost directly.**
  A passive order that fills is, by construction, filled exactly when the
  market moves through its resting price -- which can itself be a sign of
  adverse price movement immediately afterward. This report does not
  attempt to model or quantify that effect (it would require a dedicated,
  pre-registered follow-up with its own methodology); it only reports the
  fill/expire/PnL outcomes actually observed.
- **The 60-second TTL is a single configuration, not a swept parameter.**
  No optimization or parameter search was run over TTL, latency, or
  ack_unknown_rate combinations. Per this project's research discipline
  (see ADR-0010's Signal Iteration 1 closure), this report treats the
  single documented configuration as the object of inquiry and does not
  retroactively search for a more favorable TTL.
- **This report is scoped to June 2023 and the same 13 pairs Sprint 8/9
  approved.** It inherits every limitation already logged for that window
  in `reports/sprint_08_backtest.md`, `reports/backtest_executable_v1.md`,
  and `reports/research_sprint_07.md`.

## Conclusion

Technical implementation: complete. `ExecutionStyle` (`MARKET_IOC` /
`LIMIT_MAKER_TTL`) is implemented in `src/backtest/execution_simulator.py`,
propagated through `src/backtest/replay_engine.py`, and exercised by
`scripts/run_sprint10_passive_execution_variant.py`. The MARKET_IOC path is
confirmed byte-for-byte equivalent to Sprint 9 (baseline reproduction check:
PASS). 324 tests pass (full suite), ruff clean.

**Gate for "PnL líquido positivo em cenário conservador": still NAO PASSA.**
0 of 13 pairs are net-positive under `LIMIT_MAKER_TTL`, exactly as under
`MARKET_IOC`. Passive execution measurably reduces cost (portfolio net PnL
improves by $260.35, about 11.5%) but the improvement is far short of
closing the gap to breakeven for any pair, and it introduces a new,
quantified failure mode (entry/exit legs expiring unfilled) and *increases*
aggregate unclosed residual exposure by 27%.

This closes the specific question Sprint 9 left open: the 0/13 result is
**not** simply an artifact of testing only the most expensive execution
style. Under the second execution style tested (passive/maker), the same
13-pair universe still shows no net-positive pair. Per ADR-0011, this does
not change gate policy -- it answers the narrower question the
Execution/Risk Agent asked, without promoting any pair to paper/live
trading and without claiming the underlying statistical edge has been
proven to be exactly zero under every conceivable execution style (e.g.
untested: continuous requoting/cancel-replace strategies, different TTLs,
depth-aware sizing). Any further execution-style iteration, or a decision
to proceed to the full Execution Risk Gate scope despite this result, is a
separate, explicit decision for the user.
