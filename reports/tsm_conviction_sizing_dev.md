# TASK-TSM-002 -- Conviction Sizing Dev Run (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-TSM-002.md` (ADR-0031, Line 2). Base = vol-targeted TSM with funding (weight ~ sign(trailing)/vol); conviction = weight ~ trailing/vol (same direction and unit-gross exposure; strong trends carry more than weak ones). Params fixed a priori. **Development-window result -- NOT a promotion; promotion is OOS-gated.** The robustness battery is decisive per the pre-registration.

## Headline (full dev window)

| Metric | Base | Conviction |
|---|---:|---:|
| Sharpe | 0.970 | 0.888 |
| Max drawdown | 0.3470 | 0.3897 |
| Net PnL | 1.2672 | 1.3873 |
| Mean turnover | 0.4570 | 0.5657 |
| Rebalances | 219 | 219 |

## Sub-period stability (Sharpe)

| Period | Base | Conviction |
|---|---:|---:|
| 2023-06_2024-05 | 1.556 | 1.584 |
| 2024-06_2025-05 | 0.586 | 0.587 |
| 2025-06_2026-05 | 0.975 | 0.623 |

## BTC regime (Sharpe)

| Regime | Base | Conviction |
|---|---:|---:|
| BTC_up | 0.874 | 0.711 |
| BTC_down | 1.096 | 1.114 |

## Cost sensitivity (Sharpe)

| Cost bps/leg | Base | Conviction |
|---|---:|---:|
| 0 | 1.016 | 0.936 |
| 6 | 0.970 | 0.888 |
| 15 | 0.901 | 0.817 |
| 30 | 0.786 | 0.698 |
| 60 | 0.556 | 0.460 |

## Funding sensitivity (Sharpe)

| include_funding | Base | Conviction |
|---|---:|---:|
| False | 1.038 | 0.957 |
| True | 0.970 | 0.888 |

## Reading

Conviction vs base: Sharpe 0.970 -> 0.888 (delta -0.081); maxDD 0.3470 -> 0.3897 (delta +0.0427); mean turnover 0.4570 -> 0.5657 (delta +0.1086). Consistent across sub-periods AND BTC regimes: False. REJECTED as a dev candidate: no CONSISTENT risk-adjusted improvement (Sharpe up AND drawdown not worse, stable across all 3 sub-periods and both BTC regimes). Per the pre-registration, a gain seen only in aggregate or one regime is treated as a likely false positive. Hypothesis closed with this negative result; proceed to Line 3 (portfolio construction: risk parity / ERC / HRP).
