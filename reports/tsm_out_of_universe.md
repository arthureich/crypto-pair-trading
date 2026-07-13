# TASK-TSM-009 -- Out-of-Universe Generalization Test (combined TSM)

Per `docs/pre_registers/TASK-TSM-009.md` (ADR-0031). The FIXED combined ERC + vol-targeting TSM (config from TASK-TSM-008, ZERO re-tune) run on a DIFFERENT liquid-USDM-perp universe (not the original 20), coverage-gated. Does the edge generalize? Breadth-robustness (cross-universe) evidence -- not a live promotion.

New universe (coverage gate 95%): AAVEUSDT, ALGOUSDT, AXSUSDT, CRVUSDT, FILUSDT, GRTUSDT, ICPUSDT, MANAUSDT, NEARUSDT, SANDUSDT.

## Headline (full window)

| Metric | Combined | Base TSM | Buy-and-hold |
|---|---:|---:|---:|
| Sharpe | 0.3347 | 0.5765 | -0.4286 |
| Max drawdown | 0.9330 | 0.8014 | 1.9943 |
| Net PnL | 0.6732 | 1.1262 | -1.0102 |

## Sub-period Sharpe (combined vs buy-hold)

| Period | Combined | Buy-and-hold |
|---|---:|---:|
| 2023-06_2024-05 | 1.0480 | 0.4996 |
| 2024-06_2025-05 | 0.1235 | -0.5302 |
| 2025-06_2026-05 | 0.0477 | -1.4248 |

## Reading

CORE TSM EDGE GENERALIZES: on a different 10-alt universe both base (0.577) and combined (0.335) beat buy-and-hold (-0.429) with positive net, in every sub-period -- trend-following is a GENERAL crypto-perp edge, not an artifact of the original 20. Raises confidence in the base TSM lead. BUT the overlays (ERC + vol-target) DO NOT generalize: combined 0.335 < base 0.577 here (and worse drawdown 0.933 vs 0.801) -- the OPPOSITE of the original universe (combined 1.183 > base 0.970). The clean-looking ERC+vol-target wins are PARTLY UNIVERSE-SPECIFIC; this TEMPERS confidence in the combined candidate. Also the absolute edge is weaker here (base 0.577) than on the original 20 (0.970).
