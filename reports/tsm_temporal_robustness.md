# TASK-TSM-014 -- Temporal robustness of the base TSM

Per `docs/pre_registers/TASK-TSM-014.md` (ADR-0031). Base TSM (fixed FC-II-008, include_funding, zero re-tune) reconstructed OFFLINE from cached bars for 7 crypto universes. Windows declared a priori. Descriptive; no promotion, no parameter change. TradFi out-of-domain, not re-run.

## (A) Fixed sub-period Sharpe per universe (backfills TSM-013 to 7/7)

| Universe | 2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05 | full |
|---|---|---|---|---|
| original_20 | 1.556 | 0.586 | 0.975 | 0.970 |
| large_cap | 1.890 | 0.370 | 0.971 | 0.987 |
| mid_alt_l1 | 1.693 | 0.313 | 0.107 | 0.650 |
| defi | 1.409 | 0.924 | -0.015 | 0.832 |
| gaming | 1.530 | 0.486 | 1.243 | 1.004 |
| old_guard | 0.314 | 0.502 | 0.592 | 0.462 |
| mid_tier_ref | 1.331 | 0.324 | 0.044 | 0.577 |

Cross-universe by sub-period:

- 2023-06_2024-05: mean 1.389, sd 0.508, min 0.314, max 1.890, positive 100%
- 2024-06_2025-05: mean 0.501, sd 0.212, min 0.313, max 0.924, positive 100%
- 2025-06_2026-05: mean 0.559, sd 0.518, min -0.015, max 1.243, positive 86%

Weakest sub-period: **2024-06_2025-05**. Negative (universe, sub-period) cells: 1.

## (B) Rolling-window Sharpe (W6=37 ~6mo, W12=73 ~12mo, step 1)

| Universe | W6 %pos | W6 min/med/max | W6 longest neg | W12 %pos | W12 min/med/max | W12 longest neg |
|---|---|---|---|---|---|---|
| original_20 | 85% | -0.896/1.015/2.568 | 13 | 100% | 0.203/0.851/1.784 | 0 |
| large_cap | 92% | -0.909/1.077/3.244 | 9 | 100% | 0.358/0.881/1.942 | 0 |
| mid_alt_l1 | 69% | -2.619/0.626/3.268 | 29 | 77% | -0.783/0.412/2.257 | 26 |
| defi | 75% | -2.642/1.142/2.817 | 35 | 85% | -0.594/0.868/1.592 | 20 |
| gaming | 81% | -2.145/1.077/3.440 | 20 | 100% | 0.134/0.753/1.702 | 0 |
| old_guard | 72% | -1.679/0.401/2.412 | 14 | 88% | -0.740/0.581/1.253 | 18 |
| mid_tier_ref | 68% | -2.007/0.683/2.782 | 28 | 87% | -0.571/0.438/1.710 | 18 |

Pooled: W6 77% of 1281 windows positive; W12 91% of 1029.

## (C) Drawdown duration (time underwater)

| Universe | max DD duration (days) | frac underwater |
|---|---|---|
| original_20 | 155 | 83% |
| large_cap | 135 | 79% |
| mid_alt_l1 | 415 | 85% |
| defi | 415 | 85% |
| gaming | 300 | 81% |
| old_guard | 200 | 89% |
| mid_tier_ref | 415 | 87% |

## Reading

TEMPORALLY ROBUST (in-domain crypto): the base TSM holds across time, not just in one hot window.

(A) SUB-PERIODS (n=7 universes x 3 fixed windows, backfills TSM-013 coverage to 7/7): cross-universe mean Sharpe by period -- 2023-06_2024-05 1.39 (pos 100%), 2024-06_2025-05 0.50 (pos 100%), 2025-06_2026-05 0.56 (pos 86%). Weakest: **2024-06_2025-05**; negative cells: defi/2025-06_2026-05 -0.02. Every universe positive in >=2/3 sub-periods: True.

(B) ROLLING WINDOWS (pooled across universes): W6(~6mo) 77% of windows positive; W12(~12mo) 91%. Majority positive: True.

(C) DRAWDOWN DURATION (honest risk feature, NOT sugar-coated): worst peak-to-recovery across universes = 415 days (~14 months), and time-underwater is high (79-89%). Two caveats: (i) the ~415d stretch lands in the mid/alt universes (mid_alt_l1, defi, mid_tier_ref) -- the SAME ones with the weakest FINAL sub-period, i.e. a long drawdown entered in the last year and likely not fully recovered by window-end; (ii) high time-underwater reflects a slow-grinding equity curve making infrequent new highs at MODEST depth (maxDD ~0.31-0.80, TSM-013), not deep losses. This is a real risk (long flat stretches, typical of trend-following), not dismissible -- the robustness verdict rests on (A)+(B), with this as the honest cost.

Descriptive temporal characterization; fixed params, a-priori windows, offline from cached bars; no promotion, no parameter change. TradFi (out-of-domain) not re-run here.
