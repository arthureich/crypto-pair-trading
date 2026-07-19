# Forward Monitor -- canonical TSM (TASK-DEPLOY-001, Phase 7)

Reads the immutable forward ledger (Phase 2/3). Alerts only ALERT -- the frozen strategy is never modified here. Reading horizons gate interpretation so a short track is not read as a verdict.

## Reading horizon: **operational_diagnostic_only** (5 rebalances ~ 0.8 months)

Verdict horizon reached: **False**. 1mo = operational diagnostic; 3mo preliminary; 6mo initial; 12mo first relevant; 18-24mo more confident. **A short track is NOISE, not a verdict.**

## Streams (accrued OOS)

| Stream | n | Sharpe | Sortino | maxDD % | hit rate | PF | net |
|---|---:|---:|---:|---:|---:|---:|---:|
| theoretical | 5 | 4.192 | n/a | 4.2 | 0.80 | 3.06 | 0.0868 |
| executable | 5 | 4.190 | n/a | 4.2 | 0.80 | 3.06 | 0.0867 |
| conservative | 5 | 4.190 | n/a | 2.1 | 0.80 | 3.06 | 0.0434 |
| cash | 5 | 0.000 | -- | 0.0 | -- | -- | 0.0000 |
| buy-hold (ref) | 5 | -4.299 | -- | -- | -- | -- | -0.1033 |

## Alerts (alert only -- NEVER auto-modify the strategy)

- none tripped.

Alert criteria: execution shortfall > budget; cost above breakeven; drawdown beyond historical; hit-rate persistent drop; PnL concentration; recurring data failures; config-hash mismatch; exposure != frozen config. A tripped alert means a HUMAN reviews -- the frozen economic parameters are never changed automatically.

## Reading (fact / limitation)

- FACT: config-hash matches the frozen canonical (True); 0 data-failure events in the ledger.
- LIMITATION: the OOS track is short (well below any verdict horizon); all metrics here are operational diagnostics, NOT evidence of the edge. The track accrues as each new month is downloaded and the execution report appends to the ledger. Re-run this monitor after each append.
