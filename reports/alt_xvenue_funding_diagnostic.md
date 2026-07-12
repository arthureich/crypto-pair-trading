# TASK-ALT-010 -- Cross-Venue Funding Dispersion Information-Content Diagnostic

Per `docs/pre_registers/TASK-ALT-010.md` (ADR-0030). Second half of the free-tier external-data path (Coinalyze, ZERO cost). Cross-venue funding across {Binance, Bybit, OKX, Huobi, BitMEX} (>= 3 venues/day), 3 causal daily features vs 1d and 3d forward daily return. Disclosed prior: single-venue funding / OI / aggregate flow were all null; the bet is specifically on cross-venue DISAGREEMENT. Sign-consistency across 3 sub-periods is the pre-committed multiple-testing defense for the 6 cells.

Target: forward_return_h = daily_log_price[D+h] - daily_log_price[D], h in [1, 3] days. Threshold: |rho| >= 0.03.

## Results

| Feature @ horizon | Full rho | n | Sub (2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05) | Sign consistent | Has info |
|---|---:|---:|---|---|---|
| xvenue_funding_disp_z@1d | +0.0267 | 20080 | +0.0173 | +0.0533 | +0.0067 | True | False |
| xvenue_funding_range_z@1d | +0.0280 | 20080 | +0.0194 | +0.0543 | +0.0074 | True | False |
| xvenue_funding_mean_z@1d | +0.0011 | 20080 | +0.0248 | +0.0173 | -0.0285 | False | False |
| xvenue_funding_disp_z@3d | +0.0395 | 20040 | +0.0082 | +0.1045 | -0.0069 | False | False |
| xvenue_funding_range_z@3d | +0.0404 | 20040 | +0.0072 | +0.1068 | -0.0057 | False | False |
| xvenue_funding_mean_z@3d | +0.0181 | 20040 | +0.0399 | +0.0294 | -0.0099 | False | False |

## Reading

No cross-venue funding feature passes BOTH criteria (|rho| >= 0.03 AND sign-consistent across the 3 sub-periods). The cross-venue flow half closes SEM_INFORMACAO. This exhausts the FREE-TIER external-data avenue (on-chain ALT-009 + cross-venue ALT-010 both null): what remains is paid feeds (premium on-chain, options surface) and the options-book instrument pivot -- all user spend/instrument decisions.

### Documented near-miss (NOT a hit)

The dispersion features (`disp`/`range`, positive: venues disagreeing -> higher forward return) are the most structured near-miss of the whole external-data search, but NON-PERSISTENT:

- Cleared magnitude, failed sign-consistency: xvenue_funding_disp_z@3d, xvenue_funding_range_z@3d. The full-sample rho is driven ENTIRELY by the middle sub-period (2024-06/2025-05, rho ~+0.10); the first is ~flat and the most recent sub-period is slightly NEGATIVE -- a one-regime mirage the 3-sub-period rule is built to reject.
- Sign-consistent but sub-threshold: xvenue_funding_disp_z@1d, xvenue_funding_range_z@1d. All three sub-periods positive but the full rho is just under 0.03, again concentrated in that same middle window.

Reading: cross-venue funding dispersion had a directionally-coherent edge in ONE ~12-month regime that has since decayed (the same efficiency-decay seen in OI/order-flow). Recorded, not promoted; no threshold adjustment. A future genuinely-new OOS window would test whether the mid-2024/2025 effect ever returns -- not a re-test of this.
