# Blockers

Last updated: 2026-06-30

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
Sprint 7 technical research base is implemented and reviewed, but the Sprint 8
advancement gate requires at least one real candidate pair set with documented
liquidity, spread/cost evidence, stationarity, half-life, beta stability, and
clear results. The documented 36 complete-month Binance USD-M dataset has not
yet been downloaded, checksumed, normalized, or run through the research
pipeline.
```

Required correction:

```text
1. Build or run the historical dataset loader/normalizer for the documented
   2023-06-01T00:00:00Z <= open_time < 2026-06-01T00:00:00Z window.
2. Verify checksums and dataset version/provenance.
3. Run pair selection, stationarity, Kalman, and OU against real normalized
   bars.
4. Update reports/research_sprint_07.md with real approved/rejected pair tables.
5. Re-run required tests and reviewer gate.
```

Gate policy:

```text
Do not start Sprint 8 from synthetic notebook evidence. Sprint 8 may start only
after the real-dataset research gate is re-run and passes.
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
