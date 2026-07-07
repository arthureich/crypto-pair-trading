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

## ADR-0011 - Open Sprint 10 Scoped To A Passive/Maker Execution Variant

## Status

Accepted

## Context

Signal Iteration 1 is closed as a rejected hypothesis (ADR-0010) and Sprint
10 (Execution Risk Gate, per `project_control/ROADMAP.md`) remained
deliberately NOT opened, pending an explicit user decision. `reports/
backtest_executable_v1.md` documents that the Sprint 9 result (0/13 pairs
net-positive, portfolio -$2266.27) used MARKET_IOC (aggressive, spread-crossing)
execution on both legs of both entry and exit -- the most expensive execution
style tested, not the only one. The Execution/Risk Agent's explicit,
formally-reviewed recommendation was to test a passive/maker execution
variant (`simulate_limit_fill`, already implemented and unit-tested in
`src/backtest/fill_model.py`, but never wired into `execution_simulator.py`
or the real runner) before concluding the strategy has no exploitable edge.

The user has now made that decision explicitly: open Sprint 10, but scoped
narrowly to this one recommended test, not to the full roadmap Sprint 10
scope (a complete Execution Risk Gate) and not to any paper/live trading
work.

## Decision

1. Sprint 10 opens now, scoped to a single first block: "Passive/Maker
   Execution Variant + Execution Risk Gate preparation." The full roadmap
   Sprint 10 scope (a complete Execution Risk Gate with daily loss/drawdown
   thresholds, kill switch wiring, etc.) remains explicitly out of scope for
   this block and is not claimed as delivered.
2. `execution_simulator.py` gains an explicit `ExecutionStyle` choice
   (`MARKET_IOC`, matching Sprint 9 exactly, vs. `LIMIT_MAKER_TTL`, a
   resting order quoted at the touch -- best bid for a BUY, best ask for a
   SELL -- that never crosses the spread at placement and only fills if the
   market later crosses to it within the configured TTL). This reuses
   `simulate_limit_fill` (already implemented, tested, and reviewed in
   Sprint 9) instead of adding a new fill-simulation code path.
3. The comparison runs against the exact same 13 Sprint 8 backtest-approved
   pairs, the exact same causal signals, and the exact same checksum-verified
   June-2023 raw bookTicker data already used in Sprint 9 -- no new data is
   downloaded, and the 17GB raw archive under
   `data/research/binance_public/cost_pilot/raw/` is not touched or deleted
   (TASK-008-08 remains BLOCKED, unrelated to this decision).
4. This does not change gate policy. A passive-execution result that is
   still net-negative does not get relabeled as a pass; a result that turns
   net-positive does not, by itself, authorize paper/live promotion -- it
   only answers the narrower question of whether all-aggressive execution
   cost, specifically, is what destroyed the Sprint 9 result. Any promotion
   decision remains separate and explicit.

## Consequences

The project gets a direct answer to the open question left by Sprint 9
(Execution/Risk Agent's caveat) without reopening Signal Iteration 1 or
committing to the full, heavier Execution Risk Gate scope yet. If the
passive variant is still net-negative across the 13 pairs, that closes the
"was it just execution cost" question and strengthens (does not create) the
case that this signal family has no exploitable net edge under realistic
execution of any style tested so far. If it turns net-positive, that is a
narrow, real finding that would justify a separate, explicit follow-up
decision about the full Execution Risk Gate scope -- not an automatic green
light.

## Agent Impact

- PM Agent
- Backtest Agent
- Execution / Risk Agent
- QA / Chaos Testing Agent
- Documentation Agent

## Migration

Track this block as `TASK-010-01` through `TASK-010-06` in `TASK_BOARD.md`.
Update `CURRENT_SPRINT.md` to define Sprint 10's first block explicitly,
`PROJECT_STATE.md` to record the sprint as opened (scoped), and `RISKS.md`
to reflect the passive-execution risk row's resolution once the real run
completes.

## ADR-0012 - Pause Sprint 10 Execution Risk Gate; Pivot Away From Kalman/OU Mean-Reversion Signal Family

## Status

Accepted

## Context

Sprint 10 Block 1 (`reports/passive_execution_variant.md`, ADR-0011)
answered the specific question left open by Sprint 9: whether the 0/13
net-positive result was an artifact of testing only maximally aggressive
(`MARKET_IOC`) execution. It was not. Under `LIMIT_MAKER_TTL` (passive,
never crosses the spread at placement), the portfolio is still 0/13
net-positive; net PnL improves only $260.35 (~11.5%, still deeply
negative), and aggregate unclosed residual ("naked leg") exposure
*increases* 27% rather than decreasing. The user's own analysis of this
result: passive orders are filled disproportionately when the market moves
through the resting price against the position (adverse selection), and
when the spread genuinely reverts cleanly, price moves away from the limit
before it can fill -- so the passive style cannot durably capture the small
gross edge this signal has at a 1-hour holding horizon, on top of the
signal itself having already failed three independent causal falsification
tests (ADR-0010).

## Decision

1. The Kalman/OU mean-reversion pair-trading signal family (as formulated:
   dynamic hedge ratio spread, causal rolling z-score entries, OU-half-life
   exits, on this 1h-candle Binance USD-M universe) is now closed to further
   investment under **any** execution style tested (aggressive or passive).
   This is additive to, not a reopening of, ADR-0010's closure of Signal
   Iteration 1 -- ADR-0010 closed the signal on statistical/gross-edge
   grounds; this ADR closes it on execution-realism grounds as well, so both
   angles (does it have edge; can realistic execution capture that edge) are
   now answered negatively for this signal family.
2. The roadmap's Sprint 10 (Execution Risk Gate, full scope: daily loss/
   drawdown thresholds, kill switch, sizing) is **paused, not abandoned**.
   Building a full risk gate around a signal with no demonstrated edge under
   either execution style would validate the machinery, not the strategy --
   the gate would either reject ~100% of trade intentions or, worse, invite
   overfitting the sample to manufacture an apparent edge. The Execution
   Risk Gate resumes once a new signal candidate clears the same bar this
   one failed (net edge under at least one realistic execution style).
3. Research effort pivots to a new signal hypothesis, structurally
   different from short-horizon mean reversion, so that the same
   execution-realism lesson does not simply repeat. The specific next
   hypothesis (cross-sectional momentum vs. funding-rate carry/basis vs.
   intraday order-flow) is a separate, explicit decision -- not resolved by
   this ADR.
