# Strategy Results & Feedback -- Consolidated Ledger

Single source of truth for **every strategy / hypothesis the project has
tested**, with results and the feedback/lesson from each, grouped by kind.
Supersedes `research_program_retrospective_2026-07.md` (which predates the
funding-carry incremental result, the ML/FC-II work, and the forward paper
track). Numbers are taken from the per-line reports in `reports/`, the
pre-registrations in `docs/pre_registers/`, and `project_control/DECISIONS.md`.
Last updated: 2026-07-11.

## Bottom line

**No strategy has passed its own pre-registered gate under realistic
execution cost.** Across ~13 backtested lines, every one closed NAO_PASSA /
REJECTED. The closest was **funding carry (incremental K=5): profit factor
1.0904 vs a 1.10 gate**, net PnL positive. Its first genuinely out-of-sample
month (June 2026) came in **negative (PF 0.78)** -- the in-sample near-miss
did not persist. Every information-content family testable on public data is
now closed; the one real directional signal found (`imbalance_price_divergence`
at short horizon) is economically negligible. The frontier is external data
(options / on-chain / high-res ticks), not more mining of the data we hold.

Verdict legend: **NAO_PASSA** = ran, failed its gate. **SEM_INFO** = no
information-content. **NEAR-MISS** = closest to passing. **ABORT** =
real information but economically negligible. **BLOCKED** = pre-registered,
waiting on data. **CAUTIONARY** = development signal, no verdict yet.

---

## Group 1 -- Backtested strategies (real trades, PnL, gate)

| Strategy | What | Gate | Result | Verdict | Feedback / lesson |
|---|---|---|---|---|---|
| Sprint 8 (Kalman/OU pairs) | Causal rolling z-score on a Kalman spread, 1h hold, 31 stat pairs | per-pair net PnL > 0 | 13/31 pairs net+, portfolio **-1,716 bps** (622 trades) | scoped pass (13 pairs) | Passed only under a loose median-spread cost model -- see Sprint 9 |
| Sprint 9 (executable) | Same 13 pairs through a real fill simulator (latency, partial fills, ACK) | per-pair net PnL > 0 | **0/13** net+, **-$2,266** | NAO_PASSA | The clearest lesson of the project: a simplified cost model "approved" 13 pairs; a real fill sim killed all 13 on the same data. Cost realism is decisive |
| Sprint 10 Block 1 (passive) | Same signals, LIMIT_MAKER_TTL vs MARKET_IOC | net PnL > 0 | still **0/13**, -$2,006, +27% unfilled exposure | NAO_PASSA | Negative result wasn't an artifact of aggressive execution; maker execution didn't rescue it |
| Sprint 8 Canonical (ADR-0009) | Triple-barrier over all 41 stat pairs, 6bps/leg + funding | PF >= 1.10/pair | **0/41**, portfolio PF **0.782**, -861,874 bps (62,878 trades) | NAO_PASSA | Best pair PF 0.960 -- still below gate. Stat-arb pairs have no edge net of cost here |
| Signal Iteration 1 (SIG-001..004) | Rescue attempts: 4h vertical cap, half-life entry filter, 5-min bars | net PF>=1.10 AND trades>=200 | tight filter net PF 0.833 (74 trades); 5-min net PF 0.4223 (23k) | REJECTED (ADR-0010) | No threshold clears the gate; exit/entry tweaks don't create edge |
| **Funding carry (phase 1, full rebalance)** | Long low-funding / short high-funding, K=5, rebalance every 8h | net PF >= 1.10 | K=5 PF **0.840**, -10,729 bps (3,287 rebalances) | NAO_PASSA | Gross edge real (+8,992 bps) but the 19,722 bps full-rebalance cost ate it |
| **Funding carry (incremental K=5)** | Same signal, hold unless swap yield > cost threshold | net PF >= 1.10 | PF **1.0904** (0.0096 short), net **+5,620 bps** | **NEAR-MISS** | Incremental rebalancing cut cost 99.83% (19,722 -> 33.6 bps) and flipped net positive. The project's best result. K=3 hit 1.1356 but is descriptive-only (no post-hoc K retune) |
| TSMOM (Donchian breakout) | 24h channel breakout + ATR trailing stop, 12bps cost | net PF>=1.20 AND win>=30% | win 34.3%, PF **1.005**, +8,187 bps, **maxDD 85,654 bps (~10x profit)** | NAO_PASSA | Trend-following exists but is drowned by whipsaw drawdown net of cost |
| TSREV (Family A, 24h, OOS) | z = r/sigma reversal, genuine OOS split | net PF>1.05 AND net>0 AND DD<=baseline AND trades>=200 | win **52.68%** (stable), PF 1.0143, +7,690 bps, **maxDD 65,720 vs 11,004 baseline (~6x)** | NAO_PASSA | A real, stable directional edge -- but fails decisively on drawdown. Structural risk problem, not a signal problem |
| Regime-conditioned TSREV (ALT-004) | Block TSREV entries in top-tercile realized vol | same 4-part TSREV gate | filtered PF **0.9822**, net **-6,110 bps** (worse) | NAO_PASSA | Counter-intuitive: TSREV's edge is CONCENTRATED in high vol; excluding it removed the profit |
| Cross-sectional momentum (CS-001) | Liu-Tsyvinski weekly momentum, top/bottom quintile K=4 | net PF>1.10 AND ... | PF **0.98**, -370 bps (408 legs); gross also negative | NAO_PASSA | No gross edge even before cost in this universe/period |
| Cross-sectional reversion (CS-002) | 24h-horizon reversion (distinct from CS-001 mirror) | same as CS-001 | PF **0.94** OOS; gross negative | NAO_PASSA | Closes the classical price-factor program (5 families, all NAO_PASSA) |

