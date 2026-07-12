# TASK-ALT-008 -- Family B (Range-Vol Shape) + Family C (Amihud) Diagnostic

Per `docs/pre_registers/TASK-ALT-008.md` (ADR-0028). The last un-run DIRECTIONAL diagnostics on free bar data: range-shape estimators (B was only tested as a risk/regime signal) and bar-derived Amihud illiquidity (C was only tested via order-book depth). 6 causal features vs 24h and 4h forward return. Pure diagnostic. Sign-consistency across 3 sub-periods is the pre-committed multiple-testing defense for the 12-cell grid.

Target: forward_return_h = log_price[t+h] - log_price[t], h in [24, 4]. Threshold: |rho| >= 0.03.

## Results

| Feature @ horizon | Full rho | Sub (2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05) | Sign consistent | Has info |
|---|---:|---|---|---|
| parkinson_range_z@24h | +0.0213 | +0.0367 | +0.0517 | -0.0351 | False | False |
| rogers_satchell_z@24h | +0.0215 | +0.0347 | +0.0508 | -0.0341 | False | False |
| close_location_in_range@24h | -0.0058 | -0.0113 | -0.0112 | +0.0038 | False | False |
| amihud_illiq_z@24h | +0.0018 | +0.0205 | -0.0051 | -0.0039 | False | False |
| turnover_z@24h | +0.0234 | +0.0227 | +0.0582 | -0.0201 | False | False |
| trade_size_z@24h | +0.0006 | -0.0092 | -0.0065 | +0.0146 | False | False |
| parkinson_range_z@4h | +0.0270 | +0.0320 | +0.0375 | +0.0072 | True | False |
| rogers_satchell_z@4h | +0.0268 | +0.0294 | +0.0380 | +0.0080 | True | False |
| close_location_in_range@4h | -0.0195 | -0.0282 | -0.0223 | -0.0086 | True | False |
| amihud_illiq_z@4h | +0.0039 | +0.0135 | +0.0007 | +0.0001 | True | False |
| turnover_z@4h | +0.0179 | +0.0198 | +0.0308 | +0.0000 | True | False |
| trade_size_z@4h | -0.0057 | -0.0098 | -0.0055 | -0.0026 | True | False |

## Reading

No range-shape or liquidity feature carries directional information at 24h or 4h. Families B (Volatility) and C (Liquidity) move from ~Concluida to CONCLUIDA on public data: no economically-relevant directional information in range-vol shape or bar-derived Amihud illiquidity in this universe/period. The public-data family sweep is complete; only external-data families (options VRP, on-chain, cross-venue flow) remain -- their acquisition is a user investment decision.
