# Blockers

Last updated: 2026-07-02

## Active Blockers

### BLOCKER-2026-06-30-S7-REAL-DATASET-GATE

Status: PARTIALLY RESOLVED (scoped)

Severity: P2 (downgraded from P1 now that genuine scoped cost-gated evidence exists)

Owner: PM Agent

Blocked scope:

```text
Sprint 8 start for any pair/claim WITHOUT a real verified cost-gated evidence
window. Sprint 8 start is NOT blocked for the 31 pairs with genuine June 2023
cost-gated evidence (see Resolution).
```

Reason:

```text
Sprint 7 technical research base is implemented. The documented 2023-06 through
2026-05 Binance USD-M dataset has been downloaded, checksumed, normalized, and
run through pair selection, stationarity, Kalman, OU, and z-score checks.

TASK-007-09 and TASK-007-10 are both DONE. TASK-007-10 first proved that
Binance Public Data bookTicker (top-of-book/L2) coverage exists for only 11 of
the 36 required months (2023-06 through approximately 2024-04), identically
for all 20 accepted symbols — verified directly against the live Binance S3
endpoint (ruling out a pagination artifact) and independently re-verified by
QA Agent. This remains true: the full 36-month window cannot be cost-gated
from this source.
```

Resolution (scoped, per ADR-0007):

```text
Per ADR-0007 (Cost-Gated PASS Scoped To Verified Evidence), memory-safe
daily-bookTicker pilots were run for real inside June 2023. The first 6-symbol
pilot proved the path and was reviewed by Market Data Agent and QA Agent. On
2026-07-02 the scope was expanded to all 15 symbols appearing in the 41 Sprint
7 candidate pairs. The runner was hardened to stream-read each ZIP member with
numeric dtypes before processing BTCUSDT/ETHUSDT, avoiding the prior
decompressed whole-file load. The expanded run verified 450 Binance daily ZIPs
and .CHECKSUM files (17.98GB compressed), produced 10827 raw hourly rows,
isolated 27 duplicate symbol-hours at day boundaries, and wrote a deduplicated
10800-row hourly-cost file for the gate.

The scoped June-2023 cost gate produced `cost_gated_pass=true`: 31 of 41
candidate pairs pass with genuine verified top-of-book evidence. The 10
failures are all ADAUSDT pairs, correctly blocked because ADAUSDT fails the
symbol-level spread gate (`WIDE_MEDIAN_SPREAD`, median spread 3.52bps >
3.0bps threshold).

Sprint 8 may now open, SCOPED to these 31 pairs, explicitly labeled as backed
by a single verified month (June 2023) of real top-of-book evidence -- not a
multi-year backtest validation. Any work claiming cost-gated status for the 10
failed ADAUSDT pairs or for months outside this verified June-2023 window
remains statistical-only and blocked from cost-gated claims.
```

Residual blocker (kept open, downgraded severity):

```text
1. The remaining ~10 verified months (2023-07 through ~2024-04) have not been
   processed; extending the pilot is possible with the same daily-download
   tooling but was not run in this pass (time/resource scoping choice, not a
   source limitation).
2. The window 2024-05 through 2026-05 (25 of 36 months) has NO verified
   top-of-book source on Binance Public Data at all. Closing this permanently
   requires either an alternative source (paid vendor) or reliance on the
   live Market Data Plane (Sprint 5/6 BookFeatures) for forward evidence once
   paper/live trading exists, per ADR-0007.
3. Any pair/claim outside the 31 passed pairs and verified June-2023 window
   must not be presented as cost-gated without repeating this same
   real-download-and-verify process.
```

Gate policy:

```text
Do not present statistical-only candidates as cost-gated. Cost-gated PASS
claims must always cite the exact symbols/dates/granularity of the verified
evidence they rest on (ADR-0007). Sprint 8 may open only for the specific
scope that has real verified cost-gated evidence; broader claims require
repeating this process or an alternative source.
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
