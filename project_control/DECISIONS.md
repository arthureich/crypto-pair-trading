# DECISIONS

Use this file as a simplified ADR log. Any interface, state machine, ledger schema, risk gate, sizing, live mode, leverage, or dead man switch policy change requires an ADR.

## ADR Template

```markdown
# ADR-XXX - Title

## Status
Proposed / Accepted / Rejected / Superseded

## Context
What problem are we solving?

## Decision
What was decided?

## Consequences
What improves?
What gets worse?
What must change?

## Agent Impact
- agent 1
- agent 2

## Migration
How should the system be updated?
```

## ADR-0001 - Control Files Are Source of Truth

## Status

Accepted

## Context

Multiple agents need a shared project memory that does not depend on conversation history.

## Decision

`project_control/` is the operational source of truth. Conversation history is not source of truth.

## Consequences

Every completed task updates `TASK_BOARD.md` and `HANDOFFS.md`. Architecture changes update `DECISIONS.md`. New tests or scenarios update `TEST_MATRIX.md`. Blockers update `BLOCKERS.md`.

## Agent Impact

- PM Agent
- Documentation Agent
- All specialized agents

## Migration

All agents must start by reading `PROJECT_STATE.md`, `CURRENT_SPRINT.md`, `TASK_BOARD.md`, assigned task files, and relevant contracts.

## ADR-0002 - Safety Before Edge

## Status

Accepted

## Context

The system can lose real money if execution, ledger, recovery, or risk controls are unsafe.

## Decision

The project proves operational safety before proving edge, and proves edge before scaling risk.

## Consequences

No real order execution implementation before specification and ledger/recovery foundations. No leverage, Cross Margin, Kelly sizing, or live multi-exchange behavior in MVP.

## Agent Impact

- PM Agent
- Execution / Risk Agent
- Ledger Agent
- ML Agent
- Quant Research Agent

## Migration

All sprint gates must preserve this order: safety, edge, small live, scale.

## ADR-0003 - Plane Separation

## Status

Accepted

## Context

Signal, execution, ledger, market data, ML, and recovery responsibilities must not collapse into one unsafe pipeline.

## Decision

Responsibilities remain separated by explicit interfaces.

## Consequences

SignalIntent is advisory only. Execution owns order lifecycle and deterministic exits. Ledger owns transactional truth. ML never controls emergency or reconciliation logic.

## Agent Impact

- Architect Agent
- Signal-related agents
- Execution / Risk Agent
- Ledger Agent
- ML Agent

## Migration

All interface changes must be added to `INTERFACES.md` and reviewed through ADR when they affect contracts.

## ADR-0004 - ML and Recovery Component Status

## Status

Accepted

## Context

The architecture needs ML and Recovery as explicit components without making them independent order-sending planes.

## Decision

ML and Recovery are first-class components with explicit interfaces, but they are not independent order-sending planes in the MVP.

## Consequences

ML is advisory to Signal only. Recovery is safety-critical and may block entries, reconcile, enter safe mode, and coordinate risk reduction. Recovery cannot create new strategy entries. External Dead Man Switch remains independent from the main process.

## Agent Impact

- Architect Agent
- ML Agent
- Ledger Agent
- Execution / Risk Agent
- DevOps / Observability Agent

## Migration

Architecture and interfaces must distinguish planes from safety/advisory components.

## ADR-0005 - Control File Format Normalization

## Status

Accepted

## Context

The PM operating instructions require specific templates for `PROJECT_STATE.md`, `CURRENT_SPRINT.md`, `TASK_BOARD.md`, `OWNERSHIP.md`, `INTERFACES.md`, `DECISIONS.md`, `HANDOFFS.md`, and `TEST_MATRIX.md`.

## Decision

Normalize control files to the required PM templates while preserving Sprint 1 technical content.

## Consequences

Agents can onboard from files without reading conversation history. `INTERFACES.md` now carries versioned contract skeletons.

## Agent Impact

- PM Agent
- Architect Agent
- Ledger Agent
- Execution / Risk Agent
- QA / Chaos Testing Agent
- Documentation Agent

## Migration

Future task files and handoffs should follow the normalized templates.

## ADR-0006 - Durable Event Contracts Before Exchange Side Effects

## Status

Accepted

## Context

Order lifecycle ambiguity can create duplicate sends, duplicate fills, unsafe retries, and unclear recovery after process crashes or exchange uncertainty.

## Decision