---

## Group 2 -- Information-content diagnostics (families)

Method (ADR-0019): Spearman rho vs 24h forward return, |rho| >= 0.03 AND
sign-consistent across 3 fixed 12-month sub-periods. Pure diagnostic, no gate.

| Family / task | Features | Result | Verdict | Feedback / lesson |
|---|---|---|---|---|
| G -- Funding structure (ALT-001) | 4 funding features | all SEM_INFO; `funding_price_divergence` near-miss rho 0.0248, stable + | SEM_INFO | 3 of 4 flip sign across sub-periods (spurious) |
| G -- funding_price_divergence new-OOS (ALT-005) | the one near-miss, on June 2026 | rho **-0.118** (sign INVERTED, ~4x larger) | NAO_PROMOVE | The canonical cautionary tale: a stable in-sample "signal" reversed on genuinely new data |
| F -- Open Interest (ALT-002) | 5 OI features | all SEM_INFO; oi_delta/oi_acceleration DECAY across sub-periods | SEM_INFO | Decaying signal = market getting more efficient over time |
| J -- Regime detection (ALT-003) | 6 vol/context features | **TEM_INFORMACAO** (realized_vol_168h rho 0.30, 24h rho 0.29) | INFO (risk/context) | The strongest signal in the project -- but risk/context, NOT directional alpha (its one operational test, ALT-004, failed) |
| H -- Order flow / bookDepth (ALT-007) | 5 book-imbalance features | all SEM_INFO; `imbalance_price_divergence` near-miss rho 0.0208, GROWING trajectory | SEM_INFO | Near-miss with a growing sub-period trajectory -> motivated the short-horizon retest (FC-II-003) |
| D -- Basis spot-futures (FC-II-002) | 4 basis features (premium index) | all SEM_INFO, standard AND incremental-over-funding (abs(rho)<0.013) | SEM_INFO | Basis adds nothing beyond the funding carry; premium index already in the bars (no download) |
| I -- Microstructure short-horizon (FC-II-003) | Family H features vs 1h/4h return | `imbalance_price_divergence` **TEM** (rho +0.035 @1h/4h, sign-consistent) | **ABORT** | First directional info hit in a new test, theory-coherent -- BUT gross decile spread ~1-2 bps vs 6-12 bps cost -> economically dead (like the z-score micro-reversion) |
| E -- Flow (FC-II-004) | taker aggressor + long/short ratios | all 10 cells SEM_INFO (abs(rho)<0.011) | SEM_INFO | Aggressor flow and positioning ratios carry no directional info |
| B+C -- Range-vol shape + Amihud (ALT-008) | Parkinson/Rogers-Satchell/close-location + Amihud/turnover/trade-size, 24h & 4h | all 12 cells SEM_INFO (max abs(rho) 0.027 < 0.03); range-vol magnitude highest but sub-threshold (vol-clustering, not directional); Amihud rho ~0.00 | SEM_INFO | Closes the DIRECTIONAL test of the two families the report cites (range vol, illiquidity premium). Public-data family sweep now complete: only external-data families remain |

