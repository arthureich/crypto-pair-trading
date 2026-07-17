# TASK-TSM-013 -- Statistical characterization of TSM robustness

DESCRIPTIVE synthesis of committed validation artifacts (TSM-008/009/010/
011/012). No backtest run; no parameter changed. Pre-registered in
`docs/pre_registers/TASK-TSM-013.md`. Crypto (in-domain) and TradFi
(out-of-domain) reported SEPARATELY, never pooled.

## Population A -- CRYPTO (in-domain), base TSM (fixed params)

- Universes (n=7): original_20, defi, gaming, large_cap, mid_alt_l1, mid_tier_ref, old_guard
- **Sharpe**: n=7 mean=0.783 sd=0.220 min=0.462 med=0.832 max=1.004  CV=0.28
  - bootstrap 95% CI of mean (seed=0, 10000 resamples): [0.628, 0.928]
  - t-Student 95% CI of mean (cross-check): [0.579, 0.987]
- **maxDD**: n=7 mean=0.629 sd=0.184 min=0.347 med=0.745 max=0.801
- **net**: n=7 mean=1.355 sd=0.447 min=0.738 med=1.267 max=2.186
- Positive in **100%** of universes; beats buy-hold in **100%**

### Degradation map (ranked by base Sharpe)

| Universe | base Sharpe |
|---|---|
| old_guard | 0.462 |
| mid_tier_ref | 0.577 |
| mid_alt_l1 | 0.650 |
| defi | 0.832 |
| original_20 | 0.970 |
| large_cap | 0.987 |
| gaming | 1.004 |

Best `gaming`, worst `old_guard`, spread 0.543.

## Overlay (combined ERC+vol-target minus base), n=7

- delta Sharpe: n=7 mean=-0.027 sd=0.178 min=-0.263 med=-0.040 max=0.213
- combined beats base Sharpe in **43%** of universes
- combined has lower maxDD in **29%** of universes

## Temporal (fixed sub-periods, where saved)

- Coverage: 1/7 crypto universes have saved sub-periods (original_20)
  - 2023-06_2024-05: n=1 mean=1.556 sd=0.000 min=1.556 med=1.556 max=1.556
  - 2024-06_2025-05: n=1 mean=0.586 sd=0.000 min=0.586 med=0.586 max=0.586
  - 2025-06_2026-05: n=1 mean=0.975 sd=0.000 min=0.975 med=0.975 max=0.975
- Weakest sub-period (by mean): **2024-06_2025-05**

## Population B -- TradFi (OUT-OF-DOMAIN, reported separately)

- Sharpe: n=4 mean=-0.037 sd=0.225 min=-0.294 med=-0.015 max=0.176
- maxDD: n=4 mean=0.133 sd=0.055 min=0.073 med=0.129 max=0.204   net: n=4 mean=-0.012 sd=0.073 min=-0.110 med=0.003 max=0.058
- Positive in 50%; beats buy-hold in 0% (documented limit, TSM-012)
- Per class: commodities 0.176, etfs 0.126, forex -0.157, indices -0.294

## Reading

CRYPTO (in-domain, n=7): base TSM Sharpe mean 0.783 (median 0.832, sd 0.220, CV 0.28), bootstrap 95% CI [0.628, 0.928] (t-CI [0.579, 0.987]). Positive in 100% of universes, beats buy-hold in 100%. STATISTICALLY ROBUST IN-DOMAIN (crypto): the mean base-TSM Sharpe is positive with a 95% CI that EXCLUDES zero, and it is positive in every universe -- the edge is a stable cross-universe property, not a lucky draw.

DEGRADATION: strongest in 'gaming', weakest in 'old_guard' (spread 0.543 Sharpe) -- degradation is graceful (worst universe still positive), not a cliff. Weakest sub-period across covered runs: 2024-06_2025-05.

OVERLAY (combined ERC+vol-target - base): mean delta Sharpe -0.027; combined beats base in only 43% of universes -> confirms the overlays are partly universe-specific; the base vol-targeted TSM is the robust CORE.

TRADFI (OUT-OF-DOMAIN, n=4, reported SEPARATELY -- NEVER pooled with crypto): base Sharpe mean -0.037, positive in 50%, beats buy-hold in 0% -- the documented limit (TSM-012). Descriptive synthesis only; no promotion, no parameter change.
