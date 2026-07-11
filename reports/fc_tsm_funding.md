# TASK-FC-II-008 -- Vol-Targeted TSM with Perp Funding P&L

Per `docs/pre_registers/TASK-FC-II-008.md` (ADR-0027). Adds funding P&L (long pays when funding>0, short receives) over each 5d hold to the LOCKED FC-II-005 signal. In-sample, descriptive, no verdict. Closes the gap flagged in FC-II-005/007 (a perp book held 5d incurs funding).

## Funding off vs on (6 bps/leg cost)

| Metric | Funding OFF | Funding ON |
|---|---:|---:|
| Sharpe | 1.038 | 0.970 |
| Net PnL | 1.3634 | 1.2672 |
| Max drawdown | 0.3489 | 0.3470 |
| Baseline Sharpe | -0.143 | -0.143 |

Funding-on net-PnL breakeven cost: **132.6 bps/leg** (realistic band 10-15).

## Reading

SURVIVES funding: with funding P&L included, Sharpe 0.970 still beats baseline -0.143 with positive net PnL, and the cost breakeven stays above the realistic band. The last cheap in-sample gap is closed favorably -> the lead now merits an OOS pursuit.
