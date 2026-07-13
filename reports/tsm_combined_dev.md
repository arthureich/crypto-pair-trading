# TASK-TSM-008 -- Combined ERC + Vol-Targeting TSM (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-TSM-008.md` (ADR-0031). Composes the two independently-validated wins -- ERC (cross-sectional, TSM-003) + volatility targeting (time-series, TSM-007). **Development-window result -- NOT a promotion; OOS-gated.** The combined cell is preferred only if it beats the best single component; a tie keeps the single overlay (parsimony).

## Headline (full dev window) -- Sharpe / maxDD / net

| Variant | Sharpe | Max drawdown | Net PnL |
|---|---:|---:|---:|
| base | 0.970 | 0.3470 | 1.2672 |
| ERC-only | 1.039 | 0.3257 | 1.3539 |
| vol-target-only | 1.107 | 0.3286 | 1.4222 |
| COMBINED | 1.183 | 0.3093 | 1.5318 |

## Sub-period Sharpe

| Period | base | ERC | vol-tgt | COMBINED |
|---|---:|---:|---:|---:|
| 2023-06_2024-05 | 1.556 | 1.618 | 1.591 | 1.671 |
| 2024-06_2025-05 | 0.586 | 0.663 | 0.668 | 0.755 |
| 2025-06_2026-05 | 0.975 | 1.058 | 1.292 | 1.368 |

## BTC regime Sharpe

| Regime | base | ERC | vol-tgt | COMBINED |
|---|---:|---:|---:|---:|
| BTC_up | 0.874 | 0.997 | 1.058 | 1.171 |
| BTC_down | 1.096 | 1.093 | 1.176 | 1.199 |

## Cost sensitivity (Sharpe)

| Cost bps/leg | base | ERC | vol-tgt | COMBINED |
|---|---:|---:|---:|---:|
| 0 | 1.016 | 1.079 | 1.150 | 1.221 |
| 6 | 0.970 | 1.039 | 1.107 | 1.183 |
| 15 | 0.901 | 0.979 | 1.042 | 1.126 |
| 30 | 0.786 | 0.879 | 0.934 | 1.030 |

## Reading

Sharpe: base 0.970 | ERC 1.039 | vol-target 1.107 | combined 1.183. Combined beats base in every cut: True; combined maxDD <= base: True. CANDIDATE (combined preferred): combined Sharpe 1.183 beats the best single component (vol-targeting 1.107) by +0.076, drawdown not worse, consistent across cuts. The two overlays are complementary.
