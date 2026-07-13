# TASK-ALT-012 -- VRP-Timing Strategy Dev Run (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-ALT-012.md` (ADR-0032). Primary: long/short sign(vrp_z) weekly BTC/ETH book vs equal-weight buy-and-hold. Signal = the exact ALT-011 vrp_z; non-overlapping weekly rebalance (corrects the decile check's overlapping-sample bias). **Development-window result -- NOT a promotion; OOS-gated.** Long-only is a DESCRIPTIVE secondary (never promoted).

## Headline (full dev window)

| Metric | Long/short (primary) | Buy-and-hold | Long-only (secondary) |
|---|---:|---:|---:|
| Sharpe | 0.493 | 0.349 | 0.601 |
| Max drawdown | 0.7874 | 0.7741 | 0.5005 |
| Net PnL | 0.6924 | 0.5433 | 0.7582 |
| Mean turnover | 0.4615 | -- | 0.3269 |
| Rebalances | 156 | 156 | 156 |

## Sub-period stability (primary long/short Sharpe: strat vs buy-hold)

| Period | Strat | Buy-hold |
|---|---:|---:|
| 2023-06_2024-05 | 0.788 | 1.708 |
| 2024-06_2025-05 | -0.480 | -0.098 |
| 2025-06_2026-05 | 1.170 | -0.460 |

## BTC regime (primary Sharpe: strat vs buy-hold)

| Regime | Strat | Buy-hold |
|---|---:|---:|
| BTC_up | 0.923 | 1.389 |
| BTC_down | 0.043 | -0.776 |

## Cost sensitivity (primary strat Sharpe)

| Cost bps/leg | Strat Sharpe |
|---|---:|
| 0 | 0.524 |
| 6 | 0.493 |
| 15 | 0.447 |
| 30 | 0.371 |

## Reading

Primary long/short: Sharpe 0.349 (buy-hold) -> 0.493 (delta +0.144); maxDD 0.7874 vs buy-hold 0.7741 (<= baseline: False); beats buy-hold in every sub-period: False. REJECTED as a standalone-strategy candidate by the pre-registered criterion: the primary long/short improves Sharpe and net PnL over buy-and-hold but does NOT satisfy maxDD <= baseline and/or sub-period consistency. The VRP signal is real (ALT-011) but a naive long/short weekly trade is a modest, drawdown-heavy standalone. The long-only SECONDARY looks better (higher Sharpe, much lower drawdown) -- but it is descriptive-only and CANNOT be promoted here (no ex-post secondary promotion); it would need its OWN pre-registration. Best use of VRP is likely as a FEATURE/overlay, not a standalone trade. No promotion; OOS-gated.
