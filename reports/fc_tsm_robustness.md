# TASK-FC-II-006 -- Vol-Targeted TSM Robustness Decomposition

Per `docs/pre_registers/TASK-FC-II-006.md` (ADR-0027). Descriptive, in-sample; NO verdict. Decides whether the TSM lead (FC-II-005) is broad (worth OOS) or fragile (concentrated in a sub-period / the short leg / a single BTC regime).

## By sub-period

| Sub-period | Sharpe | Net PnL | Max drawdown | N |
|---|---:|---:|---:|---:|
| 2023-06_2024-05 | 1.708 | 0.6329 | 0.2014 | 74 |
| 2024-06_2025-05 | 0.613 | 0.3270 | 0.3489 | 73 |
| 2025-06_2026-05 | 1.015 | 0.4035 | 0.2394 | 72 |

## By leg (same book; long + short = gross)

- Long sleeve net PnL: 0.6739 (Sharpe 0.635)
- Short sleeve net PnL: 0.7496 (Sharpe 0.697)

## By BTC regime (28d trailing sign at each rebalance)

- BTC up: Sharpe 0.996, net 0.7613 (n=126)
- BTC down: Sharpe 1.126, net 0.6021 (n=87)

## Reading

BROAD: positive across all 3 sub-periods, the long leg contributes, and it works in both BTC regimes. The lead is not a single-regime artifact -> merits a separately pre-registered OOS pursuit.
