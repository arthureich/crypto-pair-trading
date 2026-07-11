# TASK-FC-II-004 -- Family E (Flow) Information-Content Diagnostic

Per `docs/pre_registers/TASK-FC-II-004.md` (ADR-0027). Aggressor taker flow (bars) + long/short positioning ratios (metrics archives already on disk), 5 causal features vs 24h and 4h forward return. Pure diagnostic. Sign-consistency across 3 sub-periods is the multiple-testing defense for the 10-cell grid.

Target: forward_return_h = log_price[t+h] - log_price[t], h in [24, 4]. Threshold: 0.03.

## Results

| Feature @ horizon | Full rho | Sub (2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05) | Sign consistent | Has info |
|---|---:|---|---|---|
| taker_buy_fraction@24h | -0.0064 | -0.0111 | -0.0068 | -0.0015 | True | False |
| taker_buy_fraction_z@24h | -0.0065 | -0.0122 | -0.0057 | -0.0025 | True | False |
| taker_lsv_ratio_z@24h | -0.0031 | -0.0090 | -0.0080 | +0.0034 | False | False |
| toptrader_ls_ratio_z@24h | -0.0018 | +0.0201 | -0.0261 | +0.0044 | False | False |
| global_ls_ratio_z@24h | -0.0045 | -0.0266 | -0.0056 | -0.0014 | True | False |
| taker_buy_fraction@4h | -0.0104 | -0.0159 | -0.0145 | -0.0017 | True | False |
| taker_buy_fraction_z@4h | -0.0086 | -0.0133 | -0.0126 | -0.0019 | True | False |
| taker_lsv_ratio_z@4h | -0.0063 | -0.0041 | -0.0153 | +0.0020 | False | False |
| toptrader_ls_ratio_z@4h | -0.0014 | +0.0149 | -0.0093 | -0.0050 | False | False |
| global_ls_ratio_z@4h | -0.0006 | +0.0086 | -0.0044 | -0.0043 | False | False |

## Reading

No flow feature carries information at 24h or 4h. Family E (Flow) closes: no economically-relevant directional information in aggressor taker flow or long/short positioning ratios in this universe/period.
