# TASK-FC-II-003 -- Book Imbalance vs Short-Horizon Returns

Per `docs/pre_registers/TASK-FC-II-003.md` (ADR-0027). The 5 Family H features reused verbatim; only the forward-return target horizon changes (1h, 4h). Pure diagnostic, no gate. Sign-consistency across the 3 sub-periods is the multiple-testing defense for the 10-cell grid.

Target: forward_return_h = log_price[t+h] - log_price[t], h in [1, 4]. Threshold: 0.03.

## Results

| Feature @ horizon | Full rho | Sub (2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05) | Sign consistent | Has info |
|---|---:|---|---|---|
| book_imbalance_1pct@1h | +0.0129 | +0.0191 | +0.0203 | +0.0053 | True | False |
| book_imbalance_5pct@1h | +0.0146 | +0.0269 | +0.0118 | +0.0092 | True | False |
| depth_concentration@1h | -0.0023 | -0.0091 | -0.0045 | +0.0058 | False | False |
| depth_change_24h@1h | -0.0023 | -0.0141 | -0.0036 | +0.0091 | False | False |
| imbalance_price_divergence@1h | +0.0350 | +0.0444 | +0.0384 | +0.0253 | True | True |
| book_imbalance_1pct@4h | -0.0017 | -0.0043 | +0.0026 | +0.0013 | False | False |
| book_imbalance_5pct@4h | +0.0058 | +0.0124 | -0.0023 | +0.0103 | False | False |
| depth_concentration@4h | -0.0068 | -0.0180 | -0.0091 | +0.0054 | False | False |
| depth_change_24h@4h | -0.0097 | -0.0196 | -0.0100 | -0.0008 | True | False |
| imbalance_price_divergence@4h | +0.0337 | +0.0332 | +0.0375 | +0.0309 | True | True |

## Reading

Features with information at a short horizon: imbalance_price_divergence@1h (rho +0.0350), imbalance_price_divergence@4h (rho +0.0337), both sign-consistent across the 3 sub-periods. This is the first *directional* feature in the project to clear the information-content criterion in a genuinely new test, and it is theory-coherent (order-book imbalance informs short-horizon returns) and not a random hit among 10 -- it is the pre-identified 24h near-miss crossing the threshold at exactly the horizon microstructure theory predicts.

## Economic reality check (in-sample, descriptive) -- ABORT before strategy

Information is not a tradeable edge, and short horizons are where cost dominates. Gross cross-sectional top-decile-minus-bottom-decile forward return per interval for `imbalance_price_divergence`: **median ~+1.06 bps @1h and ~+2.05 bps @4h, with a NEGATIVE mean (-1.32, -2.56 bps)** dragged by fat tails (n~21,900 intervals). At 1-4h turnover this is dwarfed by a realistic ~6-12 bps round-trip cost -- and the negative mean means it is not even robustly positive gross.

Verdict: **statistically real information, economically negligible** -- the exact pattern of the z-score micro-reversion the project already ABORTED (1.643 bps vs a 10 bps threshold). No strategy pre-registration is warranted; taking it to OOS would burn a scarce validation window on a signal that cannot survive cost. Logged as a real diagnostic finding, closed on economics. This also exhausts the cheap-to-test angles on the data we already hold; further factor search requires external data (options IV/skew, on-chain, cross-exchange), which is a data-acquisition decision.
