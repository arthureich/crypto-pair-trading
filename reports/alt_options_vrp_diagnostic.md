# TASK-ALT-011 -- Family F (Options) DVOL/VRP-as-Predictor Diagnostic

Per `docs/pre_registers/TASK-ALT-011.md` (ADR-0032). Free Deribit DVOL (keyless, ZERO cost) + DVOL-derived features vs 7d and 30d forward BTC/ETH return. Angle B (predictor for the perp strategy) -- NO options-book pivot. Pure diagnostic. BTC/ETH-only -> 2-asset pooled panel (low cross-sectional breadth, flagged). Sign-consistency across 3 sub-periods is the multiple-testing defense for the 8-cell grid.

Target: forward_return_h = daily_log_price[D+h] - daily_log_price[D], h in [7, 30] days. Threshold: |rho| >= 0.03.

## Results

| Feature @ horizon | Full rho | n | Sub (2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05) | Sign consistent | Has info |
|---|---:|---:|---|---|---|
| dvol_z@7d | +0.0542 | 1996 | -0.0911 | +0.1877 | -0.0239 | False | False |
| vrp_z@7d | +0.0866 | 1936 | +0.0879 | +0.0461 | +0.1095 | True | True |
| dvol_change_z@7d | +0.0205 | 1994 | +0.0935 | +0.0136 | -0.0321 | False | False |
| iv_rv_ratio_z@7d | +0.0518 | 1936 | +0.1409 | -0.0041 | +0.0810 | False | False |
| dvol_z@30d | +0.0280 | 1950 | -0.3706 | +0.1326 | +0.1030 | False | False |
| vrp_z@30d | +0.1109 | 1890 | -0.0497 | +0.1270 | +0.1189 | False | False |
| dvol_change_z@30d | +0.0151 | 1948 | +0.0470 | +0.0407 | -0.0311 | False | False |
| iv_rv_ratio_z@30d | +0.0614 | 1890 | -0.0058 | +0.0894 | +0.0489 | False | False |

## Reading

Features with information: vrp_z@7d. Each must pass the descriptive economic check (gross decile spread vs cost) before becoming a perp-strategy feature -- information is not a tradeable edge. A real edge would only THEN raise the larger Angle-A options-book decision.