P0 lifecycle and audit events are specified in `docs/event_contracts.md`. Every exchange-facing order path must persist `ORDER_INTENT_CREATED` and `ORDER_SENT` before the exchange side effect. `ORDER_SENT` is a durable pre-side-effect send attempt, not exchange confirmation. `clientOrderId` values must be deterministic, versioned, stable after restart, and unique by venue/account/strategy/trade/leg/phase/symbol/attempt or slice. Fill reconciliation uses cumulative exchange `executedQty` and applies only `delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)`.

## Consequences

Ledger can recover order truth from persisted events after restart. `ACK_UNKNOWN` blocks blind retry and resolves only through reconciliation by `clientOrderId`, exchange order id, and cumulative fills. Same-leg slicing is blocked while a previous slice is uncertain. Recovery, safe-mode, risk-reducing, and kill-switch actions now have audit event contracts.

## Agent Impact

- Ledger Agent
- Execution / Risk Agent
- Architect Agent
- QA / Chaos Testing Agent
- DevOps / Observability Agent

## Migration

Implementation tasks must derive Ledger schema, order router behavior, recovery boot, and documentation checks from `docs/event_contracts.md`. Any future contract-breaking event or `clientOrderId` change requires a new ADR and migration plan.

## ADR-0007 - Cost-Gated PASS Scoped To Verified Evidence, Not The Full Backtest Window

## Status

Accepted

## Context

TASK-007-10 proved that Binance Public Data does not publish verified
top-of-book/L2 (`bookTicker`) archives for USD-M futures symbols past
approximately 2024-04. Only 11 of the 36 months in the Sprint 7 research
window (2023-06 through 2026-05) have any verified top-of-book coverage, for
every symbol. This was independently confirmed against the live source (not a
pagination artifact) and re-verified by QA Agent. The original Sprint 7 gate
policy required verified cost evidence across the *entire* backtest window
before any pair could be cost-gated PASS, which is now known to be
unsatisfiable from this source, permanently.

Separately, downloading and normalizing full-month `bookTicker` archives at
monthly granularity is itself unsafe: a single mid-cap symbol's monthly
archive decompresses into multiple GB of tick data, and loading it in one
pandas frame caused an out-of-memory kill in this environment (30 GiB RAM).

## Decision

1. Cost-gated PASS claims are scoped to the specific symbols, dates, and
   granularity for which verified top-of-book evidence was actually
   downloaded, checksum-verified, and aggregated — never to the full 36-month
   window by default. A pair's cost-gated status must always cite the exact
   evidence window it was evaluated against.
2. Historical top-of-book ingestion uses Binance **daily** `bookTicker`
   archives, processed one symbol-day at a time, with the raw tick-level
   frame freed before moving to the next symbol-day. Monthly `bookTicker`
   archives must not be loaded whole into memory.
3. Going forward, once any paper or live trading exists, the already-built
   Market Data Plane (`LocalOrderBook`/`BookBuilder`, `BookFeatures` with
   `spread_bps`/`depth_5bps`/`depth_10bps`, Sprint 5/6) is the source of truth
   for forward execution-cost evidence. Sprint 8 work that depends on cost
   evidence should prefer live-captured `BookFeatures` history over
   attempting to backfill more historical Binance archives.
4. Sprint 8 may open scoped only to work items that either (a) depend on
   pairs with real verified cost-gated evidence for the specific evidence
   window covered, or (b) do not require historical execution-cost evidence
   at all. Claims beyond the verified evidence window remain statistical-only
   and must be labeled as such.

## Consequences

Sprint 7's cost-gated conclusion is now precise instead of blocked-in-full:
some pairs may get a genuine, narrowly-scoped cost-gated PASS/FAIL for the
period actually verified (for example one representative month within
2023-06 through 2024-04), while the claim for the remaining, unverifiable
portion of the 36-month window stays statistical-only. `PROJECT_STATE.md`,
`CURRENT_SPRINT.md`, and `reports/research_sprint_07.md` must state the
evidence window explicitly whenever `cost_gated_pass` is reported.

## Agent Impact

- PM Agent
- Market Data Agent
- Quant Research Agent
- QA / Chaos Testing Agent

## Migration

`src/research/execution_cost_evidence.py` and
`scripts/run_sprint7_execution_cost_download.py` implement the daily,
memory-bounded ingestion path. Any future cost-gated claim must record the
evidence window (symbols, dates, granularity) alongside `cost_gated_pass` and
must not silently imply full-window coverage.

## Addendum 2026-07-02

