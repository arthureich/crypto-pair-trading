# TASK-TSM-007 -- Volatility-Targeted TSM Dev Run (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-TSM-007.md` (ADR-0031). Managed-vol overlay (scale each rebalance's return inversely to the strategy's own trailing realized vol; target ~constant vol, average leverage ~1) on the base TSM (FC-II-008). **Development-window result -- NOT a promotion; OOS-gated.** Honest prior: the benefit is often muted for pure trend.

## Headline (full dev window)

| Metric | Base | Vol-targeted |
|---|---:|---:|
| Sharpe | 0.970 | 1.107 |
| Max drawdown | 0.3470 | 0.3286 |
| Net PnL | 1.2672 | 1.4222 |
| Rebalances | 219 | 219 |

## Sub-period stability (Sharpe)

| Period | Base | Vol-targeted |
|---|---:|---:|
| 2023-06_2024-05 | 1.556 | 1.591 |
| 2024-06_2025-05 | 0.586 | 0.668 |
| 2025-06_2026-05 | 0.975 | 1.292 |

## BTC regime (Sharpe)

| Regime | Base | Vol-targeted |
|---|---:|---:|
| BTC_up | 0.874 | 1.058 |
| BTC_down | 1.096 | 1.176 |

## Cost sensitivity (Sharpe)

| Cost bps/leg | Base | Vol-targeted |
|---|---:|---:|
| 0 | 1.016 | 1.150 |
| 6 | 0.970 | 1.107 |
| 15 | 0.901 | 1.042 |
| 30 | 0.786 | 0.934 |

## Funding sensitivity (Sharpe)

| include_funding | Base | Vol-targeted |
|---|---:|---:|
| False | 1.038 | 1.163 |
| True | 0.970 | 1.107 |

## Reading

Vol-targeted vs base: Sharpe 0.970 -> 1.107 (delta +0.137); maxDD 0.3470 -> 0.3286 (delta -0.0184). Consistent across sub-periods AND BTC regimes: True. CANDIDATE for OOS: vol-targeting improves Sharpe AND does not worsen drawdown, consistently across sub-periods and BTC regimes.
