# TASK-ALT-013 -- VRP-as-Overlay on the TSM (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-ALT-013.md` (ADR-0032). Equal-risk 50/50 blend of the TSM (trend, 20 perps) and VRP-timing (BTC/ETH, primary long/short) weekly return streams -- testing the ALT-012 conclusion that VRP is best used as a diversifying FEATURE/overlay, not a standalone trade. **Development result -- NOT a promotion; OOS-gated.**

## Overall (full dev window, weekly)

| Metric | Value |
|---|---:|
| Overlapping weeks | 156 |
| TSM Sharpe | 0.991 |
| VRP Sharpe | 0.493 |
| **Blend Sharpe** | **0.966** |
| Stream correlation | +0.180 |
| TSM max drawdown (risk units) | 5.865 |
| Blend max drawdown (risk units) | 5.073 |

## Sub-period (Sharpe: TSM / VRP / Blend; corr)

| Period | TSM | VRP | Blend | Corr |
|---|---:|---:|---:|---:|
| 2023-06_2024-05 | 1.432 | 0.794 | 1.381 | +0.299 |
| 2024-06_2025-05 | 0.648 | -0.480 | 0.122 | -0.055 |
| 2025-06_2026-05 | 0.968 | 1.168 | 1.301 | +0.349 |

## Reading

Blend vs TSM Sharpe: 0.991 -> 0.966 (delta -0.025); VRP sleeve Sharpe 0.493; correlation +0.180. Blend beats TSM in every sub-period: False; drawdown not worse: True. REJECTED as a dev candidate: adding VRP as an overlay does not consistently improve the TSM's risk-adjusted return. The VRP signal is real (ALT-011) but does not lift the perp book as a diversifying sleeve either. Closes the free VRP exploration; remaining options avenues (skew/surface, Angle-A options book) are user decisions. No promotion; OOS-gated.
