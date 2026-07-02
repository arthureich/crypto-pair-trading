# Sprint 8 Backtest Report

Status: final report for Sprint 8 walk-forward cost-aware backtest.

Last updated: 2026-07-02.

Gate conclusion for Sprint 9: PASSA, SCOPED to 13 candidate pairs with genuine
positive net PnL after realistic round-trip execution cost and a causal,
no-look-ahead walk-forward evaluation, all inside the June 2023 verified
evidence window. The full 31-pair portfolio (equal-weighted, all pairs kept
open) is net negative and must not be presented as approved.

## Executive Summary

Sprint 8 built and ran an offline, cost-aware, walk-forward backtest over the
31 candidate pairs that passed the Sprint 7 real cost-gate for June 2023 (see
`project_control/SPRINT8_UNIVERSE.json` and `reports/research_sprint_07.md`).
The pipeline: freezes the cost-gated universe as a loadable, fail-closed
contract; builds causal walk-forward folds; generates offline `SignalIntent`
records from a causal rolling z-score on a sequential Kalman spread; and
simulates a 1-hour round-trip trade per signal with real, causal execution
cost applied on both entry and exit.

A first implementation pass was reviewed by Backtest Agent, Quant Research
Agent, Market Data Agent, and QA Agent in parallel and returned **three
blocking (P1) findings**, all of which would have overstated the strategy's
apparent edge:

1. **Beta-weighting mismatch** -- the entry signal came from a beta-weighted
   Kalman spread, but simulated PnL summed both legs' raw returns 1:1,
   pricing a different, uncontrolled exposure than the one that triggered
   the signal.
2. **Look-ahead in the mean-reversion/half-life gate** -- `estimate_ou` was
   fit once on each pair's entire 30-day spread series, so a regime that only
   became mean-reverting later in the month could "approve" signals earlier
   in the same month, before that regime existed.
3. **Missing exit cost** -- execution cost was charged only for opening the
   position, not for closing it one hour later, understating round-trip cost
   by roughly half.

All three were fixed (beta-weighted PnL; a strictly causal trailing-window
OU/half-life gate, replacing the full-sample fit; explicit entry+exit cost),
covered by new regression tests (including a test that appends 40 future bars
with a sharply different trend and asserts the signals generated inside the
original window are byte-for-byte unchanged), and independently re-confirmed
PASSA by a second review pass. The backtest was rerun after the fix.

**Corrected result**: 31 pairs evaluated, 622 trades total, **13 pairs
individually net-PnL-positive** after realistic cost, **18 rejected**. The
equal-weighted portfolio across all 31 pairs is net negative
(`total_net_pnl_bps = -1716.67`, `portfolio_net_pnl_quote = -$171.67` on
$1,000 notional per leg per trade). This is the expected direction for a
fail-closed correction: fixing look-ahead and cost understatement made the
result more conservative (13 approved instead of the pre-fix 17), not less.

## Universe And Evidence Scope

Frozen in `project_control/SPRINT8_UNIVERSE.json`, loaded and validated by
`src/research/sprint8.py::load_sprint8_universe_contract`:

- 31 approved pairs (cost-gated PASS for June 2023, no ADAUSDT).
- 10 blocked pairs (all contain ADAUSDT, rejected for `WIDE_MEDIAN_SPREAD`:
  median spread 3.52bps > 3.0bps threshold).
- Evidence scope: `2023-06` only. The contract fails closed
  (`Sprint8ContractError`) if evidence_scope, pair counts, or cost-gate status
  do not match exactly.
- Any pair outside the 31 approved raises `Sprint8ContractError` when passed
  to `assert_pair_cost_gated`, `generate_offline_signal_intent`,
  `generate_pair_signal_intents`, or `run_cost_aware_backtest`.

This scope inherits directly from the real, checksum-verified June-2023
bookTicker pilot documented in `reports/research_sprint_07.md`. It does not
extend coverage: the same 25-of-36-month gap in Binance Public Data bookTicker
coverage (2024-05 through 2026-05) still applies, and this report says nothing
about performance outside June 2023.

