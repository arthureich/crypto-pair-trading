# TASK-ML-001 -- Meta-Labeling CV Model/Threshold Selection (development)

Per `docs/pre_registers/TASK-ML-001.md` / ADR-0026. **This is a development run: no promotion verdict.** The pre-registered PROMOTE/NAO_PROMOVE gate stays BLOCKED until a genuinely new OOS holdout (>=500 resolved rebalances after 2026-05-31) exists.

Window: existing (bars `C:\Users\arthu\Desktop\Aula\Projects\Crypto-Pair-Trading\data\research\binance_public\normalized\sprint7_binance_usdm_202306_202605_bars.csv.gz`). Primary signal: funding carry incremental K=5 (unaltered). Purged/embargoed CV: 5 folds, embargo 8h. Grid: 24 cells. Threshold candidates: [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7].

## Selected (on CV folds only)

- Hyperparameters: `{'max_depth': 3, 'n_estimators': 100, 'learning_rate': 0.03, 'min_child_weight': 5}`
- Threshold: 0.6
- Mean fold filtered profit factor: 4.9893
- Panel rows (entries): 30140

## Per-fold detail (winning candidate)

| Fold | Filtered PF | Filtered net PnL (bps) | Kept rebalances | Baseline PF |
|---:|---:|---:|---:|---:|
| 1 | 0.5459 | -160.36 | 503 | 1.1204 |
| 2 | 0.3429 | -920.58 | 502 | 1.2422 |
| 3 | 11.1835 | 169.21 | 502 | 1.3096 |
| 4 | 0.9244 | -7.13 | 502 | 0.8762 |
| 5 | 11.9500 | 7.42 | 502 | 1.0573 |

## Interpretation limits

The mean fold filtered PF above is an in-development CV estimate on the SAME window the K=5 near-miss (1.0904) was observed on. It is NOT evidence of edge and does NOT clear any gate. The only admissible verdict comes from the untouched new-OOS holdout, per ADR-0026's four-condition gate (filtered PF >= 1.10; net PnL > 0; >= 500 kept rebalances; filtered PF exceeds the unfiltered K=5 baseline by >= +0.02).

WARNING -- read the per-fold table, not the headline mean. Profit factor is a ratio: a fold that keeps only a few tiny winning intervals and cuts losers shows a huge PF on negligible net PnL. A high mean PF driven by one or two such folds, while other folds are net-negative or below their baseline, is a ratio artifact / overfit signal, not a robust improvement. Judge the filter by whether it beats the baseline consistently AND with real net PnL across folds.

## Development finding (2026-07-09)

This selected candidate's mean fold PF of 4.99 is exactly such an artifact. It is driven by folds 3 and 5 (PF 11.18 and 11.95) whose net PnL is negligible (+169 and +7 bps). In 3 of the 5 folds the filter is WORSE than doing nothing: fold 1 net -160 bps (baseline PF 1.12), fold 2 net -920 bps (baseline PF 1.24), fold 4 PF 0.92. So the meta-labeling filter shows no stable, real improvement in development -- it looks like fitting noise, consistent with the mean-PF objective rewarding ratio inflation over tiny PnL. This is a cautionary/negative development signal; it does not (and cannot) settle anything, but it lowers the prior that the eventual new-OOS test will clear the gate.
