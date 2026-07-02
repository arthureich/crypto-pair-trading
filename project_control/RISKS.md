# Risks

## Active Risk Register

| Risk | Severity | Owner | Mitigation | Status |
|---|---|---|---|---|
| Signal sends or implies direct order action | Critical | Architect Agent | Explicit SignalIntent-only interface | Open |
| Order sent without persisted event | Critical | Ledger Agent | Event-first execution contract | Open |
| ACK_UNKNOWN retried blindly | Critical | Execution / Risk Agent | Force reconciliation before retry | Open |
| Fill applied as blind delta | Critical | Ledger Agent | Cumulative executedQty reconciliation | Open |
| Stale or gapped book permits entry | High | Market Data Agent | Book health gate | Open |
| Model used for hard stop or hedge | Critical | Execution / Risk Agent | Deterministic exit invariant | Open |
| Recovery boots into trading before reconciliation | Critical | Ledger Agent | Safe mode boot protocol | Open |
| REST 5xx treated as no fill | Critical | Ledger Agent | Reconcile by order id and cumulative fills before assuming state | Open |
| Missing WebSocket event treated as no fill | Critical | Ledger Agent | REST reconciliation and cumulative executedQty checks | Open |
| Orphan order cancel treated as flat without requery | Critical | Ledger Agent | Safe orphan cancel requires cancel by exchange order id, then requery order/fill state and positions | Open |
| Safe mode permits non-risk-reducing action | Critical | Ledger Agent | Recovery protocol allows only cancellation, reconciliation, and proven risk reduction | Open |
| Recovery resumes without FLAT_RECONCILED or equivalent reconciled state | Critical | Ledger Agent | Normal resume requires zero ACK_UNKNOWN, applied cumulative fills, position match, orphan resolution, and persisted reconciled state | Open |
| Partial fill does not trigger hedge or lockdown | Critical | Execution / Risk Agent | Explicit PARTIALLY_FILLED and HEDGING_REQUIRED routes | Open |
| Ledger uncertainty permits new entry | Critical | Execution / Risk Agent | Fail-closed entry gate on ledger uncertainty | Open |
| Kill switch unavailable or fail-open | Critical | Execution / Risk Agent | Deterministic local kill switch and external heartbeat requirement | Open |
| Missing or stale risk input permits entry | Critical | Execution / Risk Agent | `docs/risk_limits.md` requires missing/stale risk inputs to fail closed | Open |
| Risk-reducing action increases exposure | Critical | Execution / Risk Agent | Stress-risk proof obligation: new stress risk must be lower than old stress risk | Open |
| Forbidden runtime configuration accepted | Critical | Execution / Risk Agent | Reject Cross Margin, Kelly, 10x, live multi-exchange, and leverage before Sprint 26 at config load and pre-order checks | Open |
| Daily loss or drawdown threshold unresolved before live mode | High | PM Agent | Mark as Sprint 1 gate unresolved; live entries fail closed until measurable thresholds are approved | Open |
| Scope drift across agents | Medium | PM Agent | Allowed-file lists and handoffs | Open |
| Binance Public Data bookTicker source has no verified top-of-book/L2 coverage past ~2024-04, so cost-gated PASS cannot be produced for the full 2023-06/2026-05 window from this source | High | PM Agent | Per ADR-0007, cost-gated claims are scoped to what was actually verified (see next row); 2024-05 through 2026-05 needs an alternative source or live-capture evidence | Open |
| Genuine cost-gated PASS for 31 candidate pairs rests on a single verified month (June 2023), not a multi-year sample; spread regimes can differ across market conditions not covered by this pilot | Medium | Quant Research Agent | Documented explicitly in reports/research_sprint_07.md and BLOCKERS.md as a 1-month pilot; do not generalize to full-window or all-regime claims without processing more verified months | Open |
| Stitching daily bookTicker archives produces a small number of duplicate/residual hourly rows at day boundaries (27 duplicate symbol-hours / 54 duplicate rows out of 10827 raw hourly rows in the expanded June 2023 pilot) | Low | Market Data Agent | Expanded gate uses an explicit deduplicated hourly-cost file (10800 rows), keeping the row with the highest spread_sample_count_1h and latest last_event_time per (symbol, open_time); raw duplicates are preserved in `all_candidates_202306_duplicate_hours.csv` for audit | Open |
| S3 ListObjectsV2 pagination (IsTruncated/NextContinuationToken) is not handled in `_fetch_s3_objects`/`parse_s3_list_objects` | Medium | Market Data Agent | Verified harmless for the current run (KeyCount << MaxKeys=1000, IsTruncated=false); add continuation-token handling before relying on this probe if per-symbol object counts could exceed 1000 | Open |
| `download_archives`/`_download_archive` real-network path in historical_dataset.py has zero test coverage (no mock) | Medium | QA Agent | Safe for offline CI since no test exercises it; add a mocked-network regression test before depending on this path for unattended/scheduled real downloads | Open |
| Sprint 8 backtest holds a fixed 1-hour horizon with no stop-loss/take-profit/z-score-reversion exit | Medium | Backtest Agent | Documented as a known first-pass simplification in reports/sprint_08_backtest.md; a proper BarrierPolicy-driven exit (already specified in docs/architecture.md for live use) is not yet wired into the offline backtest | Open |
| Sprint 8 execution cost uses only median hourly top-of-book spread, not p95/p99 tail or order-book depth/impact for the traded notional | Medium | Market Data Agent | Documented explicitly; a p95-based sensitivity re-run is a reasonable follow-up before allocating capital to the 13 backtest-approved pairs | Open |
| Sprint 8 max_drawdown_bps is computed per pair only; no time-aligned combined portfolio drawdown metric exists across the 622 simulated trades | Low | Backtest Agent | Documented in reports/sprint_08_backtest.md; do not read per-pair drawdown as a portfolio risk figure | Open |
| 17GB of raw checksum-verified Binance bookTicker archives are preserved under data/research/binance_public/cost_pilot/raw/ pending TASK-008-08 cleanup | Low | Market Data Agent | Cleanup intentionally BLOCKED until the user explicitly accepts the evidence state; disk has 353GB free, not urgent | Open |
| Roadmap canonical Sprint 8 gap: directional triple-barrier exit and Sharpe/Sortino/profit-factor metrics were never implemented (this project's actual "Sprint 8" was a different, hybrid design) | Medium | Backtest Agent | Logged as explicit deferred technical debt per ADR-0008, not silently dropped; pick up before claiming full roadmap Sprint 8 compliance | Open |

## MVP Forbidden Items

```text
Cross Margin
Kelly sizing
10x leverage
leverage before Sprint 26
blind order retry
live multi-exchange
model-driven emergency exit
```