4. Infrastructure built in Sprints 1-6 and 9-10 (event-sourced ledger,
   idempotent order lifecycle, recovery/safe-mode, local order book,
   execution/slippage features, `fill_model.py`/`execution_simulator.py`/
   `replay_engine.py` with both `MARKET_IOC` and `LIMIT_MAKER_TTL`) is
   signal-agnostic and is not reverted, deprecated, or rebuilt. A new signal
   hypothesis re-enters at the Sprint 7 research stage (pair/asset
   selection, feature/edge estimation) and reuses this infrastructure
   unchanged for backtest execution realism once it has its own statistical
   validation.

## Consequences

Sprint 9/10's real, negative finding is preserved as a permanent, citable
result (like ADR-0010's SIG-001/002/003/004): a documented case where a
statistically plausible signal failed under two independently tested
execution styles, with the specific failure mode (adverse selection against
passive resting orders) identified, not just an unexplained negative
number. No sprint is renumbered; the roadmap's Sprint 10 slot is reused
once a new signal clears its own edge bar, rather than skipped or
relabeled. The project does not build paper/live trading, an Execution Risk
Gate, or any promotion path for a signal with no demonstrated edge.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent
- Execution / Risk Agent

## Migration

Update `PROJECT_STATE.md` and `CURRENT_SPRINT.md` to record Sprint 10's
full scope as paused (not the current workstream) and to open a new
research workstream once the user selects the next signal hypothesis.
`TASK_BOARD.md` gets no new tasks from this ADR alone -- the next hypothesis
gets its own `TASK-011-*` (or equivalent) series once chosen.

## ADR-0013 - Pivot To Funding-Rate Carry As The Next Signal Hypothesis

## Status

Accepted

## Context

Per ADR-0012, the Kalman/OU mean-reversion signal family is closed and the
user asked for a recommendation among three pivot candidates: cross-sectional
momentum, funding-rate stat-arb/basis, or intraday order-flow anomalies
(HFT timeframes). The recommendation was funding-rate carry, for two
reasons: (1) it is structurally different from short-horizon mean
reversion -- the edge source is a mechanical periodic payment (funding
settlement), not a price bet, so it is far less sensitive to the
bid-ask/latency/adverse-selection friction that specifically killed the
prior signal under both `MARKET_IOC` and `LIMIT_MAKER_TTL` (ADR-0011); (2) a
data audit (this session) found that **no new data acquisition is needed**:
`data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz`
already carries real, 100%-covered, hourly `funding_rate_asof` (causally
joined via `pd.merge_asof(..., direction="backward")` in
`historical_dataset.py::_merge_funding_asof`, so it reflects only the most
recently settled funding rate at or before each bar's close -- not a future
rate) plus `mark_close`/`index_close`/`premium_close` (the mark-vs-index
premium, Binance's actual funding-rate input) for all 20 Sprint 7 symbols,
2023-06 through 2026-05. `docs/historical_dataset.md`'s "Known Risks"
section had already flagged that "funding can dominate statistical mean
reversion even when price spread looks stationary" -- this ADR turns that
previously-a-risk observation into the primary signal.

The user confirmed this recommendation ("pode ir").

## Decision

1. Open a new research workstream, "Funding Carry Signal Iteration"
   (`tasks/funding_carry/`), structurally separate from the closed Signal
   Iteration 1 (ADR-0010) and from Sprint 10 (ADR-0011/0012).
2. `TASK-FUND-001` (this session): define and pre-register the exact
   hypothesis, universe, rebalance rule, cost model, and a binding
   falsification threshold *before* any backtest code is written or run --
   the same discipline that caught TASK-SIG-003 Run 1's non-binding grid.
   See `tasks/funding_carry/TASK-FUND-001-define-hypothesis.md` for the full
   specification. Summary: cross-sectional funding-rate carry -- at each
   real Binance funding settlement (~3x/day), rank the 20 symbols by
   `funding_rate_asof` and go short the K highest-funding symbols / long the
   K lowest-funding symbols, equal-notional, dollar-neutral, rebalanced
   every interval. Primary configuration K=5, net profit factor >= 1.10
   gate (matching the canonical Sprint 8 threshold for methodological
   consistency), pre-registered before TASK-FUND-002 runs.
3. `TASK-FUND-002` (queued, not started): implement the signal and a
   candle-level statistical backtest (reusing the conservative fixed-cost
   methodology already built for canonical Sprint 8,
   `src/backtest/statistical_backtest.py`'s cost-modeling pattern, not its
   triple-barrier exit logic, which does not apply to a periodic-rebalance
   carry strategy), run it for real on the full 2023-06/2026-05 window, and
   -- if the statistical result is promising -- test at least one realistic
   execution style (reusing `src/backtest/fill_model.py`/
   `execution_simulator.py`/`replay_engine.py`, all signal-agnostic per
   ADR-0012) for the verified June-2023 tick-data window only, mirroring the
   two-stage (statistical, then executable) rigor already applied to the
   prior signal family.
4. No new data download. No leverage, no paper/live trading, no ML/
   meta-labeling (still out of scope per `PROJECT_STATE.md`).

## Consequences

The project reuses its entire signal-agnostic infrastructure (ledger,
recovery, market data, execution simulator with both `MARKET_IOC` and
`LIMIT_MAKER_TTL`) and its already-downloaded, checksum-verified dataset
for a genuinely new hypothesis, without repeating the multi-hour real-data
acquisition work that Sprint 7 and Sprint 9/10 required. The same
pre-register-before-run discipline that governed Signal Iteration 1 applies
here from the start, rather than being retrofitted after an ungoverned
first attempt.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent
- QA / Chaos Testing Agent

## Migration

Add `TASK-FUND-001`/`TASK-FUND-002` to `TASK_BOARD.md`. Update
`CURRENT_SPRINT.md` and `PROJECT_STATE.md` to record the new workstream.
`TASK-FUND-002` requires explicit confirmation of the pre-registered rule
in `TASK-FUND-001` before it is marked READY to start.

## Addendum 2026-07-05 - Funding Carry Signal Iteration Closed: NAO PASSA Accepted As Final

`TASK-FUND-002` (fase 1, full rebalance every interval) found real,
positive gross edge (funding + a correlated price component) at every
tested K, but turnover cost (19,722.00 bps at K=5) more than doubled it,
producing a deeply negative net result (-10,729.82 bps). `TASK-FUND-003`
(fase 2, incremental rebalancing via a yield threshold reusing the
existing `cost_bps_per_leg_roundtrip` constant -- no new parameter, per
explicit user design approval) cut cost by 99.83% (to 33.60 bps at K=5)
and flipped net PnL positive (+5,620.99 bps), but net profit factor at the
pre-registered primary K=5 (1.0904) still fell 0.0096 short of the 1.10
gate, on a well-powered sample (3,287 resolved rebalances, 6.57x the
pre-registered 500-rebalance floor -- not an underpowered near-miss).
K=3 (descriptive-only) cleared the gate at 1.1356.

The user explicitly declined to open a new task testing an intermediate K
(e.g. K=4) or any other parameter adjustment aimed at closing the 0.0096
gap, on the grounds that doing so after seeing K=3/K=5/K=8's monotonic
result would be ex-post curve-fitting to this exact sample -- the same
discipline that governed ADR-0010's closure of Signal Iteration 1.

**Decision:** the Funding Carry Signal Iteration (`TASK-FUND-001/002/003`)
is closed with `NAO PASSA` as its final, accepted result. This is not
treated as a failed or incomplete investigation -- it is a complete,
convergent, honestly-reported negative result: the underlying carry
premium exists and is real (unlike Signal Iteration 1, where gross edge
itself was absent or statistically weak), the specific cost-reduction fix
(incremental rebalancing) worked exactly as designed, and the strategy
still does not clear this project's pre-existing risk/return bar at the
pre-registered configuration. Effort now moves to a new signal hypothesis
(see the next ADR for the specific choice); this closure does not reopen
or revisit `TASK-FUND-001/002/003`.

## Agent Impact (Addendum)

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration (Addendum)

Update `PROJECT_STATE.md`/`CURRENT_SPRINT.md`/`TASK_BOARD.md` to record
the Funding Carry Signal Iteration as closed. `reports/
funding_carry_backtest.md` and `reports/funding_carry_incremental_backtest.md`
remain as permanent, citable evidence, per the same convention as Signal
Iteration 1's reports.

## ADR-0014 - Open Research Family C (TSREV): Time-Series And Cross-Sectional Reversal

## Status

Accepted

## Context

Two prior research families are closed: mean-reversion pairs via Kalman/OU
(Signal Iteration 1, ADR-0010 -- gross edge itself was absent/too weak) and
funding-rate carry (ADR-0013 -- gross edge real but eaten by turnover
cost, and the incremental fix's near-miss was accepted as final, not
re-tuned). This session also ran several bounded exploratory diagnostics
(cross-sectional momentum 12h-7d, cross-sectional Z-score micro-reversion
1h-4h, time-series momentum/breakout 4h-24h via a Donchian+ATR trailing
stop) -- all aborted or gated NAO PASSA, documented in `reports/
zscore_diagnostic_tails.md`, `reports/tsmom_diagnostic.md`, and `reports/
tsmom_backtest_final.md`.

The user proposed a deliberate methodological reset: stop adding
sophistication (Kalman, ML, execution engineering) before establishing
whether a genuinely simple signal has ANY raw edge. Specifically: a
single-asset (time-series) or cross-sectional reversal signal based on
`z = r/sigma` (return standardized by realized volatility), tested with a
plain fixed-horizon entry/exit, no optimization, and -- critically -- a
single pre-registered PRIMARY hypothesis decided before implementation,
with all other horizon/family combinations explicitly descriptive-only.
This directly answers this project's own stated risk at this point in the
research program: after two rejected families, the danger is no longer
"finding a bad strategy," it is starting to adapt the research to
observed results.

## Decision

1. Open Research Family C: **TSREV (Time-Series/Cross-Sectional
   Reversal)**, tracked independently under `tasks/tsrev/` and `docs/
   pre_registers/TASK-TSREV-*.md`, with its own criteria and closure --
   it does not inherit metrics or conclusions from Signal Iteration 1 or
   Funding Carry.
2. Exactly ONE primary, decisive hypothesis, pre-registered in
   `docs/pre_registers/TASK-TSREV-001.md` before any code is written:
   **Family A (Time-Series Reversal), 24h horizon.** Chosen because this
   session's own prior exploratory diagnostic (`reports/
   tsmom_diagnostic.md`) already found negative trailing-vs-forward
   correlation at every tested window (4h-24h), strengthening at longer
   horizons, with unanimous agreement across all 20 symbols individually
   -- the strongest, most consistent prior evidence available for any
   cell in the proposed grid. This is chosen for its empirical prior, not
   because a full backtest of 24h TSREV specifically has already been run
   and looked promising.
3. All other cells -- Family A at 6h/12h/48h, and Family B (Cross-Sectional
   Reversal, decile-based, same underlying `z` signal) at 6h/12h/24h/48h
   -- are explicitly descriptive/exploratory only. Per the pre-registered
   rule (verbatim, per the user): *"Somente a hipótese primária pode
   fundamentar a continuidade dessa linha de pesquisa. Resultados das
   hipóteses secundárias serão tratados exclusivamente como evidência
   exploratória e poderão servir apenas para formular futuros
   pré-registros independentes, nunca para validar esta pesquisa."* They
   cannot promote a pair/strategy to paper/live, and cannot substitute for
   the primary cell's gate outcome under any circumstance, including a
   secondary cell outperforming the primary.
4. The gate is evaluated on a held-out out-of-sample period (2025-06
   through 2026-05, the final 12 months) only, not on the full sample or
   the in-sample development period (2023-06 through 2025-05). Success
   requires ALL of: net profit factor > 1.05, net PnL > 0, max drawdown
   <= an equal-weight buy-and-hold benchmark's max drawdown over the same
   OOS period, and >= 200 resolved trades (the same statistical-power
   floor already used in TASK-SIG-003). All four criteria and the OOS
   split boundary are fixed before implementation begins.
5. No parameter sweep on the primary cell (single z-score threshold of
   1.0, single fixed 24h holding period, single inverse-volatility sizing
   convention, single 6.0bps round-trip cost assumption -- reusing the
   project's most common conservative constant, not the 12.0bps
   taker-taker assumption used for TSMOM's breakout entries, since a
   mean-reversion limit-style entry is plausibly makeable).

## Consequences

This is the strictest anti-p-hacking structure applied so far in this
project: a single decisive cell chosen by prior evidence rather than by
looking at this test's own results, an explicit rule barring secondary
cells from ever overriding it, and a genuine held-out test period (not
just a pre-registered parameter, but a temporal split reserved from the
decision). If the primary cell also fails, this closes Research Family C
cleanly, the same way ADR-0010 and ADR-0013 closed the prior two --
without an eighth attempt at a "better" cell from the descriptive grid.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent
- QA / Chaos Testing Agent

## Migration

Add `TASK-TSREV-001` (definition, this ADR's criteria) and `TASK-TSREV-002`
(implementation + real run, primary + all descriptive cells) to
`TASK_BOARD.md`. Update `CURRENT_SPRINT.md` and `PROJECT_STATE.md`.

## ADR-0015 - Open Research Family D (Payoff Engineering): Distribution/Attribution Study, Phase 1

## Status

Accepted

## Context

Three signal families are now closed with a documented NAO PASSA
(mean-reversion pairs, ADR-0010; funding-rate carry, ADR-0013; TSMOM
breakout, this session; time-series/cross-sectional reversal, ADR-0014).
TSREV's primary cell result is qualitatively different from the other
closures: win rate was nearly identical in-sample vs out-of-sample
(52.71% vs 52.68%), yet net PnL flipped sign (-48,496.48 vs +7,690.14
bps). This means the directional information itself appears stable; what
varies is the distribution of trade outcomes (loss magnitude/clustering),
and that distribution is what fails the profit-factor and drawdown gate
criteria. The user's proposed reading: the project has moved from "does
directional edge exist" to "can a stable directional edge be turned into
a risk-adjusted return" -- a different question requiring a different
kind of work (studying the shape of existing outcomes) rather than a
fourth signal-search family (which would just repeat the same
"gross-edge-exists-but-thin-or-costly" pattern already seen three times)
or a premature pivot to order-flow/L2 (which would require new data
infrastructure this project does not have, at high cost, before knowing
whether it is even needed).

## Decision

1. Open Research Family D: **Payoff Engineering**. Phase 1 (this ADR) is a
   pure distribution/attribution STUDY, not a new signal or strategy: it
   analyzes the trades already produced by the pre-registered TSREV
   primary cell (Family A, 24h, out-of-sample) -- same trades, same
   config, no re-tuning, no new backtest methodology.
2. Phase 1 has no pass/fail gate and makes no strategy decision -- it is
   descriptive only, explicitly to avoid the multiple-comparisons/p-hacking
   risk a gated re-test would carry. Its purpose is to generate
   well-motivated, SPECIFIC hypotheses (e.g., "losses cluster in a
   particular volatility regime" or "one side of the book drives most of
   the drawdown") for a future, separately pre-registered Phase 2, not to
   retroactively fix TSREV's gate outcome.
3. Questions in scope for Phase 1: where the realized drawdown comes from
   (loss concentration/Pareto share), temporal clustering (regime-like
   effects across the OOS window), symbol clustering, LONG vs SHORT side
   asymmetry (motivated by the same asymmetry already found in this
   session's Z-score cross-sectional diagnostic), entry-volatility
   clustering, and -- data permitting, reusing already-normalized columns
   -- funding-rate and liquidity/volume clustering at entry.
4. Explicitly out of scope for Phase 1: position sizing changes, dynamic
   exits, volatility targeting, regime filters, or any other strategy
   modification. Those are Phase 2 candidates, contingent on what Phase 1
   finds, and require their own pre-registration if pursued.
5. Order-flow/L2 microstructure research remains deferred (not rejected)
   pending this cheaper, already-available-data study.

## Consequences

If Phase 1 finds a genuine, well-motivated cluster (e.g., losses
concentrated in a specific regime or symbol subset), it becomes the basis
for a Phase 2 pre-registration with its own success criteria -- consistent
with this project's standing discipline of diagnosing before formulating.
If Phase 1 finds no clear cluster (losses are diffuse, no regime/symbol/side
signature), that is also a valid, informative result: it would suggest the
payoff problem is closer to irreducible (a structural cost/tail-risk issue)
rather than a segmentation the strategy could route around.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-PAYOFF-001` to `TASK_BOARD.md`. Update `CURRENT_SPRINT.md` and
`PROJECT_STATE.md`. No new pre-registered gate -- report findings in
`reports/tsrev_payoff_attribution.md`.

## ADR-0016 - Pre-Register Payoff Engineering Phase 2 Now; Pause Execution Until Genuinely New Out-Of-Sample Data Exists

## Status

Accepted

## Context

Phase 1 (ADR-0015, `TASK-PAYOFF-001`) found four descriptive patterns in
the TSREV primary cell's out-of-sample trades: a strong SHORT>>LONG
asymmetry, BTCUSDT/ETHUSDT underperformance, month-level temporal
clustering, and a non-monotonic liquidity pattern. The user's own
proposed next step (Phase 2) requires validating these patterns on a
genuinely new out-of-sample period -- explicitly NOT the same
2025-06/2026-05 window that produced them, since re-testing on that
window would be circular data-mining, not confirmation.

The normalized dataset ends 2026-05-31; today is 2026-07-05. No data past
2026-05-31 exists anywhere in this repository for the full 20-symbol
universe. Three paths were presented to the user: (a) download real data
up to today now, accepting a small (~350-400 trade) new-OOS sample; (b)
wait for more real calendar time to accumulate a larger new-OOS sample;
(c) use an internal holdout split of the already-used OOS period (weaker
guarantee, partial contamination since the hypothesis was generated from
the full 12-month aggregate). The user chose (b): wait for genuinely new
data to accumulate before running anything.

Per this project's standing discipline (ADR-0010, TASK-FUND-001,
TASK-TSREV-001), the design of a test -- including which single
hypothesis is primary/decisive versus descriptive-only, and the exact
gate -- must be locked BEFORE the data needed to run it exists, not
decided later when results are already visible. The user explicitly
chose SHORT-only as the primary/decisive cell (strongest effect size,
independently replicated by an earlier Z-score cross-sectional
diagnostic this session) and >=500 new resolved trades as the
operational threshold before attempting execution (safety margin over
the original 200-trade gate floor, since SHORT-only trades are
historically ~46% of the total population).

## Decision

1. Pre-register `TASK-PAYOFF-002` now
   (`docs/pre_registers/TASK-PAYOFF-002.md`), fully specifying: primary
   hypothesis (SHORT-only filter on the exact TSREV Family A 24h cell),
   3 descriptive-only secondary cells (exclude BTC/ETH; causal 30-day
   trailing-return regime split; Q2 liquidity-quartile filter), the exact
   gate (same structure as TASK-TSREV-001: net PF>1.05 AND net PnL>0 AND
   max DD<=baseline AND resolved SHORT trade_count>=200), and a fresh
   buy-and-hold drawdown baseline recomputed on the new OOS window (never
   reusing the old window's 11,003.94bps figure).
2. Execution of `TASK-PAYOFF-002` is explicitly PAUSED, not abandoned,
   until the dataset is extended past 2026-05-31 with real data and the
   new period contains >=500 total resolved trades of the exact primary
   cell configuration (operational trigger only, not a gate criterion).
3. No new data download happens as part of this ADR. A future task will
   extend the normalized dataset when the trigger condition is worth
   checking; this ADR only locks the design so that decision is never
   made by looking at results first.
4. Order-flow/L2 microstructure research remains deferred, per ADR-0015 --
   this ADR does not change that.

## Consequences

If SHORT-only clears the gate on genuinely new data, it becomes a
candidate for a Phase 3 pre-registration (position sizing / exposure
scoping), still requiring its own new-data validation before any
paper/live promotion. If it fails, per ADR-0010's discipline this closes
Research Family D's SHORT-only line without retrying with adjusted
parameters, and the descriptive secondary cells become candidates for a
separately pre-registered `TASK-PAYOFF-003`, not an automatic next step.
Either way, classic statistical research on this dataset/signal-family
architecture will have been given a fair, disciplined chance before any
order-flow/microstructure pivot is considered.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-PAYOFF-002` to `TASK_BOARD.md` with status BLOCKED (data
trigger). Update `CURRENT_SPRINT.md`, `PROJECT_STATE.md`, `HANDOFFS.md`,
`RISKS.md` to record the pre-registration and the resume trigger. No
code, no backtest run, no report until the trigger condition is met.

## ADR-0017 - Open Research Family E (Cross-Sectional Factors): Replicate Documented Crypto Momentum Literature Before Inventing New Signals

## Status

Accepted

## Context

Every signal family tested so far (mean-reversion pairs, funding carry,
TSMOM breakout, TSREV) was formulated internally by this project's own
diagnostics, not derived from a specific published result. The user
proposed a different research posture: before inventing further, test
whether an effect already documented in the crypto factor literature
(cross-sectional momentum, cross-sectional mean reversion, residual
momentum, PCA statistical arbitrage, an ensemble) survives in this
project's actual universe (20 USD-M perpetual symbols), sample period
(2023-06/2026-05), and realistic cost assumptions. The user explicitly
framed this as "Research Family E," proposed as five separate tasks
(TASK-CS-001 through 005), each with its own pre-registration, primary
hypothesis, and gate -- mirroring this project's existing discipline, not
replacing it.

Two design questions needed to be locked before any code: (1) whether to
pre-register all five tasks now or sequence them one at a time, and (2)
for the first task (Cross-Sectional Momentum), exactly which published
formulation to replicate and whether to introduce walk-forward/purged
cross-validation as new methodology. The user chose, via explicit
question: sequence one task at a time (CS-001 now, CS-002-005 as planned
backlog, each requiring its own pre-registration before code); replicate
the crypto-specific weekly momentum formulation (Liu & Tsyvinski 2021,
JFE) rather than the classic equity 12-1 convention (too few
non-overlapping monthly observations in a 3-year, 20-symbol universe) or
a monthly crypto variant; and keep the same simple chronological
in-sample/out-of-sample split already proven in TASK-TSREV-001/
TASK-FUND-001, not introduce purged CV (which solves a fold-contamination
problem specific to hyperparameter/model selection across folds -- not
applicable to a single fixed, non-swept rule).

## Decision

1. Open Research Family E: **Cross-Sectional Factors**. Sequenced
   execution -- only `TASK-CS-001` (Cross-Sectional Momentum) is
   pre-registered and executed now. `TASK-CS-002` (Cross-Sectional Mean
   Reversion), `TASK-CS-003` (Residual Momentum), `TASK-CS-004` (PCA
   Statistical Arbitrage), `TASK-CS-005` (Ensemble) are recorded as
   planned backlog, not started, each requiring its own pre-registration
   before any code, written only after CS-001 closes.
2. `TASK-CS-001` pre-registers a faithful replication of weekly
   cross-sectional crypto momentum (Liu & Tsyvinski 2021 style): rank all
   20 symbols by raw (non-vol-normalized) trailing 168h return, long the
   top quintile (K=4), short the bottom quintile (K=4), equal-weighted,
   dollar-neutral, full rebalance every 168h, no skip-period. See
   `docs/pre_registers/TASK-CS-001.md` for the complete locked design
   (signal formula, cost, OOS split reused from TASK-TSREV-001, gate).
3. Validation methodology for CS-001 is the existing simple chronological
   in-sample/out-of-sample split, not walk-forward or purged CV --
   explicitly justified as unnecessary for a single fixed rule with no
   hyperparameter sweep. Walk-forward/purged CV remains a candidate for a
   FUTURE task that genuinely needs cross-fold model selection.
4. Gate: net profit factor > 1.10 (reusing the project's other
   cross-sectional-style precedent, Funding Carry / Sprint 8 canonical,
   not TSREV's 1.05 or TSMOM's 1.20, both justified for different
   strategy shapes) AND net PnL > 0 AND max drawdown <= buy-and-hold
   baseline (recomputed on the same OOS window already used by TSREV) AND
   resolved leg-level trade count >= 200.
5. Research Family D (Payoff Engineering Phase 2, ADR-0016) remains
   pre-registered but execution-blocked pending new OOS data, unaffected
   by this ADR -- both lines proceed independently, not in competition.

## Consequences

If CS-001 clears the gate, it becomes the first documented-literature
effect confirmed in this project's universe, a materially stronger result
than any internally-formulated hypothesis tested so far (four have failed
NAO PASSA), and would justify continuing Family E sequentially into
CS-002. If it fails, per this project's standing discipline the result is
final for this exact rule (no parameter re-tuning after seeing results)
and becomes one more piece of evidence -- alongside ADR-0010/0013/0014 --
that this universe/cost structure may not support directional
statistical edge at the depth tested. Either way, CS-002 onward are
opened only via their own separate ADR/pre-registration.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-CS-001` to `TASK_BOARD.md`. Update `CURRENT_SPRINT.md`,
`PROJECT_STATE.md`, `HANDOFFS.md`, `RISKS.md`. Implement
`src/research/cs_momentum.py`, `scripts/backtest_cs_momentum.py`,
`tests/test_cs_momentum.py`, run for real on the existing normalized
dataset (no new download), write `reports/cs_momentum_backtest_final.md`.

## ADR-0018 - Open TASK-CS-002 (Cross-Sectional Mean Reversion) At A Genuinely Distinct Horizon, Not A Deterministic Mirror Of CS-001

## Status

Accepted

## Context

Per the sequenced Research Family E plan (ADR-0017), CS-001 (weekly
cross-sectional momentum) closed NAO PASSA. The user's proposed roadmap:
run CS-002 (Cross-Sectional Mean Reversion) with the same rigor; if it
also fails, close the classic-price-factor research line entirely and
open a genuinely new category (not "Family F") -- Market
Microstructure/Alternative Data research (open interest, order flow,
liquidations, funding-as-feature) -- rather than continuing to transform
the same price-candle dataset. The user also explicitly declined to
change the trading universe (toward smaller-cap/lower-liquidity symbols,
where crypto factor literature often finds larger gross effects) for now,
to preserve comparability with every result already produced this
session; that idea is noted as a legitimate future direction, not started.

Before writing CS-002's pre-registration, a real mathematical
verification was run: if CS-002 used the same 168h horizon as CS-001
with the identical raw-return ranking, merely swapping LONG/SHORT sides,
the OOS net PnL is deterministically negative -- because the reversal
portfolio's gross return at an identical horizon/ranking/weighting is
the exact negative of the momentum portfolio's gross return
(`gross_reversal = -gross_momentum`), while the roundtrip cost is
identical (same leg count, same per-leg cost). Using CS-001's actual OOS
numbers: `gross_reversal_mirror = +64.61bps`, `net_reversal_mirror =
64.61 - 306.00 = -241.39bps`, negative by construction, without running
any new backtest. Running that literal mirror would not be an
informative new test.

The user was asked which horizon to use instead and chose 24h,
consistent with the classic finance literature's own treatment of
short-term reversal and medium-term momentum as distinct phenomena at
different time scales (e.g. Jegadeesh 1990's weekly reversal coexisting
with 3-12 month momentum), not the same signal with a flipped sign.

A related disclosure was made before writing the pre-registration: this
project already has a descriptive (never gated) result at the same 24h
horizon -- TSREV Family B (`TASK-TSREV-002`, ADR-0014), decile k=2,
z-score-normalized ranking, full-sample (not OOS-split): profit factor
0.87, net PnL -9,035.01bps, also negative. This is not the same test
(raw return vs. vol-normalized ranking, k=4 vs k=2, OOS-only vs
full-sample) but close enough that CS-002 is not being chosen "blind" --
this is disclosed explicitly in the pre-registration itself, before any
new backtest runs, so the eventual result is read correctly rather than
presented as a surprise.

## Decision

1. Pre-register `TASK-CS-002`
   (`docs/pre_registers/TASK-CS-002.md`): Cross-Sectional Mean Reversion
   at 24h formation/holding (not 168h), raw formation return ranking (no
   volatility normalization, consistent with CS-001's literature-faithful
   convention), long the bottom quintile (K=4 losers), short the top
   quintile (K=4 winners), equal-weighted, dollar-neutral, full rebalance,
   6.0bps roundtrip cost, same OOS split already used by
   TASK-TSREV-001/TASK-CS-001, gate net PF>1.10 AND net PnL>0 AND max
   DD<=baseline AND resolved leg-level trade_count>=200.
2. Trading universe remains unchanged (the same 20 liquid USD-M
   perpetuals) -- explicitly not broadened to lower-liquidity/smaller-cap
   symbols in this task, to preserve comparability with all prior
   results in this project. A universe change remains a legitimate future
   idea, not started.
3. If CS-002 also fails NAO PASSA, per the user's proposed roadmap the
   classic-price-factor research line (Research Family E, and by
   extension every family tested this session: A/B/TSMOM/C/D/E) closes;
   the next phase opens a genuinely new information category -- Market
   Microstructure / Alternative Data (open interest, order flow,
   liquidations, funding-as-feature), not "Research Family F" continuing
   the same price-candle transformations -- via its own separate
   ADR/pre-registration, not automatically.
4. If CS-002 passes, Research Family E continues sequentially into
   CS-003.

## Consequences

Either outcome is informative without ambiguity, because the horizon
choice is genuinely distinct from CS-001 (not a deterministic mirror)
and the proximity to TSREV Family B's descriptive result is disclosed in
advance, not discovered after seeing CS-002's own number. A failure here
would complete a clean, honest closure of five internally-consistent
research families (A through E) using only price-candle-derived
information, directly motivating the user's proposed pivot to a
different information category.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-CS-002` to `TASK_BOARD.md`. Update `CURRENT_SPRINT.md`,
`PROJECT_STATE.md`, `HANDOFFS.md`, `RISKS.md`. Implement
`src/research/cs_reversion.py`, `scripts/backtest_cs_reversion.py`,
`tests/test_cs_reversion.py`, run for real on the existing normalized
dataset (no new download), write
`reports/cs_reversion_backtest_final.md`.

## ADR-0019 - Open Research Phase II (Alternative Information): No OHLCV-Only Hypotheses, Information-Content-First Methodology

## Status

Accepted

## Context

With Research Family E closing NAO PASSA (ADR-0018), the user proposed a
paradigm shift rather than another OHLCV-derived hypothesis: "Research
Phase II - Alternative Information," with a strict rule -- no hypothesis
may rely on OHLCV alone -- spanning five candidate families: F (Open
Interest), G (Funding Structure), H (Order Flow/L2 microstructure), I
(Liquidation Dynamics), J (Regime Detection, a non-trading conditioning
layer). The user also proposed inverting this project's usual workflow:
measure a feature's information content (predictive capacity, temporal
stability, persistence) BEFORE designing any trading rule, rather than
building a rule first and discovering via backtest whether it works.

Before pre-registering anything, a real data-availability reconnaissance
was run (read-only S3 listing probes against `data.binance.vision`, the
same bucket this project's existing `historical_dataset.py` already
uses -- no download committed to the repository):

```text
Family G (Funding Structure): data ALREADY EXISTS in the normalized
  dataset (`funding_rate_asof`, verified 100% coverage, zero NaN, 8h
  step function) -- zero new download needed.
Family F (Open Interest): a `metrics` data family exists in the same
  public bucket (5-minute granularity: sum_open_interest,
  sum_open_interest_value, top-trader and overall long/short ratios,
  taker buy/sell volume ratio) -- confirmed available for all 20
  universe symbols starting before 2023-06-01 (the newest, SUIUSDT,
  starts 2023-05-03), via the SAME infrastructure already built and
  reviewed (`BinanceDataFamily` enum, checksum verification). Small
  daily files (~12KB each) -- nothing like bookTicker's 17.98GB/month
  problem. Requires a new but cheap download.
Family H (Order Flow/L2): still requires tick-level bookTicker data,
  the same expensive/machine-local constraint already mapped and
  deferred earlier this session -- unchanged.
Family I (Liquidation Dynamics): the `liquidationSnapshot` prefix
  (daily AND monthly, checked with no symbol filter) is COMPLETELY
  EMPTY in this public bucket for every symbol -- Binance does not
  publish bulk historical liquidation data here (likely discontinued
  for position-privacy reasons). No historical backtest is possible
  from this source; only a forward-only capture via the `forceOrder`
  WebSocket stream (no history) or an unauthorized third-party vendor
  would supply this family.
```

Given this, the user made four decisions: (1) sequence Family G first
(zero new data), then Family F (cheap new download, same infra); (2)
Family I is formally BLOCKED (not cancelled) and deferred indefinitely --
no third-party vendor evaluation, no forward-only capture project
started now; (3) Family J may use OHLCV-derived features (volatility,
trend) since it does not itself claim to have found new alpha, only
segments/contextualizes other work -- the "no OHLCV alone" rule targets
hypotheses claiming novel predictive information, not a conditioning
layer; (4) the information-content-first methodology uses Spearman rank
correlation (not mutual information) as the primary diagnostic metric,
plus a sign-consistency check across 3 non-overlapping ~12-month
sub-periods -- explicitly chosen for the same simplicity preference that
already led this project to abandon Kalman/OU sophistication and reject
purged cross-validation as unnecessary complexity for a fixed rule.

## Decision

1. Open Research Phase II: **Alternative Information**. No hypothesis in
   this phase may rely on OHLCV alone; Family J is the sole explicit
   exception, since it is a conditioning/segmentation layer, not an
   alpha claim.
2. Sequenced execution: Family G first (`TASK-ALT-001`, this session),
   then Family F. Family H (Order Flow) remains deferred, unchanged from
   prior sessions. Family I (Liquidation Dynamics) is formally BLOCKED
   -- no viable historical data source from this project's established
   Binance public-data pipeline; not started, not cancelled.
3. `TASK-ALT-001` (Family G, Funding Structure) is a pure
   information-content DIAGNOSTIC, not a strategy backtest -- no
   economic gate, no pass/fail on PnL/cost/drawdown. It measures whether
   4 formalized funding-derived features (extreme funding z-score,
   24h funding reversal, funding acceleration, funding-price divergence)
   show a stable, non-trivial Spearman correlation with 24h forward
   returns (reusing the same horizon already used in TASK-CS-002). See
   `docs/pre_registers/TASK-ALT-001.md` for the exact formulas,
   sub-period boundaries, and the pre-registered "has information"
   threshold (`|rho|>=0.03` full-sample AND sign-consistent across 3
   sub-periods).
4. If a feature shows information, designing an operational strategy
   around it is a SEPARATE task (`TASK-ALT-002` or later), with its own
   pre-registration -- mirroring the Payoff Engineering Phase
   1-diagnostic/Phase 2-strategy split (ADR-0015/0016) that the user
   already validated as a good pattern.
5. Reusable infrastructure: a generic causal information-content
   evaluator (Spearman correlation + sub-period sign-consistency) is
   built once and reused across future Family F/etc. diagnostics, not
   re-implemented per family.

## Consequences

This phase tests a fundamentally different information source than the
five OHLCV-derived families already closed NAO PASSA this session,
directly addressing the user's own diagnosis that the project's
remaining upside comes from information quality/originality, not further
transformations of the same price-candle dataset. A "no information
found" result for Family G would be informative on its own terms (the
funding data existed and was cheap to test, so a null result costs
little) and would not by itself justify skipping Family F (a distinct
data source with its own reconnaissance-confirmed availability).

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-ALT-001` to `TASK_BOARD.md`. Update `CURRENT_SPRINT.md`,
`PROJECT_STATE.md`, `HANDOFFS.md`, `RISKS.md`. Implement
`src/research/info_content.py` (reusable diagnostic engine),
`scripts/diagnostic_alt_funding_structure.py`,
`tests/test_info_content.py`, run for real on the existing normalized
dataset (no new download), write
`reports/alt_info_funding_structure_diagnostic.md`.

## ADR-0020 - Execute Family F (Open Interest): New Small Download, Same Information-Content Methodology As TASK-ALT-001

## Status

Accepted

## Context

Per the sequencing already agreed in ADR-0019 (Family G first, then
Family F), and the data-availability reconnaissance already performed
before ADR-0019 was written, Family F proceeds next: the `metrics`
family in Binance's public data bucket (5-minute granularity: open
interest level/value, top-trader and overall long/short ratios, taker
buy/sell volume ratio), confirmed available for all 20 universe symbols
starting before 2023-06-01. This download was already disclosed and
implicitly authorized when the user chose the "Familia G primeiro,
depois F" sequencing option, whose description explicitly stated it
"requer um novo download pequeno" -- this ADR does not re-request
authorization, it executes what was already agreed.

Two new technical facts were confirmed before writing the
pre-registration: (1) the `metrics` family is published as DAILY
archives only (the monthly listing is empty for every symbol checked),
unlike this project's existing `historical_dataset.py` machinery which
is built around monthly archives -- a new, dedicated small downloader is
needed rather than reusing `BinanceArchiveSpec` unchanged; (2) the
`.CHECKSUM` sidecar format is unchanged (64-character SHA256 hex,
verified against a real sample), so the existing generic
`verify_checksum_file` function is reused without modification. Total
new download: ~21,920 small daily files (~12KB each, ~260MB total) --
categorically smaller than the bookTicker 17.98GB/month problem that
required machine-local storage in earlier sprints.

## Decision

1. Pre-register `TASK-ALT-002`
   (`docs/pre_registers/TASK-ALT-002.md`): 5 Open Interest features
   formalized before any code runs (`oi_delta`, `oi_volume_ratio`,
   `oi_percentile`, `oi_acceleration`, `oi_price_divergence`), reusing
   the exact same information-content methodology, sub-period
   boundaries, magnitude threshold (0.03), and forward-return horizon
   (24h) already fixed in ADR-0019/TASK-ALT-001 -- not re-decided per
   family.
2. Build a new, dedicated daily-archive downloader (distinct from
   `historical_dataset.py`'s monthly-oriented `BinanceArchiveSpec`),
   reusing `verify_checksum_file` unchanged. Process one symbol at a
   time, resampling 5-minute data to hourly (last-observation-in-hour,
   the correct convention for a stock/level variable like open
   interest, not a flow variable) and discarding the 5-minute frame
   before moving to the next symbol -- avoids the memory-unsafe pattern
   that caused an OOM kill earlier in this project's history (Sprint 7
   bookTicker).
3. Write the resulting hourly-resampled Open Interest data to a new
   normalized file, separate from the existing OHLCV bars dataset,
   joinable by (symbol, open_time).

## Consequences

If Family F also shows no information, per the same discipline as
TASK-ALT-001 the result is final for these 5 exact features (no
parameter re-tuning after seeing results), and the next Research Phase
II candidate (Family J, or a follow-up on TASK-ALT-001's
`funding_price_divergence` near-miss) requires its own separate
pre-registration.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-ALT-002` to `TASK_BOARD.md`. Update `CURRENT_SPRINT.md`,
`PROJECT_STATE.md`, `HANDOFFS.md`, `RISKS.md`. Implement a new daily
Open Interest downloader/normalizer, run the real download (checksum
verified), compute the 5 features, run the same
`src/research/info_content.py` diagnostic, write
`reports/alt_info_open_interest_diagnostic.md`.

## ADR-0021 - Execute Family J (Regime Detection): Context/Risk Diagnostic, Not Directional Alpha

## Status

Accepted

## Context

`TASK-ALT-001` (Funding Structure) and `TASK-ALT-002` (Open Interest)
both closed without information under the pre-registered ADR-0019
criterion. Remaining Research Phase II branches are: Family H (Order
Flow/L2), still expensive/deferred; Family I (Liquidation Dynamics),
blocked by lack of historical public data; a future separate follow-up
on the `funding_price_divergence` near-miss; and Family J (Regime
Detection), explicitly allowed by ADR-0019 to use OHLCV-derived inputs
because it is a non-trading conditioning layer, not an alpha claim.

## Decision

Open `TASK-ALT-003` for Family J. This is a pure information-content
diagnostic, not a strategy. To preserve that distinction, the target is
not signed future return. The target is future 24h absolute log-return:
`abs(log_price[t+24h] - log_price[t])`, measuring future movement
intensity/risk. Six causal, pre-registered regime features are tested:
`realized_vol_24h`, `realized_vol_168h`, `trend_intensity_168h`,
`volume_shock_24h`, `market_dispersion_24h`, and
`market_abs_return_24h`.

The diagnostic reuses the same generic Spearman + 3-subperiod
sign-stability methodology and the same `|rho| >= 0.03` threshold from
ADR-0019/TASK-ALT-001. No new data download is needed; the Sprint 7
normalized hourly bars are sufficient.

## Consequences

A positive result means only that a regime/context variable has stable
information about future volatility/risk. It does not authorize a
SignalIntent, side selection, entry filter, exit filter, sizing rule, ML
feature in live logic, or any Execution/Ledger/Recovery change. Any
operational use requires a future separately pre-registered task.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-ALT-003` to `TASK_BOARD.md`. Add
`docs/pre_registers/TASK-ALT-003.md`, implement
`scripts/diagnostic_alt_regime_detection.py`, add focused tests, run the
real diagnostic on the existing normalized dataset, write
`reports/alt_info_regime_detection_diagnostic.md`, and update
`PROJECT_STATE.md`, `CURRENT_SPRINT.md`, `HANDOFFS.md`, `RISKS.md`, and
`TEST_MATRIX.md`.

## ADR-0022 - Test Minimal Regime Conditioning On TSREV 24h As Feasibility Only

## Status

Accepted

## Context

`TASK-ALT-003` found strong, stable information about future absolute
24h returns in causal regime features, especially realized volatility.
This is not directional alpha. The most disciplined operational follow-up
is therefore not a new signal, but a risk-conditioning diagnostic applied
to an already-known failed strategy: TSREV Family A 24h, whose original
failure was dominated by excessive drawdown versus buy-and-hold.

The available TSREV OOS period (2025-06 through 2026-05) has already been
analyzed repeatedly. Therefore this task cannot be treated as final
confirmation. It is a feasibility screen: a PASSA only motivates a future
new-OOS validation; a NAO_PASSA stops this regime-conditioning variant.

## Decision

Open `TASK-ALT-004`. Primary and only tested filter: block TSREV 24h
entries when `realized_vol_168h[t]` is above the symbol's own causal
90-day 67th percentile. Missing regime data fails closed. The 67th
percentile is fixed before execution as the top-tercile high-volatility
cut; no sweep is allowed. Remaining trades are renormalized by the same
inverse-vol sizing convention as TSREV, so the result is not helped merely
by lower total exposure.

Feasibility gate reuses the TSREV primary gate on the filtered OOS sample:
net PF > 1.05, net PnL > 0, max drawdown <= buy-and-hold max drawdown for
the same period, and at least 200 resolved trades.

## Consequences

This task may show whether regime information can plausibly reduce TSREV's
drawdown problem. It cannot authorize paper/live trading, SignalIntent
changes, execution filters, ML features, or any ledger/execution/recovery
changes. Any positive result requires a future separately pre-registered
new-OOS validation.

## Agent Impact

- PM Agent
- Quant Research Agent
- Backtest Agent

## Migration

Add `TASK-ALT-004` to `TASK_BOARD.md`. Add
`docs/pre_registers/TASK-ALT-004.md`, implement
`scripts/run_regime_conditioned_tsrev.py`, add focused tests, run the real
feasibility diagnostic on the existing normalized dataset, write
`reports/regime_conditioned_tsrev_feasibility.md`, and update
`PROJECT_STATE.md`, `CURRENT_SPRINT.md`, `HANDOFFS.md`, `RISKS.md`, and
`TEST_MATRIX.md`.
