# TASK-ALT-009 -- Family G (On-Chain) Information-Content Diagnostic

Per `docs/pre_registers/TASK-ALT-009.md` (ADR-0029). First EXTERNAL-data family tested -- and at ZERO cost (Coin Metrics community, keyless). 4 causal daily features vs 1d and 7d forward daily return. Pure diagnostic. Sign-consistency across 3 sub-periods is the pre-committed multiple-testing defense for the 8-cell grid. `exchange_netflow_z` is BTC/ETH-only (2 assets) -- pooled daily obs, NOT a cross-sectional result.

Target: forward_return_h = daily_log_price[D+h] - daily_log_price[D], h in [1, 7] days. Threshold: |rho| >= 0.03.

## Results

| Feature @ horizon | Full rho | n | Sub (2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05) | Sign consistent | Has info |
|---|---:|---:|---|---|---|
| mvrv_z@1d | +0.0069 | 10040 | -0.0039 | -0.0020 | +0.0021 | False | False |
| active_addr_growth_z@1d | +0.0072 | 11033 | +0.0235 | -0.0066 | +0.0121 | False | False |
| tx_count_growth_z@1d | +0.0045 | 11033 | -0.0085 | +0.0010 | +0.0184 | False | False |
| exchange_netflow_z@1d | -0.0169 | 2008 | -0.0515 | -0.0211 | +0.0157 | False | False |
| mvrv_z@7d | +0.0238 | 9980 | -0.0520 | +0.0186 | +0.0047 | False | False |
| active_addr_growth_z@7d | +0.0070 | 10967 | +0.0239 | -0.0117 | +0.0153 | False | False |
| tx_count_growth_z@7d | +0.0003 | 10967 | +0.0084 | -0.0068 | +0.0017 | False | False |
| exchange_netflow_z@7d | -0.0346 | 1996 | -0.0784 | +0.0042 | -0.0405 | False | False |

## Reading

No free-tier on-chain feature carries directional information at 1d or 7d by the pre-registered criterion (|rho| >= 0.03 AND sign-consistent across the 3 sub-periods). Family G closes on the ZERO-COST tier. Paying for premium on-chain metrics (Glassnode / CryptoQuant / CM premium) would need a stronger prior than 'the free proxies were null'. Cross-venue flow remains open, gated on a free Coinalyze/Coinglass key (TASK-ALT-010).

### Documented near-miss (NOT a hit)

exchange_netflow_z@7d: full-sample |rho| clears the 0.03 bar but sign-consistency FAILS, so it is SEM_INFORMACAO by the locked rule -- recorded, not promoted, no threshold adjustment. Notably `exchange_netflow_z@7d` (-0.0346) is theory-coherent (exchange inflows = sell pressure -> lower forward return) with 2 of 3 sub-periods clearly negative (-0.078, -0.041), only the middle period flat-positive (+0.004). BUT it is BTC/ETH-only (2 assets) -- a BTC/ETH-timing signal, not a cross-sectional factor. A richer / broader exchange-flow feed (e.g. CryptoQuant) MIGHT sharpen it; that is a paid-feed user decision, not a re-test of this.
