# Funding Carry K=5 -- Forward Paper Track (genuine OOS)

Per ADR-0027. The FIXED, pre-registered incremental K=5 policy run on data AFTER the 2026-05-31 development cutoff -- genuine out-of-sample, since the signal was frozen before this data existed. **Monitoring, not a verdict**: the pre-registered gate is evaluated only once the trigger count of OOS rebalances has accrued.

## OOS track so far

| Metric | Value |
|---|---:|
| Resolved OOS rebalances | 89 |
| Trigger (for a verdict) | 500 |
| Remaining to trigger | 411 |
| Net PnL (bps) | -300.4 |
| Profit factor | 0.7830 |
| Hit rate | 0.4944 |
| Status | ACCRUING (below trigger) |

## Reading this honestly

A single short window is noisy: a real edge can miss it and a fake one can pass it. Do NOT read the current PF as a verdict -- it is one small sample. The point is the accumulating record: survive a growing sequence of independent OOS periods and the 'it was just luck' explanation gets progressively harder. The base-signal gate stays at profit factor >= 1.10 on the accrued OOS once the trigger count is reached.