---

## Group 3 -- ML & execution overlays (development phase, gate blocked until OOS)

| Task | What | Dev result | Verdict | Feedback / lesson |
|---|---|---|---|---|
| ML-001 -- meta-labeling filter | XGBoost gate on incremental K=5 legs (per-interval) | CV "best" mean fold PF **4.99** -- a RATIO-INFLATION MIRAGE (2 folds PF ~11-12 on tiny PnL; 3 of 5 folds worse than baseline) | CAUTIONARY (blocked) | On a 0.0096-thin edge, ML manufactures illusory in-sample "passes". The per-fold table, not the headline mean, tells the truth. Also: the incremental policy makes so few entries (~66/3yr) that entry-gating was data-starved -> switched to per-interval gating |
| FC-II-001 -- risk position sizing | inverse-vol weights + vol-targeting overlay on K=5 | Sharpe 0.993 -> **1.042 (+0.049 < +0.15 gate)**; maxDD **worse** (1582 -> 1725 bps) | CAUTIONARY (blocked) | PF-invariant by design (targets Sharpe/DD, not PF). Doesn't beat its own gate even in development. Sizing can't create edge |

---

## Group 4 -- Forward paper validation (genuine OOS, accruing)

| Track | What | Result so far | Status | Feedback / lesson |
|---|---|---|---|---|
| Funding carry K=5 paper-forward (ADR-0027) | Fixed K=5 on post-2026-05-31 data, marked to market | June 2026 (89 rebalances): PF **0.78**, net **-300 bps**, hit 49.4% | ACCRUING (411 short of 500 trigger) | Genuine OOS, cannot be look-ahead-contaminated. One month is noisy and NOT a verdict, but the in-sample 1.0904 did not carry into the first unseen month. Verdict at >= 500 rebalances (~mid-Nov 2026) |

---

## Group 5 -- Blocked / data-gated (pre-registered, not yet run)

| Task | What | Trigger | Feedback / lesson |
|---|---|---|---|
| PAYOFF-002 | SHORT-only TSREV (the leg that was +37,938 bps / WR 55.2% in attribution) | >= 500 new resolved trades after 2026-05-31 | Reverse-engineered from a seen result -> must be validated on genuinely new OOS, not the same window (data-mining discipline) |
| ALT-006 | TSREV restricted to high-vol regime (inverse of ALT-004) | >= 750 new resolved TSREV trades | Same data-mining discipline: the hypothesis was built from the ALT-004 decomposition |
| Family I -- Liquidations | Liquidation-cascade features | -- | BLOCKED permanently: Binance no longer publishes historical liquidationSnapshot data |

---

## Group 6 -- Informal aborts (killed before pre-registration)

