# TASK-TSM-005 -- Trend + Carry Ensemble Dev Run (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-TSM-005.md` (ADR-0031, Line 5). Equal-risk 50/50 blend of two weekly return streams -- the vol-targeted TSM (trend) and the funding-carry K=5 incremental (carry), the canonical diversifying CTA sources. Streams standardized to unit risk (scale-invariant). **Development-window result -- NOT a promotion; OOS-gated (carry already printed a negative first OOS month).** The question: does ADDING carry beat the TSM alone, consistently, with low stream correlation?

## Overall (full dev window, weekly)

| Metric | Value |
|---|---:|
| Overlapping weeks | 157 |
| TSM Sharpe | 0.987 |
| Carry Sharpe | 1.109 |
| **Blend Sharpe** | **1.510** |
| Stream correlation | -0.037 |
| TSM max drawdown (risk units) | 5.883 |
| Blend max drawdown (risk units) | 4.895 |

## Sub-period stability (Sharpe: TSM / Carry / Blend; corr)

| Period | TSM | Carry | Blend | Corr |
|---|---:|---:|---:|---:|
| 2023-06_2024-05 | 1.432 | 1.018 | 1.688 | +0.054 |
| 2024-06_2025-05 | 0.648 | 1.650 | 1.587 | +0.049 |
| 2025-06_2026-05 | 0.956 | 0.468 | 1.190 | -0.284 |

## Reading

Blend vs TSM Sharpe: 0.987 -> 1.510 (delta +0.523); stream correlation -0.037; carry Sharpe 1.109. Blend beats TSM in every sub-period: True; drawdown not worse: True. CANDIDATE for OOS: the blend beats the TSM alone overall AND in every sub-period, with low stream correlation and no worse drawdown.