## Methodology

| Component | Definition |
|---|---|
| Signal | Causal rolling z-score (`rolling_zscore`, shifted, already no-look-ahead) on a sequential Kalman spread (`fit_kalman_filter`, causal by construction) |
| Entry threshold | `\|zscore\| >= 2.0` |
| Mean-reversion gate | OU fit on a trailing 168-bar (7-day) causal window ending at the candidate bar; requires `mean_reverting=True` and `half_life <= 240h`; also requires the Kalman beta to be stable (`unstable_points[index]` false) and positive at that index |
| Walk-forward | 2 folds, `train_bars=336`, `test_bars=168`, `step_bars=168`; only signals whose `created_at` falls inside a fold's test window are evaluated (`build_walk_forward_splits` enforces `train_end < test_start`) |
| Trade horizon | One 1-hour bar after signal creation; no stop-loss, no take-profit, no z-score-reversion exit -- a fixed, simple horizon for this first pass |
| Position sizing | `target_notional = $1,000` on leg A; leg B's return is weighted by `abs(beta)` from the same Kalman step that generated the signal, so gross PnL is measured on the same spread the entry threshold was measured on |
| Execution cost | Real June-2023 median top-of-book spread (bps) per symbol, looked up causally (`cost_available_time <= created_at`) at both the entry bar and the exit bar, summed per leg, summed across both legs |
| Rejection status | `BACKTEST_APPROVED` only if `trade_count > 0` and `net_pnl_bps > 0`; otherwise `REJECT_NO_SIGNALS` or `REJECT_NEGATIVE_NET_PNL` |

Source: `src/research/sprint8.py` (contract, splits, signal, backtest engine)
and `scripts/run_sprint8_backtest.py` (runner: gross-edge calculation,
walk-forward filtering, causal cost lookup, per-pair orchestration).

## Results

Aggregate (`data/research/binance_public/cost_pilot/sprint8_backtest_results.json`):

| Metric | Value |
|---|---:|
| Pairs evaluated | 31 |
| Pairs backtest-approved (net PnL > 0) | 13 |
| Pairs rejected | 18 |
| Total trades | 622 |
| Total gross PnL (bps, summed across all 31 pairs) | see pair CSV |
| Total cost (bps, summed across all 31 pairs) | 2366.07 |
| Total net PnL (bps, summed across all 31 pairs) | -1716.67 |
| Portfolio net PnL (quote, equal-weighted, all 31 pairs) | -$171.67 |
| `any_pair_backtest_approved` | true |
| `portfolio_gate_pass` (all 31 pairs, equal-weighted) | **false** |

These two summary flags are reported separately on purpose: `any_pair_backtest_approved`
answers "does at least one pair have a real edge after cost," which is true
and is the basis for scoping Sprint 9. `portfolio_gate_pass` answers "would an
equal-weighted book of all 31 candidates be profitable," which is false. Do
not collapse these into a single "Sprint 8 passed" statement.

Top 5 approved pairs by net PnL (bps):

| Pair | Trades | Gross bps | Cost bps | Net bps | Hit rate | Max drawdown (bps, per-pair) |
|---|---:|---:|---:|---:|---:|---:|
| ETCUSDT/LTCUSDT | 25 | 632.22 | 89.64 | 542.58 | 0.720 | 516.05 |
| ARBUSDT/AVAXUSDT | 18 | 516.41 | 59.82 | 456.59 | 0.722 | 276.35 |
| AVAXUSDT/ETHUSDT | 17 | 427.12 | 28.35 | 398.77 | 0.647 | 109.18 |
| ARBUSDT/OPUSDT | 20 | 397.86 | 65.99 | 331.87 | 0.700 | 170.95 |
| DOGEUSDT/ETHUSDT | 10 | 302.54 | 31.74 | 270.80 | 0.800 | 32.44 |

Bottom 5 rejected pairs by net PnL (bps):