The June-2023 evidence scope was expanded from the initial 6-symbol pilot to
all 15 symbols that appear in the 41 Sprint 7 statistical candidate pairs.
The runner was hardened to stream-read daily ZIP members before processing
BTCUSDT/ETHUSDT. The expanded run verified 450 daily Binance bookTicker ZIPs
and .CHECKSUM files (17.98GB compressed), produced 10800 deduplicated hourly
cost rows, and ran the cost gate for all 41 candidate pairs.

Result: 31 pairs are cost-gated PASS for June 2023 only; 10 pairs fail, all
containing ADAUSDT, because ADAUSDT fails the symbol-level spread gate
(`WIDE_MEDIAN_SPREAD`, median spread 3.52bps > 3.0bps). This addendum does
not change the ADR rule: the PASS remains scoped to the exact June-2023
evidence window and does not imply full-window validation.

## ADR-0008 - Adopt External Master Roadmap; Reconcile Sprint Numbering

## Status

Accepted

## Context

The user provided the full 28-sprint master roadmap for this project on
2026-07-02 (now stored verbatim in `project_control/ROADMAP.md`). This
roadmap predates and supersedes the ad hoc sprint definitions this project
had been improvising sprint-by-sprint. Comparing it against what was actually
built exposes a numbering and scope mismatch:

- Roadmap Sprint 7 ("Research base: pair selection, Kalman e OU") matches
  what this project built and closed as Sprint 7. No discrepancy there.
- Roadmap Sprint 8 ("Triple Barrier direcional e backtest estatistico") calls
  for a directional triple-barrier exit (separate profit/stop conditions for
  long vs short spread), a candle-based statistical backtest with
  conservative fixed fee/funding/slippage assumptions, and Sharpe/Sortino/
  profit-factor metrics gated at profit factor > 1.10.
