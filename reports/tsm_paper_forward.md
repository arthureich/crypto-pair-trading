# Vol-Targeted TSM -- Forward Paper Track (genuine OOS)

Per ADR-0027 (FC-II-005/008). The FIXED TSM (with funding P&L) run so that ONLY rebalances after the 2026-05-31 dev cutoff count as OOS; pre-cutoff bars form the causal 28d signal (a lookback, not a test set). **Monitoring, not a verdict** -- a meaningful TSM OOS needs ~100 5d-rebalances (~1-2y).

OOS rebalances so far: **5** (trigger 100; 95 remaining).

## OOS track so far (in-development scale -- NOT a verdict)

| Metric | TSM (OOS) | Baseline |
|---|---:|---:|
| Sharpe | 4.192 | -4.299 |
| Net PnL | 0.0868 | -0.1033 |
| Max drawdown | 0.0421 | 0.0956 |

A handful of rebalances is pure noise. Do NOT read this as evidence; it is the seed of an accumulating track that only becomes informative near the trigger. Re-run as each new month is downloaded.
