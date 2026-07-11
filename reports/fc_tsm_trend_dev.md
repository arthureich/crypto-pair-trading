# TASK-FC-II-005 -- Classic Vol-Targeted TSM (development)

Per `docs/pre_registers/TASK-FC-II-005.md` (ADR-0027). **Development window, NO verdict.** Position = sign of the 28d trailing return, sized inverse to 7d realized vol, unit gross, 5d rebalance, 6bps/leg. Distinct from the Donchian TSMOM. The literature claims vol-targeting rescues the trend edge; this tests that on our data.

## Development metrics (vol-targeted TSM vs equal-weight buy-and-hold)

| Metric | TSM long/short | TSM long-only | Baseline (buy-hold) |
|---|---:|---:|---:|
| Sharpe (annualized) | 1.038 | -0.011 | -0.143 |
| Max drawdown | 0.3489 | -- | 1.3833 |
| Net PnL (log-ret units) | 1.3634 | -- | -0.2706 |
| Mean turnover / rebalance | 0.457 | -- | -- |
| Rebalances | 219 | | |

## Reading

The literature's claim is risk-adjusted. Here TSM beats buy-and-hold on Sharpe and has lower max drawdown.

Both conditions hold -> a candidate for a separately pre-registered OOS test (with realistic cost); NOT a verdict here. Caveats: in-sample dev window; the short leg carries it (long-only is flat), so it may be flattered by the bear-heavy part of the sample -- regime-dependence must be checked in OOS.
