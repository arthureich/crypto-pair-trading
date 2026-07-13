# TSM Forward Paper Track (genuine OOS) -- PRIMARY: combined ERC + vol-targeting

Per ADR-0027 / ADR-0031 (TASK-TSM-008). The lead OOS candidate is the combined ERC + volatility-targeting TSM; the base vol-targeted TSM is a reference line. ONLY post-2026-05-31 rebalances count as OOS; pre-cutoff bars form the causal signal + vol-target history (a lookback, not a test set). **Monitoring, not a verdict** -- a meaningful OOS needs ~100 5d-rebalances (~1-2y).

OOS rebalances so far: **5** (trigger 100; 95 remaining).

## OOS track so far (in-development scale -- NOT a verdict)

| Metric | Combined (primary) | Base TSM (ref) | Buy-hold |
|---|---:|---:|---:|
| Sharpe | 4.0427 | 4.1921 | -4.2991 |
| Net PnL | 0.0965 | 0.0868 | -0.1033 |
| Max drawdown | 0.0492 | 0.0421 | 0.0956 |

A handful of rebalances is pure noise. Do NOT read this as evidence; it is the seed of an accumulating track that only becomes informative near the trigger. Re-run as each new month is downloaded.
