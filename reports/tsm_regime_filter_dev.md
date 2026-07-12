# TASK-TSM-001 -- Regime Filter Dev Run (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-TSM-001.md` (ADR-0031). Base = vol-targeted TSM with funding (FC-II-008); filtered = flat when aggregate trend strength (mean of |trailing_return|/vol) is below its 90d causal median. Params fixed a priori. **Development-window result -- NOT a promotion; promotion is OOS-gated.** Robustness battery below is decisive per the pre-registration.

## Headline (full dev window)

| Metric | Base | Filtered |
|---|---:|---:|
| Sharpe | 0.970 | 0.949 |
| Max drawdown | 0.3470 | 0.3209 |
| Net PnL | 1.2672 | 1.0933 |
| Mean turnover | 0.4570 | 0.3074 |
| Rebalances | 219 | 219 |

Fraction of rebalances the regime is ON (book live): **0.42** (the filter is flat the rest of the time).

## Sub-period stability (Sharpe)

| Period | Base | Filtered |
|---|---:|---:|
| 2023-06_2024-05 | 1.556 | 1.320 |
| 2024-06_2025-05 | 0.586 | 1.025 |
| 2025-06_2026-05 | 0.975 | 0.543 |

## BTC regime (Sharpe)

| Regime | Base | Filtered |
|---|---:|---:|
| BTC_up | 0.874 | 0.603 |
| BTC_down | 1.096 | 1.390 |

## Cost sensitivity (Sharpe)

| Cost bps/leg | Base | Filtered |
|---|---:|---:|
| 0 | 1.016 | 0.984 |
| 6 | 0.970 | 0.949 |
| 15 | 0.901 | 0.896 |
| 30 | 0.786 | 0.808 |
| 60 | 0.556 | 0.633 |

## Funding sensitivity (Sharpe)

| include_funding | Base | Filtered |
|---|---:|---:|
| False | 1.038 | 1.018 |
| True | 0.970 | 0.949 |

## Reading

Filtered vs base: Sharpe 0.970 -> 0.949 (delta -0.021); maxDD 0.3470 -> 0.3209 (delta -0.0261); book live 42% of the time. Consistent across sub-periods: False; across BTC regimes: False. REJECTED as a dev candidate: the filter does not deliver a CONSISTENT risk-adjusted improvement (Sharpe up AND drawdown not worse, stable across all 3 sub-periods and both BTC regimes). Per the pre-registration, an improvement seen only in aggregate or one regime is treated as a likely false positive. Hypothesis closed with this negative result; proceed to Line 2 (position sizing).