| Pair | Trades | Gross bps | Cost bps | Net bps |
|---|---:|---:|---:|---:|
| AVAXUSDT/LINKUSDT | 19 | -339.57 | 96.94 | -436.51 |
| DOTUSDT/LINKUSDT | 18 | -305.01 | 142.91 | -447.92 |
| ARBUSDT/ETCUSDT | 21 | -398.45 | 64.20 | -462.65 |
| BTCUSDT/SOLUSDT | 21 | -460.59 | 27.56 | -488.15 |
| AVAXUSDT/ETCUSDT | 28 | -419.88 | 80.10 | -499.98 |

Full per-pair results:
`data/research/binance_public/cost_pilot/sprint8_backtest_pair_results.csv`.

### 13 backtest-approved pairs (Sprint 9 operational universe)

```text
ARBUSDT/OPUSDT
ARBUSDT/ETHUSDT
ETCUSDT/ETHUSDT
ARBUSDT/DOTUSDT
ARBUSDT/LINKUSDT
ARBUSDT/AVAXUSDT
AVAXUSDT/SOLUSDT
DOGEUSDT/ETCUSDT
AVAXUSDT/ETHUSDT
DOGEUSDT/ETHUSDT
ETHUSDT/OPUSDT
ETCUSDT/LTCUSDT
ETHUSDT/UNIUSDT
```

### 18 backtest-rejected pairs (statistical- and cost-gated PASS, but not backtest-approved)

```text
BTCUSDT/ETHUSDT
ARBUSDT/ETCUSDT
ETHUSDT/LINKUSDT
AVAXUSDT/DOTUSDT
DOTUSDT/ETCUSDT
ATOMUSDT/DOTUSDT
DOTUSDT/LINKUSDT
AVAXUSDT/LINKUSDT
ETCUSDT/LINKUSDT
ETCUSDT/OPUSDT
ETHUSDT/SOLUSDT
AVAXUSDT/ETCUSDT
DOTUSDT/ETHUSDT
ARBUSDT/ATOMUSDT
DOTUSDT/OPUSDT
DOGEUSDT/DOTUSDT
BTCUSDT/SOLUSDT
ATOMUSDT/ETCUSDT
```

These 18 pairs passed statistical research (Sprint 7) and the real cost gate
(Sprint 7/ADR-0007), but do not survive a causal, cost-aware 1-hour backtest
in June 2023. They remain statistical- and cost-gate-approved for research
purposes but must not be treated as backtest-approved.

## Verification

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 211 tests (14 Sprint 8 module tests, 6 Sprint 8 runner tests,
1 causal-safety regression test, plus all prior sprint suites).

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src scripts tests
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint8_backtest.py
Result: passed. 31 pairs evaluated, 622 trades, 13 approved, 18 rejected,
portfolio net PnL negative (see Results).
```

Reviews:

```text
Backtest Agent (first pass): MUDANCAS SOLICITADAS. P1 beta-weighting mismatch
(bloqueante); P2 gate_pass naming (misleading given negative portfolio); P3
max_drawdown_bps is per-pair only, not portfolio-level (documented above);
P3 fixed 1-hour exit horizon (documented as a known simplification).

Quant Research Agent (first pass): MUDANCAS SOLICITADAS. P1 OU/half-life gate
fit on the full sample instead of causally (bloqueante); confirmed Kalman
beta itself is causal; flagged the 13/31 (post-fix) approval rate as
plausible but conditioned on the P1 fix.

Market Data Agent (first pass): MUDANCAS SOLICITADAS. P1 missing exit cost
(bloqueante, understated round-trip cost by roughly half); P2 median-only
cost understates tail risk relative to p95/p99 (documented as a known
limitation, not fixed in this pass); confirmed causal cost join and correct
per-leg symbol normalization.

QA / Chaos Testing Agent (first pass): PASSA. Confirmed no-look-ahead in the
runner's gross-edge, walk-forward-window, and causal-cost-lookup functions by
manual line review; flagged (P2, non-blocking) that the runner itself had
zero automated test coverage before this pass.

