# TASK-TSM-004 -- Meta-Labeling Filter Dev Run (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-TSM-004.md` (ADR-0031, Line 4). TSM = primary (direction); a frozen GradientBoosting secondary model (6 causal features, threshold 0.5, purged+embargoed walk-forward CV) predicts P(leg profitable) and drops low-probability legs. **Development-window, out-of-fold result -- NOT a promotion (OOS-gated, like ML-001).** The per-fold table is the mirage guard: a gain from 1-2 folds is treated as a false positive.

Legs: 4258; base label rate (leg profitable): 0.507 (a razor-thin leg-level edge).

## Per-fold (purged walk-forward CV) -- mirage guard

| Fold | n | kept | base leg-PnL | filtered leg-PnL | base prec | filt prec |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 720 | 0.52 | +0.00651 | +0.01023 | 0.504 | 0.508 |
| 2 | 719 | 0.52 | +0.00821 | +0.00353 | 0.509 | 0.493 |
| 3 | 700 | 0.50 | +0.00399 | +0.01641 | 0.480 | 0.514 |
| 4 | 700 | 0.55 | +0.00465 | +0.00050 | 0.484 | 0.457 |
| 5 | 700 | 0.35 | +0.00390 | +0.00564 | 0.523 | 0.577 |

## Headline (OUT-OF-FOLD window)

| Metric | Base | Filtered |
|---|---:|---:|
| Sharpe | 0.784 | 0.412 |
| Max drawdown | 0.3470 | 0.5026 |
| Net PnL | 0.8855 | 0.4739 |
| Rebalances | 177 | 177 |

## Sub-period (OOF) Sharpe

| Period | Base | Filtered |
|---|---:|---:|
| 2023-06_2024-05 | 0.945 | 0.307 |
| 2024-06_2025-05 | 0.586 | 0.403 |
| 2025-06_2026-05 | 0.975 | 0.507 |

## BTC regime (OOF) Sharpe

| Regime | Base | Filtered |
|---|---:|---:|
| BTC_up | 0.613 | 0.263 |
| BTC_down | 1.008 | 0.598 |

## Cost sensitivity (OOF) Sharpe

| Cost bps/leg | Base | Filtered |
|---|---:|---:|
| 0 | 0.828 | 0.515 |
| 6 | 0.784 | 0.412 |
| 15 | 0.718 | 0.258 |
| 30 | 0.607 | 0.002 |

## Funding sensitivity (OOF) Sharpe

| include_funding | Base | Filtered |
|---|---:|---:|
| False | 0.844 | 0.451 |
| True | 0.784 | 0.412 |

## Reading

OOF base -> filtered: Sharpe 0.784 -> 0.412 (delta -0.372); maxDD 0.3470 -> 0.5026 (delta +0.1557). Filter beat base leg-PnL in 3/5 folds. REJECTED / CAUTIONARY: the meta-labeling filter does not deliver a consistent out-of-fold improvement. Consistent with the ML-001 lesson -- on a razor-thin leg-level edge (base precision ~0.50) ML manufactures fold-specific gains that do not survive purged out-of-fold evaluation. Hypothesis closed; proceed to Line 5 (ensemble). Gate BLOCKED until OOS regardless.
