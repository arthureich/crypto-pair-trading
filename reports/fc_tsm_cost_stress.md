# TASK-FC-II-007 -- Vol-Targeted TSM Cost Stress

Per `docs/pre_registers/TASK-FC-II-007.md` (ADR-0027). Sensitivity, NOT tuning: the LOCKED FC-II-005 signal with cost_bps_per_leg swept over a fixed grid. In-sample, descriptive, no verdict.

Baseline (buy-hold) Sharpe -0.143. Mean turnover per rebalance 0.457. **Net-PnL breakeven cost = 142.2 bps/leg.** Realistic band for alt-perp L/S: 10-15 bps/leg.

## Degradation curve

| Cost (bps/leg) | Sharpe | Net PnL | Beats buy-hold |
|---:|---:|---:|---|
| 0 | +1.083 | +1.4235 | True |
| 3 | +1.060 | +1.3934 | True |
| 6 | +1.038 | +1.3634 | True |
| 10 | +1.007 | +1.3234 | True |
| 15 | +0.969 | +1.2733 | True |
| 20 | +0.931 | +1.2233 | True |
| 30 | +0.854 | +1.1232 | True |
| 50 | +0.702 | +0.9230 | True |

## Reading

SURVIVES: beats buy-hold with positive net PnL at 15 bps/leg, and the net-PnL breakeven is 142.2 bps/leg -- comfortably above realistic cost. The lead survives the most likely killer -> merits OOS pursuit.