| Probe | Result | Feedback / lesson |
|---|---|---|
| Z-score cross-sectional micro-reversion | Statistically consistent reversal (>51% in 9/9 combos) but **1.643 bps vs a 10 bps threshold** | The template for "real but economically negligible" -> ABORT before pre-registration. Repeated by FC-II-003 |
| TSMOM informal diagnostic | Trailing-vs-forward correlation negative in all 4 windows | Discouraged the hypothesis (the separately-authorized Donchian backtest also failed) |
| CS momentum/reversion informal diagnostic | 48-52% positive across windows = noise | Led to the formal CS backtests (also NAO_PASSA) at the user's request to replicate the literature |

---

## Family status matrix (information families)

| Family | Status | Basis |
|---|---|---|
| A -- Price | REOPENED (best lead) | pairs / TSREV / TSMOM(Donchian) / cross-sectional all NAO_PASSA -- BUT classic vol-targeted TSM (FC-II-005) beats buy-hold in-sample (Sharpe 1.04 vs -0.14, maxDD 0.35 vs 1.38) and has now survived EVERY in-sample stress: robust across the 3 sub-periods, both legs, and both BTC regimes (FC-II-006); cost breakeven 142 bps/leg (FC-II-007); and funding P&L only a ~7% haircut (Sharpe -> 0.97, FC-II-008). Params literature-fixed (not tuned). The project's strongest, most-validated lead. ONLY genuinely-new OOS remains. (Was wrongly marked CONCLUIDA.) |
| B -- Volatility | CONCLUIDA (public) | Family J: info but risk/context, not directional; ALT-008 directional test of range-shape (Parkinson/Rogers-Satchell/close-location) all SEM_INFO (max abs rho 0.027 < 0.03, the vol-clustering effect, not directional) |
| C -- Liquidity | CONCLUIDA (public) | depth_concentration null; ALT-008 bar-derived Amihud illiquidity / turnover / trade-size all SEM_INFO (Amihud rho ~0.00) |
| D -- Derivatives | CONCLUIDA (public) | funding (G), OI (F), basis (FC-II-002) all SEM_INFO |
| E -- Flow | CONCLUIDA | FC-II-004 all SEM_INFO |
| I -- Microstructure (bars) | CONCLUIDA | book (H) null 24h; short-horizon (FC-II-003) info-but-ABORT |
| J -- Regime | ~Concluida | info (risk/context); operational use (ALT-004) failed |
| **F -- Options** | **OPEN** | needs external data (options IV / skew / surface) |
| **G -- On-chain** | **OPEN** | needs external data |
| **H -- Sentiment** | **OPEN** | needs external data |
| **I -- High-res ticks** | **OPEN** | needs external data (tick / full L2) |

---

## Cross-cutting lessons (the feedback that generalizes)

1. **Cost realism is the decider.** The single largest reversal (Sprint 8 -> 9)
   was a simplified cost model approving 13 pairs that a real fill simulator
   killed. Every "gross edge" must be judged net of realistic cost at its
   trading frequency.
2. **Short horizons are where cost wins.** Two independent short-horizon signals
   (z-score micro-reversion, imbalance_price_divergence) were statistically real
   and economically negligible. Information != tradeable edge.
3. **In-sample does not survive OOS by default.** funding_price_divergence
   inverted sign on new data; funding carry's 1.0904 came in negative on its
   first OOS month. Only untouched OOS (and an accumulating forward record)
   settles anything.
4. **ML concentrates edge, it doesn't create it.** On a 0.0096-thin edge,
   meta-labeling produced a pure in-sample mirage. Discipline (frozen model
   space, purged CV, blocked gate) is what keeps ML honest.
5. **Drawdown / risk is a separate failure mode from signal.** TSREV and TSMOM
   had real edges that died on drawdown, not on gross PnL.
6. **The market got more efficient over the sample.** Decaying sub-period
   trajectories (Families F/H) are direct evidence -- simple public-data factors
   are largely arbitraged out in this 2023-2026, 20-perp universe.