- What this project actually built and closed as "Sprint 8" ("Backtest
  walk-forward cost-aware") is a different, hybrid design: a fixed 1-hour
  holding period (not a triple barrier), real verified June-2023 top-of-book
  cost evidence (more rigorous than the roadmap's conservative-estimate
  assumption), a causal walk-forward split, and per-pair net-PnL/hit-rate/
  drawdown metrics (no Sharpe/Sortino/profit-factor). It does not implement
  triple-barrier direction-aware exits at all.

## Decision

1. `project_control/ROADMAP.md` is now the authoritative source of truth for
   sprint sequencing, objectives, and gates. Every future `CURRENT_SPRINT.md`
   must trace back to it.
2. The already-completed "Sprint 8" (walk-forward cost-aware backtest, gate
   PASSA scoped to 13 pairs) is accepted as valid, real technical work and is
   NOT redone or reverted. It is recorded as a documented deviation from the
   roadmap's canonical Sprint 8, not a silent substitution: the roadmap's
   Sprint 8 requirements (directional triple barrier, Sharpe/Sortino/profit
   factor) remain **outstanding technical debt**, tracked in
   `project_control/RISKS.md`, to be picked up explicitly later rather than
   skipped permanently.
3. Per explicit user instruction, the project proceeds directly to the
   roadmap's Sprint 9 ("Backtest executavel com simulacao de ordens"), using
   the 13 backtest-approved pairs and the already-downloaded, checksum-verified
   raw June-2023 tick-level bookTicker archives
   (`data/research/binance_public/cost_pilot/raw/`) as its input. Sprint 9's
   fill/execution realism work does not depend on the roadmap's Sprint 8
   triple-barrier gap being closed first, since it targets a different axis
   (execution realism vs. exit-strategy sophistication) and reuses the same
   signals already generated and reviewed in the completed Sprint 8.
4. From Sprint 9 onward, sprint numbers in `CURRENT_SPRINT.md`/
   `TASK_BOARD.md`/`tasks/` follow `ROADMAP.md` numbering exactly. No further
   ad hoc sprint content is invented without checking `ROADMAP.md` first.

## Consequences

The roadmap's canonical Sprint 8 scope (triple barrier, profit factor gate)
is not lost -- it is explicitly logged as deferred technical debt rather than
silently dropped. Sprint 9 can start immediately since it does not strictly
require the triple-barrier exit to exist first (it can be layered on top of
Sprint 9's execution simulator later). Future PM sessions must read
`ROADMAP.md` before opening any new sprint.

## Agent Impact

- PM Agent
- Backtest Agent
- Documentation Agent

## Migration

Add "Sprint 8 canonical gap: directional triple barrier + Sharpe/Sortino/
profit-factor metrics" to `project_control/RISKS.md` as open technical debt.
Any future sprint that revisits exit-strategy sophistication should close
this gap explicitly and reference this ADR.

## ADR-0009 - Retroactively Build Canonical Sprint 8 (Triple Barrier + Statistical Backtest)

## Status

Accepted

## Context

ADR-0008 logged the roadmap's canonical Sprint 8 ("Triple Barrier direcional
e backtest estatistico") as deferred technical debt after the project
proceeded directly to Sprint 9 by explicit user instruction. The user has now
asked to go back and build it properly, noting that `project_control/ROADMAP.md`
was only made available to the PM in the Sprint 8/9 session -- prior sessions
that built the non-canonical "Sprint 8" (walk-forward cost-aware) never had
this document and could not have followed it.

## Decision

1. Build the roadmap's canonical Sprint 8 deliverables now, as a distinct,
   separately tracked body of work (`tasks/sprint_08_canonical/`,
   `TASK-008C-*` in `TASK_BOARD.md`) rather than overwriting or renumbering
   the already-closed non-canonical Sprint 8 (whose real, reviewed
   walk-forward/Sprint 9 chain of work stands on its own and is not reverted).
2. Universe: all 41 Sprint 7 statistical candidate pairs
   (`sprint7_binance_usdm_202306_202605_research_gate.json`), not the
   cost-gated 31 or backtest-approved 13 -- the roadmap's Sprint 8 sits
   between Sprint 7 (research) and the expensive real-cost-evidence work this
   project added beyond the roadmap (ADR-0007), so it is evaluated on the
   full statistical universe with the roadmap's own conservative-fixed-cost
   assumption, not gated by data this sprint was never meant to depend on.
3. Cost model: exactly as the roadmap specifies -- "fees estimadas, funding
   estimado, slippage conservador fixo" -- not the real tick-level cost
   evidence from ADR-0007/Sprint 9. Funding uses the real, already-computed
   `funding_carry_bps_per_day` per pair (Sprint 7 output); fees/slippage use
   a single documented conservative fixed constant per leg round-trip,
   explicitly labeled as an assumption, not a measurement.
4. Exit logic: directional triple barrier in z-score space (profit barrier =
   reversion toward the OU mean, stop barrier = adverse z-score excursion
   beyond entry, vertical barrier = a multiple of the pair's OU half-life,
   capped). Barrier resolution scans forward through already-known historical
   bars after a causally-generated entry signal -- this is standard backtest
   label resolution, not look-ahead in the entry signal itself, and must be
   documented as such to avoid confusion with the project's no-look-ahead
   rules for signal generation.
5. Metrics: Sharpe, Sortino, max drawdown, profit factor, hit rate, avg
   win/loss, turnover, average time in trade -- all roadmap-specified,
   previously never implemented in this project.
6. Gate: profit factor >= 1.10 net of costs, per roadmap.

## Consequences

This does not replace or invalidate the non-canonical Sprint 8 or Sprint 9
work already done and reviewed; both remain valid, real, reviewed
engineering. Canonical Sprint 8 is additive: it answers the roadmap's
original question (does a simple, cheap, candle-level backtest with
conservative fixed costs show a profit-factor-positive edge) using a
different methodology than what Sprint 9 already tested (tick-level real
execution simulation). The two are complementary evidence, not duplicates.
If canonical Sprint 8's approved universe differs materially from the
13-pair Sprint 9 universe, that is expected (different filter) and does not
by itself invalidate either result.

## Agent Impact

- PM Agent
- Backtest Agent
- Quant Research Agent
- QA / Chaos Testing Agent

## Migration

Update `RISKS.md` to close the ADR-0008 technical-debt entry once this ADR's
deliverables are reviewed and merged. Update `TASK_BOARD.md`/`CURRENT_SPRINT.md`
with `TASK-008C-*` tasks distinct from the already-closed `TASK-008-*` series.

## ADR-0010 - Close Signal Iteration 1 as a Rejected Hypothesis

## Status

Accepted

## Context

Canonical Sprint 8 (ADR-0009) gated NAO PASSA for all 41 statistical pairs
(`reports/backtest_statistical.md`). Before opening Sprint 10 or abandoning
the mean-reversion signal family entirely, the user asked to iterate on the
signal itself first (this session), producing three sequential, formally
reviewed, pre-registered falsification tests:

1. **TASK-SIG-001** (diagnostic, no rerun): aggregate gross PnL is negative
   before any cost (-0.7673 bps/trade); `|z| >= 3.0` performs worse than
   `2.0-2.5`; the only strong ex-post cut was 2-4h resolved reversions.
2. **TASK-SIG-002** (causal exit-side test): capping the vertical exit at 4
   bars to force "fast reversion" trades makes gross PnL WORSE, not better --
   the 2-4h ex-post cut in TASK-SIG-001 was survivorship bias, not a causal
   edge. `STOP_FAST_REVERSION_PATH`.
3. **TASK-SIG-003** (causal entry-side test, two pre-registered runs): a
   `max_half_life_hours` entry gate is non-binding down to 12h (Run 1, a real
   methodology gap caught by Quant Research Agent review), and only becomes
   binding at 0.375h (Run 2), where gross profit factor exceeds 1.0 for the
   first time in the entire iteration (1.156) but net profit factor stays at
   0.833 and the qualifying sample is 74 trades across 3 pairs --
   underpowered by the task's own pre-registered `trade_count >= 200` bar.
   `STOP_SIGNAL_ITERATION`.

All three tasks reproduced their baselines exactly, applied literal
pre-registered decision rules (no ex-post cherry-picking), and passed
independent formal review (Quant Research Agent + QA / Chaos Testing Agent +
PM Agent), including at least one real P1 caught and fixed per task before
acceptance. This is a clean, convergent, three-times-independently-tested
negative result, not a single failed attempt.

## Decision

1. **Signal Iteration 1 is officially closed as a REJECTED HYPOTHESIS.** The
   Kalman/OU mean-reversion signal, as formulated (dynamic hedge ratio spread,
   causal rolling z-score entries, OU-half-life-driven triple-barrier exits),
   on this universe (41 Sprint 7 statistical pairs) and this dataset (1h
   candles, Binance USD-M futures, 2023-06 through 2026-05), shows no
   exploitable net edge via exit-side timing or entry-side half-life
   filtering. This is documented as a durable negative research result, not
   left as an open/pending iteration.
2. Sprint 10 (Execution Risk Gate) remains NOT opened by this decision alone;
   opening it is a separate decision for the user, independent of whether
   this signal family is abandoned or not.
3. One bounded, small-scope exploratory check is authorized as a final,
   non-repeating sanity pass before moving to the next research hypothesis:
   re-examine the 3 pairs and 74 trades from TASK-SIG-003 Run 2's tightest
   bucket (`max_half_life_hours=0.375`, ~22.5 minutes) using finer-grained
   (5-15 minute) bars, on the theory that hourly bars cannot reliably
   estimate or resolve reversions faster than the bar interval itself. This
   check is explicitly NOT a new optimization cycle: no parameter sweep, no
   new pre-registered decision rule beyond a plain "does gross/net edge
   replicate at finer granularity on this narrow slice," small universe (the
   3 pairs' underlying symbols only), and a bounded time window (not a
   3-year download). If it does not show consistent evidence, this signal
   family receives no further investment and effort moves to the next
   roadmap research hypothesis.

## Consequences

The three SIG tasks and their reports remain as permanent, citable evidence
of a real research dead end -- this is valuable output, not wasted work: it
prevents future sessions (or the live Execution Risk Gate work in Sprint 10)
from re-deriving or re-litigating the same conclusion. Whatever the
5-15-minute exploratory check finds, it does not reopen TASK-SIG-001/002/003;
it is a distinct, separately-scoped follow-up.

## Addendum 2026-07-03 - TASK-SIG-004 Executed

The bounded intrahour check was executed and closed. Scope was kept small:
8 symbols / 9 pairs that had any trade in TASK-SIG-003 Run 2's tightest
bucket, 2025-12 through 2026-05, Binance 5m klines, no full-universe
redownload. A review-found sub-hour vertical-barrier unit bug was corrected
with `bar_duration_hours` propagation before accepting the result.

Final result after correction: baseline 5m and tight 5m
(`max_half_life_hours=0.375`) were identical: 23,051 trades, gross profit
factor 1.1343, net profit factor 0.4223. The 1h motivating observation
(gross PF 1.1559, net PF 0.8327, n=74) does not become an exploitable net
edge at 5m. Decision is unchanged: no TASK-SIG-005, Signal Iteration 1
remains closed as a rejected hypothesis, and Sprint 10 is not opened by this
ADR.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent
- QA / Chaos Testing Agent

## Migration

Update `PROJECT_STATE.md` and `CURRENT_SPRINT.md` to reflect Signal
Iteration 1 as closed/rejected, not pending. Track the bounded intrahour
exploratory check as its own small task
(`tasks/signal_iteration/TASK-SIG-004-intrahour-sanity-check.md`), explicitly
scoped smaller than TASK-SIG-001/002/003 and not part of the same
pre-registered decision chain.
