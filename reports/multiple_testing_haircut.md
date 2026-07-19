# Multiple-Testing Statistical Haircut (TASK-DEPLOY-001, Phase 6)

How much of the canonical TSM's evidence survives higher moments, finite sample, and the number of hypotheses the program tried. Canonical stream = original-20, n=219 rebalances. No promotion; descriptive.

## Canonical Sharpe under scrutiny

- Annualized Sharpe: **0.970** (per-period 0.1135)
- Skew 0.454, kurtosis 4.323 (non-excess)
- **PSR vs 0** (prob true SR > 0): **0.9565**
- Block-bootstrap 95% Sharpe CI (annualized, block=10, seed=0): **[-0.051, 1.942]**

## Deflated Sharpe Ratio (correcting for selection across trials)

- Trial Sharpe variance (per-period, from 7 TSM-family variants): 0.000865
- Expected MAX Sharpe (annualized) under N direct trials (7): 0.349; under N program hypotheses (24): 0.498
- **DSR (direct, N=7): 0.8635**
- **DSR (whole program, N=24): 0.7976**

## Cross-universe dependence (7 universes are NOT 7 independent tests)

- Average pairwise correlation of the 7 base streams: **0.827**
- Effective independent universes: **1.17** (of 7) -> the cross-universe breadth is worth far fewer than 7 independent bets.

## PnL concentration

- Months: 36; best-month share of total: **0.3769**; top-3-month share: **0.7088**

## PBO / CSCV

NOT reliably estimable under the available experiment structure (few pre-registered variants, not a large combinatorial config grid on the same data). Not fabricated.

## Reading -- a MIXED, sobering picture (fact / assumption / limitation)

The multiple-testing correction is REASSURING, but three dependence/finite-sample facts cut the other way and are the honest haircut:

- REASSURING (FACT): under iid assumptions PSR vs 0 = 0.956, and even deflating for the whole 24-hypothesis program the DSR stays high (0.798) -> the lead is not plausibly the luckiest of many random trials (and the trials are mostly the same TSM family, so the naive count over-states selection risk).
- SOBERING (FACT): the block-bootstrap Sharpe CI (serial-dependence aware) is **[-0.051, 1.942] -- it INCLUDES zero**. So on the single 3-year stream the Sharpe is NOT conclusively above zero once autocorrelation is respected; the iid PSR is optimistic.
- SOBERING (FACT): the 7 crypto universes are 0.83-correlated -> only ~1.2 EFFECTIVE independent universes. 'Positive in 7/7' (TSM-010/013) is worth roughly ONE independent bet, not seven -- the breadth claim was materially overstated.
- SOBERING (FACT): PnL is CONCENTRATED -- the best month is 0.38 of total and the top 3 months are 0.71 of total return; the edge is episodic, not steady.
- ASSUMPTION: trial Sharpe variance from the 7 original-20 TSM variants; block bootstrap block=10 rebalances. PBO/CSCV not estimable here (documented, not faked).
- NET: the edge SURVIVES multiple-testing selection (DSR high), but its effective statistical weight is much THINNER than the raw '7/7, CI excludes zero' headline -- ~1 independent universe, a single-stream CI that touches zero, and episodic PnL. Honest verdict: a real but modest, dependence-discounted edge; the forward track (Phase 7) is what ultimately settles it.