7. **The frontier is data, not ideas or code.** Everything derivable from
   OHLCV + funding + OI + aggregated L2 has been tested. Further edge, if it
   exists, lives in data others don't cheaply have.

---

## External literature cross-check (2026-07-11)

Cross-checked against an external survey of the 2020-2026 crypto factor
literature (industry + academic). Treat its citations skeptically (LLM-
generated, several likely fabricated); its taxonomy and ranking are
mainstream and -- importantly -- converge hard with our empirical results
in BOTH directions. Its rankings are PRIORS to test under our gate, not
truths (our own history is proof that "documented in the literature" does
not imply "survives realistic cost in our universe/period").

| Family | External rank / potential | Our empirical evidence | Agreement |
|---|---|---|---|
| Cross-exchange arb | #11, Null (MEV/gas/fees) | not tested; reported dead | -- |
| ML black-box (directional) | #10, Low (spread problem, overfit) | meta-labeling = in-sample mirage | STRONG |
| Order flow (non-HFT) | #9, Null (eroded by fees) | info real, economically dead (FC-II-003) | STRONG |
| Cross-sectional | #8, Weak (short-leg small caps) | CS-001/002 NAO_PASSA | STRONG |
| Liquidity (Amihud) | #7, Medium (risk filter, not signal) | low prior; not a signal | agree |
| Funding carry / basis | #6, evidence high but monetization MEDIUM, compressing post-ETF | near-miss 1.09; 1st OOS month negative | STRONG (post-ETF compression explains our "near" not "pass") |
| TSM (trend) | #3, High -- via **vol-targeting**, ~28d lookback | classic vol-targeted TSM (FC-II-005) now tested: Sharpe 1.04 vs buy-hold -0.14, maxDD 0.35 vs 1.38 IN-SAMPLE | RESOLVED in survey's favor (in-sample) -- the survey was right that vol-targeting is the key our Donchian TSMOM missed; OOS + regime check pending |
| Fiat flows (ETF/stablecoin) | #4, High | OPEN (needs external data) | -- |
| On-chain | #2, Very High | OPEN (needs external data) | -- |
| **Options IV / Skew (VRP)** | **#1, Very High ("Santo Graal")** | OPEN (needs external data) | -- |

Conclusions:
- Everything the survey ranks low/null, we independently killed. Everything
  it ranks highest is exactly what we marked OPEN (external-data families).
  Strong external validation that the frontier is data acquisition.
- The one actionable divergence WAS TSM -- and it resolved in the survey's
  favor. TASK-FC-II-005 tested classic vol-targeted TSM (sign of trailing
  ~28d return, size ~ 1/vol, unit gross, 5d rebalance, 6bps/leg): in-sample
  Sharpe **1.04** vs buy-hold **-0.14** and maxDD **0.35 vs 1.38**. So the
  survey was right that vol-targeting is the ingredient our Donchian TSMOM
  lacked, and my earlier "price family exhausted" claim was wrong. STRONG
  CAVEATS: in-sample dev window; the short leg carries it (long-only Sharpe
  ~0), so it is likely flattered by the bear-heavy part of 2022-2024 and its
  edge may be regime-dependent; the buy-hold baseline is a low bar (alts were
  negative-Sharpe over the window). This is the first dev result in the ML/
  FC-II work that clears its own bar and is NOT economically dead -- so it is
  a genuine candidate for OOS validation (unlike the microstructure hit or
  the meta-labeling mirage), pending a regime-robustness check.
- Why options VRP is the best-justified next bet specifically: it is a
  DIFFERENT KIND of edge -- selling variance/convexity (a risk premium for
  bearing variance risk driven by persistent retail call-buying), not a
  price-prediction signal. Every failed line in this project was a price/
  carry prediction signal; VRP is orthogonal to all of them, which is the
  real reason it warrants the data investment rather than being "one more
  factor."
