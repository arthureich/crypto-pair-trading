# Blockers

Last updated: 2026-07-01

## Active Blockers

### BLOCKER-2026-06-30-S7-REAL-DATASET-GATE

Status: ACTIVE

Severity: P1

Owner: PM Agent

Blocked scope:

```text
Sprint 8 start
```

Reason:

```text
Sprint 7 technical research base is implemented. The documented 2023-06 through
2026-05 Binance USD-M dataset has been downloaded, checksumed, normalized, and
run through pair selection, stationarity, Kalman, OU, and z-score checks.

TASK-007-09 (loader/normalizer) passed Market Data Agent + QA Agent review and
is DONE. TASK-007-10 (execution-cost evidence) is also DONE, but with a
definitive negative finding: Binance Public Data bookTicker (top-of-book/L2)
coverage exists for only 11 of the 36 required months (2023-06 through
approximately 2024-04), identically for all 20 accepted symbols. This was
verified directly against the live Binance S3 endpoint (KeyCount << MaxKeys,
IsTruncated=false on both monthly and daily prefixes for the checked symbol,
ruling out a pagination artifact) and independently re-verified by QA Agent.
cost_gated_pass=false for all 41 candidate pairs, enforced unconditionally
when the source is incomplete.

This is no longer a "pending execution" blocker. It is a real data-availability
limit of the current source. Sprint 8 cannot start from statistical-only
candidates per ADR-0002 (Safety Before Edge).
```

Required correction (decision, not execution):

```text
1. Dataset and cost-evidence artifacts are preserved under
   data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_*
   including the execution-cost source review and gate outputs.
2. TASK-007-09 and TASK-007-10 are DONE; no further execution work unblocks
   this on its own.
3. PM/stakeholder must choose a path forward before Sprint 8 can open:
   a. Locate and verify an alternative historical top-of-book/L2 source
      (e.g. a paid tick-data vendor) covering the full 2023-06 through 2026-05
      window, then rerun the cost gate.
   b. Shrink the Sprint 7 research window to the verified-covered sub-period
      (2023-06 through ~2024-04, ~11 months) and rerun the full statistical +
      cost gate on that sub-window only.
   c. Redefine cost-gated PASS policy via a new ADR in DECISIONS.md (for
      example: accept forward-collected execution-cost evidence from live
      market-data capture going forward, instead of requiring retroactive
      historical top-of-book coverage for the full backtest window).
   d. Keep Sprint 8 blocked indefinitely until (a) or (c) is resolved.
4. Whichever path is chosen requires an ADR entry and a rerun of the affected
   gate before Sprint 8 opens.
```

Gate policy:

```text
Do not start Sprint 8 from statistical-only candidates. Sprint 8 may start only
after either verified execution-cost evidence exists and passes cost-gated
review, or an ADR explicitly redefines the cost-gated PASS requirement.
```

## Resolved Blockers

### BLOCKER-2026-06-30-S5S6-GATE-LOCAL-BOOK

Status: RESOLVED

Severity: P1

Owner: PM Agent

Blocked scope:

```text
Sprint 7 start
```

Reason:

```text
Pre-Sprint 7 gate audit found that the Sprint 5/6 implementation passes the
existing book-health/features/slippage tests, but does not yet satisfy the
literal gate checklist for a local order book with snapshot/diff application
and explicit BookFeatures book_age_ms/in_sync fields.
```

Required correction:

```text
1. Add a pure LocalOrderBook/BookBuilder that applies snapshots and in-sequence
   diffs, discards old updates, invalidates on gaps, removes zero-quantity
   levels, exposes best_bid/best_ask, book_age_ms, and in_sync, and fails closed
   for stale/empty/out-of-sync books.
2. Expose book_age_ms and in_sync on execution feature snapshots.
3. Add focused regression tests and rerun the Sprint 5/6 gate tests.
```

Gate policy:

```text
Sprint 7 must not start until this blocker is resolved.
```

Resolution:

```text
Resolved on 2026-06-30.
Added LocalOrderBook/BookBuilder snapshot/diff behavior, explicit
BookExecutionFeatures book_age_ms/in_sync fields, focused regression tests,
full-suite verification, and QA / Chaos Testing Agent re-review.
Gate result: PASSA.
```

## Blocker Protocol

When blocked:

```text
1. Stop work on the unsafe path.
2. Add a blocker entry here.
3. Update HANDOFFS.md.
4. Mark the task BLOCKED in TASK_BOARD.md.
5. Ask PM Agent or Architect Agent for a decision.
6. Add an ADR if architecture changes.
```
