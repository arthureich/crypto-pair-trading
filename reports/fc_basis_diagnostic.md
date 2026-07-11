# TASK-FC-II-002 -- Spot-Futures Basis Information-Content Diagnostic

Per `docs/pre_registers/TASK-FC-II-002.md` (ADR-0027). Pure diagnostic: no economic gate. The decisive column is INCREMENTAL information over funding (partial Spearman controlling for `funding_rate_asof`) -- a feature that passes only the standard test but not the incremental one is merely re-expressing the carry we already have.

Target: forward_return_24h = log_price[t+24h] - log_price[t]. Threshold: 0.03.

## Results

| Feature | Standard rho | Standard sub (2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05) | Has info | Partial rho \| funding | Partial sub | Incremental info |
|---|---:|---|---|---:|---|---|
| basis_level | -0.0023 | -0.0148, -0.0017, -0.0154 | False | +0.0082 | -0.0021, +0.0125, -0.0041 | False |
| basis_zscore | +0.0060 | +0.0067, +0.0239, -0.0209 | False | +0.0110 | +0.0221, +0.0356, -0.0121 | False |
| basis_change_24h | -0.0128 | -0.0318, -0.0018, -0.0058 | False | -0.0121 | -0.0312, -0.0007, -0.0035 | False |
| basis_excess_funding | +0.0025 | -0.0142, +0.0077, -0.0064 | False | +0.0091 | -0.0042, +0.0159, -0.0053 | False |

## Reading

No feature carries information INCREMENTAL to the funding rate. The basis adds nothing beyond the carry already captured by funding in this universe/period -- consistent with the Family G null. Basis closes as a standalone avenue; move to a source with higher independent-information prior (options IV/skew, on-chain), accepting their higher data-acquisition cost.