Combined confirmation review (second pass, after fixes): PASSA. Independently
verified the beta-weighting direction against the Kalman spread definition,
confirmed the OU causal window never reads past the candidate index, judged
the new causal-safety regression test as a genuine (non-trivial) proof of
no-look-ahead, and confirmed the round-trip cost sums entry and exit without
leg mixups. One P3 (non-blocking): total_trades stayed at 622 before and
after the OU-gate fix; independently reproduced and explained (see Risks) --
not a residual bug.
```

## Risks

- The backtest evaluates a fixed 1-hour holding period with no stop-loss,
  take-profit, or z-score-reversion exit. Real execution would likely exit
  earlier or later depending on regime; this is a known simplification of
  this first pass, not a defect.
- Execution cost uses only the median hourly top-of-book spread, not p95/p99
  tail spread; in wider-spread hours the 13 approved pairs' true cost could
  be higher than modeled. A p95-based sensitivity re-run is a reasonable
  follow-up before allocating real capital.
- Cost evidence is verified bookTicker (best bid/ask only), not order-book
  depth or market-impact-adjusted cost for the traded notional
  ($1,000/leg here); larger size would face higher realized slippage than
  this report models.
- `total_trades=622` was numerically identical before and after fixing the
  look-ahead OU/half-life gate. This was independently investigated and
  explained: for these specific pairs, the full-sample half-life is very
  short (roughly 1-1.5 hours), so the pair is strongly mean-reverting
  throughout essentially the entire 30-day window, and the causal
  trailing-window OU fit agrees with the full-sample fit at nearly every
  index. This is a property of this dataset/month, not evidence the fix is a
  no-op -- the fix still changed net PnL materially (17 to 13 approved pairs)
  through the beta-weighting and exit-cost corrections. A month with a
  genuine mid-window regime change would show the OU-gate fix changing
  signal counts too; this one did not need to.
- `max_drawdown_bps` is computed per pair only; there is no combined,
  time-aligned portfolio drawdown metric across the 622 trades. Do not read
  the per-pair figures as a portfolio risk figure.
- This entire report is scoped to June 2023 and 31 specific pairs. It says
  nothing about performance in any other month, especially the 25 of 36
  months (2024-05 through 2026-05) with no verified top-of-book evidence at
  all (see `project_control/BLOCKERS.md`,
  `BLOCKER-2026-06-30-S7-REAL-DATASET-GATE`).
- 17GB of raw checksum-verified Binance archives remain preserved under
  `data/research/binance_public/cost_pilot/raw/` for audit purposes
  (TASK-008-08 cleanup is intentionally blocked pending explicit
  acceptance -- do not delete without a separate, explicit decision).

## Conclusion

Technical implementation: PASSA. The Sprint 8 universe contract, walk-forward
splits, offline signal generation, and cost-aware backtest are implemented,
reviewed by Backtest Agent, Quant Research Agent, Market Data Agent, and QA
Agent, and covered by 20 new automated tests (14 module tests + 6 runner
tests, including a dedicated causal-safety regression test). All three
blocking findings from the first review pass were fixed and independently
re-confirmed.

Sprint 9 gate: PASSA, SCOPED to the 13 backtest-approved pairs listed above,
for the June 2023 evidence window only. The 18 backtest-rejected pairs and
the 10 ADAUSDT-blocked pairs remain excluded from any operational universe.
The equal-weighted 31-pair portfolio is net negative and must never be cited
as a passing result -- only the 13-pair, cost-aware, walk-forward-validated
subset is.

Required before Sprint 9 uses these 13 pairs for anything beyond further
research: extend the verified cost-evidence and backtest window beyond a
single month (per ADR-0007's options: more real-download passes, an
alternative source, or live Market Data Plane capture), and decide whether a
fixed 1-hour exit is acceptable for the next phase or needs a proper barrier
policy (already specified for live use in `docs/architecture.md`'s
`BarrierPolicy` contract, not yet wired into this offline backtest).
