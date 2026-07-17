# TASK-TSM-011 -- Cross-Exchange Generalization (Bybit vs Binance)

Per `docs/pre_registers/TASK-TSM-011.md` (ADR-0031). The FIXED base TSM (FC-II-008, zero re-tune) run with the SAME code on Bybit and Binance, SAME 20 symbols. Cross-venue robustness, not a live promotion. Bybit funding is 8h (same as Binance).

## Headline (full window, same symbols both venues)

| Metric | Bybit | Binance |
|---|---:|---:|
| Base Sharpe | 0.9708 | 0.9698 |
| Max drawdown | 0.3409 | 0.3470 |
| Net PnL | 1.2697 | 1.2672 |
| Mean turnover | 0.4576 | 0.4570 |
| Buy-hold Sharpe | -0.1429 | -0.1429 |
| Rebalances | 219 | 219 |

## Sub-period base Sharpe

| Period | Bybit | Binance |
|---|---:|---:|
| 2023-06_2024-05 | 1.5501 | 1.5558 |
| 2024-06_2025-05 | 0.5857 | 0.5855 |
| 2025-06_2026-05 | 0.9815 | 0.9748 |

## Reading

Bybit base Sharpe 0.971 (buy-hold -0.143) vs Binance 0.970. GENERALIZES CROSS-EXCHANGE: on Bybit the base TSM Sharpe 0.971 is positive, beats buy-hold (-0.143), positive in every sub-period, and comparable to Binance (0.970). The edge is not an artifact of Binance microstructure -- it is a venue-independent trend property. CAVEAT on strength: same-symbol prices are tightly ARBITRAGED across venues, so near-identical results are EXPECTED -- this test mainly rules out Binance-specific data/microstructure artifacts; the cross-UNIVERSE tests (TSM-009/010, different assets) remain the stronger diversity evidence.
