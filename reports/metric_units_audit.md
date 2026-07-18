# Metric-Units Audit -- TSM drawdown (TASK-DEPLOY-001, Phase 1)

Audits the `maxDD ~0.31-0.80` numbers previously described as 'modest/
shallow'. Canonical-core stream reconstructed offline for 7 crypto universes; drawdown reported in BOTH framings.

## VERDICT: option B -- unit/framing issue (not a calc bug)

The reported maxDD ~0.31-0.80 was in ADDITIVE fixed-notional units (cumulative P&L per unit gross via np.cumsum), NOT compounded equity percent. It is a UNIT/FRAMING issue, not a calculation bug: the additive numbers reproduce the legacy _max_drawdown exactly. The 'modest/shallow' wording was internally consistent with additive net PnL but MISLEADING against the '%' reading a reader assumes.

- Additive numbers reproduce legacy `_max_drawdown` exactly: **True**.
- Additive maxDD range (return units, fixed-notional): **0.347 - 0.801**.
- Compounded maxDD range (canonical equity %): **31.0% - 57.8%**.

So `0.80` did NOT mean an 80% equity drawdown; it meant cumulative losses reached 0.80 of one unit of gross notional (fixed-notional). The TRUE compounded drawdowns are shown below and are the numbers to quote going forward. Correcting the earlier 'shallow' characterization.

## Per-universe drawdown (canonical core, both framings)

| Universe | n | additive maxDD (ret units) | **compounded maxDD %** | duration (days) | time underwater | recovered? |
|---|---:|---:|---:|---:|---:|---|
| original_20 | 219 | 0.347 | **31.0%** | 140 | 85% | yes |
| large_cap | 219 | 0.419 | **36.2%** | 140 | 82% | yes |
| mid_alt_l1 | 219 | 0.769 | **57.1%** | 415 | 87% | no (UNRECOVERED) |
| defi | 219 | 0.749 | **55.6%** | 415 | 86% | no (UNRECOVERED) |
| gaming | 219 | 0.745 | **56.7%** | 315 | 84% | yes |
| old_guard | 219 | 0.571 | **45.1%** | 150 | 94% | yes |
| mid_tier_ref | 219 | 0.801 | **57.8%** | 280 | 89% | yes |

## Peak / trough / recovery timestamps (compounded)

| Universe | peak | trough | recovery | peak eq | trough eq |
|---|---|---|---|---:|---:|
| original_20 | 2024-06-30 | 2024-09-28 | 2024-11-17 | 1.838 | 1.268 |
| large_cap | 2024-06-30 | 2024-09-28 | 2024-11-17 | 2.054 | 1.310 |
| mid_alt_l1 | 2025-04-06 | 2026-01-21 | UNRECOVERED | 3.296 | 1.414 |
| defi | 2025-04-06 | 2025-09-28 | UNRECOVERED | 4.062 | 1.805 |
| gaming | 2025-04-11 | 2025-10-03 | 2026-02-20 | 3.826 | 1.656 |
| old_guard | 2024-06-30 | 2024-10-03 | 2024-11-27 | 1.227 | 0.674 |
| mid_tier_ref | 2024-06-30 | 2024-11-02 | 2025-04-06 | 2.422 | 1.021 |

## Fact / estimate / assumption / limitation

- FACT: the validation scripts computed drawdown as np.cumsum(returns) peak-to-trough (additive, fixed-notional); this audit reproduces those numbers exactly.
- FACT: under the canonical compounded formula, the maxDD figures are different and are the ones to quote as 'equity drawdown %'.
- ASSUMPTION: compounded equity reinvests P&L (bet size scales with equity); additive assumes constant notional. Both are legitimate; a real fixed-capital vol-targeted deployment sits between them.
- ASSUMPTION: NaN per-rebalance returns treated as 0.0 (flagged).
- LIMITATION: per-rebalance returns are gross-notional returns of a unit-gross long/short book; compounding a levered L/S book can drive equity non-positive (flagged per universe), which additive never shows.
- DECISION: quote COMPOUNDED maxDD % as the headline risk number going forward; keep additive clearly labeled where used. No strategy/parameter change; the drawdown metric is reporting, not economic logic.
