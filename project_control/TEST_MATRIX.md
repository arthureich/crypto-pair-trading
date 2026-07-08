# TEST_MATRIX

## Categories

```text
unit
integration
backtest
execution
recovery
chaos
financial stress
live readiness
documentation review
```

## Matrix

| Teste | Tipo | Sprint | Modulo | Status | Obrigatorio para gate |
|---|---|---:|---|---|---|
| Architecture forbids Signal/ML order paths | documentation review | 1 | architecture | passed | sim |
| State machine contains all required states | documentation review | 1 | execution | passed | sim |
| State machine critical failures route only to safe states | documentation review | 1 | execution/recovery | passed | sim |
| Negative transition matrix exists | documentation review | 1 | execution | passed | sim |
| P0 event contracts documented | documentation review | 1 | ledger | passed | sim |
| Risk limits define fail-closed behavior | documentation review | 1 | risk | passed | sim |
| Risk forbidden configurations documented | documentation review | 1 | risk | passed | sim |
| Risk entry blockers documented | documentation review | 1 | risk | passed | sim |
| Risk kill-switch triggers have owner threshold action | documentation review | 1 | risk/execution | passed | sim |
| Risk-reducing proof obligation documented | documentation review | 1 | risk/execution | passed | sim |
| Recovery boot blocks new entries | documentation review | 1 | recovery | passed | sim |
| Recovery safe mode allowed actions documented | documentation review | 1 | recovery | passed | sim |
| Recovery ACK_UNKNOWN resolution documented | documentation review | 1 | recovery/ledger | passed | sim |
| Recovery orphan order handling documented | documentation review | 1 | recovery/ledger | passed | sim |
| Recovery REST 5xx and WebSocket missing event fail closed | documentation review | 1 | recovery | passed | sim |
| Recovery cumulative executedQty reconciliation documented | documentation review | 1 | recovery/ledger | passed | sim |
| Recovery resume requires FLAT_RECONCILED or equivalent reconciled state | documentation review | 1 | recovery/ledger | passed | sim |
| SQLite WAL bootstrap migration applies required tables | integration | 2 | ledger | passed | sim |
| EventStore append-only persistence and idempotency | unit | 2 | ledger | passed | sim |
| EventStore sequence gap and failed append rollback | chaos | 2 | ledger | passed | sim |
| EventStore trade event and open position rebuild reads | unit | 2 | ledger | passed | sim |
| Order cannot be sent before persisted event | unit | 2 | ledger/execution | pending | sim |
| Fill duplicado nao duplica posicao | integration | 3 | ledger/reconciliation | passed | sim |
| ACK_UNKNOWN forca reconciliacao | integration | 3 | execution/ledger | passed | sim |
| Crash apos ORDER_SENT | chaos | 4 | recovery | passed | sim |
| Partial fill enters hedge or lockdown route | integration | 4 | execution/recovery | passed | sim |
| Book gap invalida book | unit | 5 | market_data | passed | sim |
| Book stale invalida entry eligibility | unit | 5 | market_data | passed | sim |
| Snapshot mismatch/incomplete exige resync | unit | 5 | market_data | passed | sim |
| Execution spread/depth/imbalance features | unit | 6 | features | passed | sim |
| Slippage estimator detects cost and insufficient liquidity | unit | 6 | execution | passed | sim |
| Feature cache freshness fails closed | unit | 6 | market_data | passed | sim |
| LocalOrderBook snapshot/diff gate correction | unit | 5 | market_data | passed | sim |
| BookFeatures book_age_ms/in_sync gate correction | unit | 6 | features | passed | sim |
| Book stale bloqueia entrada | execution | 6 | execution risk gate | pending | sim |
| Pair selection rejects insufficient data | unit | 7 | research | passed | sim |
| Pair selection rejects low correlation | unit | 7 | research | passed | sim |
| Pair selection ranks candidates by score | unit | 7 | research | passed | sim |
| ADF/KPSS wrappers return standardized results | unit | 7 | research | passed | sim |
| Preliminary half-life is calculated | unit | 7 | research | passed | sim |
| Kalman recovers synthetic beta | unit | 7 | research | passed | sim |
| Kalman spread length matches input series | unit | 7 | research | passed | sim |
| Kalman flags unstable beta | unit | 7 | research | passed | sim |
| OU estimates positive theta for mean-reverting synthetic series | unit | 7 | research | passed | sim |
| OU rejects or warns theta <= 0 | unit | 7 | research | passed | sim |
| Rolling z-score avoids look-ahead | unit | 7 | research | passed | sim |
| Rolling correlation avoids look-ahead | unit | 7 | research | passed | sim |
| Pair selection execution cost filters fail closed | unit | 7 | research | passed | sim |
| OU sigma respects non-unit dt | unit | 7 | research | passed | sim |
| Historical dataset checksum parser/verifier | unit | 7 | research | passed | sim |
| Historical dataset normalizer no-forward-fill gaps | unit | 7 | research | passed | sim |
| Historical dataset archive plan feeds pair selection | integration | 7 | research | passed | sim |
| Sprint 7 historical runner local no-download smoke | integration | 7 | research | passed | sim |
| Sprint 7 historical runner real one-month smoke | integration | 7 | research | passed | nao |
| Sprint 7 full Binance USD-M dataset normalization | integration | 7 | research | passed | sim |
| Sprint 7 real statistical research gate | integration | 7 | research | passed | sim |
| Historical dataset headerless Binance CSV preserves first row | unit | 7 | research | passed | sim |
| Historical dataset checksum mismatch rejected before normalization | unit | 7 | research | passed | sim |
| Execution-cost evidence book-ticker normalization/hourly schema | unit | 7 | research | passed | sim |
| Execution-cost gate forces cost_gated_pass=false when source incomplete | unit | 7 | research | passed | sim |
| Sprint 7 historical execution-cost evidence source review | documentation review | 7 | market_data | passed (SOURCE_INCOMPLETE_FAIL_CLOSED, verified against live source) | sim |
| Sprint 7 cost-gated execution-cost evidence | integration | 7 | research/market_data | passed (definitive: cost_gated_pass=false for all 41 pairs, evidence source incomplete) | sim |
| TASK-007-09 Market Data Agent review | documentation review | 7 | market_data | passed (2 P3, non-blocking) | sim |
| TASK-007-09 QA Agent fail-closed review | documentation review | 7 | research | passed (2 P2 + 1 P3, non-blocking) | sim |
| TASK-007-10 QA Agent independent re-review (S3 pagination, no-default-approve) | documentation review | 7 | research/market_data | passed (1 P2, non-blocking) | sim |
| Historical dataset bookTicker daily archive path (BinanceDataFamily.BOOK_TICKER) | unit | 7 | research | passed | sim |
| Execution-cost daily download fails closed on checksum mismatch | unit | 7 | research | passed | sim |
| Execution-cost daily download never calls real network in tests (mocked urlopen) | unit | 7 | research | passed | sim |
| Execution-cost daily download day-range is half-open and ordered | unit | 7 | research | passed | sim |
| Real memory-safe pilot: 6 symbols x June 2023 daily bookTicker, real network | integration | 7 | research/market_data | passed (4326 hourly rows, checksum-verified) | sim |
| Real cost gate on pilot: 5/6 candidate pairs cost_gated_pass, 1 correctly rejected | integration | 7 | research/market_data | passed | sim |
| TASK-007-10 pilot code review (Market Data Agent: memory safety, checksum, paths) | documentation review | 7 | market_data | passed (1 P3, non-blocking) | sim |
| TASK-007-10 pilot result genuineness review (QA Agent: statistical plausibility) | documentation review | 7 | research | passed | sim |
| Expanded real memory-safe pilot: all 15 symbols used by 41 Sprint 7 candidate pairs, June 2023 daily bookTicker | integration | 7 | research/market_data | passed (450 archives, 17.98GB, checksum-verified, no OOM) | sim |
| Expanded duplicate-hour audit and deduplication | data quality | 7 | market_data | passed (10827 raw hourly rows, 27 duplicate symbol-hours, 10800 deduped rows used by gate) | sim |
| Expanded real cost gate on all 41 candidate pairs | integration | 7 | research/market_data | passed (31/41 cost_gated_pass, 10 ADAUSDT pairs correctly rejected) | sim |
| Sprint 8 universe contract: 31 approved pairs / ADAUSDT fail-closed | unit | 8 | research/backtest | passed (5 tests) | sim |
| Sprint 8 walk-forward split no-look-ahead | unit/integration | 8 | backtest | passed (3 tests) | sim |
| Sprint 8 offline SignalIntent schema and plane-boundary test | unit | 8 | research/architecture | passed (does not import live/ledger/execution/recovery) | sim |
| Sprint 8 cost-aware backtest PnL net of cost | unit/integration | 8 | backtest | passed | sim |
| Sprint 8 fail-closed for missing cost/out-of-universe pair | unit | 8 | backtest/qa | passed | sim |
| Sprint 8 metrics and deterministic ranking | unit/integration | 8 | backtest | passed | sim |
| Sprint 8 causal-safety regression: appended future bars do not change past signals | unit | 8 | backtest/qa | passed (dedicated no-look-ahead proof, added after P1 finding) | sim |
| Sprint 8 backtest runner: beta-weighted gross edge, walk-forward window inclusivity, round-trip cost | unit | 8 | backtest | passed (6 tests, added after QA P2 coverage gap finding) | sim |
| Sprint 8 first-pass review (Backtest/Quant Research/Market Data Agent) | documentation review | 8 | backtest/research/market_data | changes requested -> 3 P1 findings (beta weighting, OU look-ahead, missing exit cost), all fixed | sim |
| Sprint 8 first-pass review (QA Agent) | documentation review | 8 | backtest | passed (1 P2: runner test coverage gap, addressed) | sim |
| Sprint 8 confirmation review after P1 fixes (Backtest + QA combined) | documentation review | 8 | backtest | passed (1 P3 investigated and explained, not a bug) | sim |
| Sprint 8 real backtest run: 31 pairs, corrected methodology | integration | 8 | backtest | passed (622 trades, 13 approved, 18 rejected, portfolio net negative) | sim |
| Backtest sem look-ahead bias | backtest | 8 | backtest | passed (see causal-safety regression above) | sim |
| Sprint 9 fill_model: MARKET/IOC full and partial fill against level-1 quotes | unit | 9 | backtest | passed (14 tests) | sim |
| Sprint 9 fill_model: LIMIT+TTL fill, expiry, partial-then-expired | unit | 9 | backtest | passed | sim |
| Sprint 9 fill_model: latency never selects a quote before decision+latency | unit | 9 | backtest | passed | sim |
| Sprint 9 fill_model: ACK_UNKNOWN deterministic per order_id, integrated with real AckGuardOrderStatus | unit | 9 | backtest | passed | sim |
| Sprint 9 fill_model: partial fill still reports real average_price/slippage (regression for the PnL-zeroing bug) | unit | 9 | backtest | passed | sim |
| Sprint 9 execution_simulator: beta-weighted round trip, LEG_FILL_MISMATCH detection | unit | 9 | backtest | passed (9 tests) | sim |
| Sprint 9 execution_simulator: partially-filled leg contributes real PnL, not zero (regression) | unit | 9 | backtest | passed | sim |
| Sprint 9 execution_simulator: ACK_UNKNOWN entry genuinely delays exit via evaluate_ack_guard, accounting for reconciliation time already elapsed | unit | 9 | backtest | passed | sim |
| Sprint 9 execution_simulator: does not import live/ledger/execution/recovery planes | unit | 9 | backtest/architecture | passed | sim |
| Sprint 9 replay_engine: bounded FIFO day-cache never exceeds maxsize | unit | 9 | backtest | passed (7 tests) | sim |
| Sprint 9 replay_engine: fails closed on missing archive, missing checksum sidecar, checksum mismatch | unit | 9 | backtest | passed | sim |
| Sprint 9 replay_engine: causal replay never uses a quote before the signal | unit | 9 | backtest | passed | sim |
| Sprint 9 chaos: large data gap, zero liquidity, simultaneous both-leg exit failure, invalid side | unit | 9 | backtest | passed (4 tests) | sim |
| Sprint 9 real replay: 13 backtest-approved pairs, real tick data, no mock | integration | 9 | backtest/market_data | passed (247 signals, 239 trades, 0/13 net-positive, portfolio -$2266.27) | sim |
| Sprint 9 review (Backtest Agent): methodology, report-communication findings addressed | documentation review | 9 | backtest | passed (MARKET_IOC caveat + residual metric added) | sim |
| Sprint 9 review (QA Agent): partial-fill PnL bug fix independently re-derived and confirmed correct | documentation review | 9 | backtest | passed | sim |
| Sprint 9 review (Market Data Agent): checksum-verification P1 found and fixed, level-1-only confirmed | documentation review | 9 | backtest/market_data | passed (1 P1 fixed) | sim |
| Sprint 9 review (Execution/Risk Agent, consultative): latency/ack-rate assumptions flagged, leg risk documented, LIMIT/maker gap identified | documentation review | 9 | backtest | reviewed, findings incorporated | sim |
| Sprint 10 fill_model: simulate_limit_fill slippage_bps consistent with MARKET_IOC when reference_price given, None (not fabricated 0.0) otherwise | unit | 10 | backtest | passed (3 tests) | sim |
| Sprint 10 execution_simulator: LIMIT_MAKER_TTL never crosses the spread at placement, fills only when a later quote crosses | unit | 10 | backtest | passed | sim |
| Sprint 10 execution_simulator: LIMIT_MAKER_TTL expires within TTL when the market never crosses (NO_ENTRY_FILL) | unit | 10 | backtest | passed | sim |
| Sprint 10 execution_simulator: LIMIT_MAKER_TTL fails closed to NO_QUOTE without a causal quote | unit | 10 | backtest | passed | sim |
| Sprint 10 execution_simulator: default execution_style is MARKET_IOC, unchanged from Sprint 9 | unit | 10 | backtest | passed | sim |
| Sprint 10 replay_engine: ReplayConfig.execution_style defaults to MARKET_IOC and propagates LIMIT_MAKER_TTL into simulate_round_trip_trade | unit | 10 | backtest | passed (2 tests) | sim |
| Sprint 10 real comparison: MARKET_IOC rerun exactly reproduces Sprint 9 (baseline_reproduction pass, all deltas 0) | integration | 10 | backtest/market_data | passed | sim |
| Sprint 10 real comparison: 13 backtest-approved pairs, MARKET_IOC vs LIMIT_MAKER_TTL, real tick data, no mock | integration | 10 | backtest/market_data | passed (0/13 net-positive under both styles; net PnL -2266.27 -> -2005.91; unclosed residual +27%) | sim |
| Funding carry: Binance sign convention (LONG=-funding_rate, SHORT=+funding_rate) hand-computed against known values | unit | FUND-1 | research | passed (3 tests) | sim |
| Funding carry: symbol with non-finite funding_rate_asof excluded, not fabricated; insufficient eligible symbols at one rebalance fails closed for that rebalance only | unit | FUND-1 | research | passed (2 tests) | sim |
| Funding carry: last rebalance with no forward bar is NO_DATA, not a crash; duplicate (symbol, open_time) rows fail closed; k too large for the universe fails closed | unit | FUND-1 | research | passed (3 tests) | sim |
| Funding carry: profit_factor is +inf (not excluded/fabricated as 0.0) when a resolved rebalance has no losses; summarize fails closed to NaN with zero resolved rebalances; gate requires the pre-registered minimum rebalance count | unit | FUND-1 | research | passed (3 tests) | sim |
| Funding carry real backtest: K=5 (primary)/K=3/K=8 on the full 20-symbol Sprint 7 dataset, real causal funding_rate_asof, no mock, no new download | integration | FUND-1 | research/market_data | passed (gate NAO PASSA at K=5: net profit factor 0.840, net PnL -10729.82 bps over 3287 rebalances; gross edge real and positive but exceeded by full-rebalance-every-8h cost) | sim |
| Funding carry incremental: bootstrap matches fresh top/bottom-K and pays fase-1-equivalent flat cost; held leg retained when swap gain does not clear the yield threshold | unit | FUND-1 | research | passed (2 tests) | sim |
| Funding carry incremental: held leg swapped when gain clears the threshold, cost charged only for the swapped legs; ineligible held leg forced out and unconditionally refilled | unit | FUND-1 | research | passed (2 tests) | sim |
| Funding carry incremental: swap/hold decision is causal, independent of forward price; results are cross-compatible with the fase-1 summarizer | unit | FUND-1 | research | passed (2 tests) | sim |
| Funding carry incremental real backtest: K=5 (primary)/K=3/K=8, same 20-symbol dataset, no new download | integration | FUND-1 | research/market_data | passed (gate NAO PASSA at K=5: net profit factor 1.0904 vs 1.10 threshold, a 0.0096 near-miss on 3287 resolved rebalances, not underpowered; cost cut 99.83% vs fase 1, net PnL flips from -10729.82 to +5620.99 bps; K=3 passes at 1.1356 but is descriptive-only per the pre-registered rule) | sim |
| TSMOM breakout: causal Donchian channel/ATR (shift(1), never the current bar), hand-computed trailing-stop exit, OPEN_AT_END not fabricated, inverse-ATR% weighting, gate requires both PF and win_rate | unit | TSMOM-1 | research | passed (12 tests) | sim |
| TSMOM real backtest: 20-symbol dataset, 24h Donchian/14h ATR/3x stop/12bps cost, no new download | integration | TSMOM-1 | research/market_data | passed (gate NAO PASSA: net profit factor 1.005 vs 1.20 threshold; win rate 34.30% clears the 30% floor; max drawdown ~10.5x total net profit) | sim |
| TSREV signal: causal z=r/sigma (sigma excludes the current bar's own hourly return via shift(1)), Family A hand-computed entry/exit, OPEN_AT_END not fabricated, inverse-sigma weighting, Family B decile ranking excludes zero-variance symbols, OOS split, buy-and-hold drawdown baseline, composite gate (PF+PnL+drawdown+count) | unit | TSREV-C | research | passed (12 tests) | sim |
| TSREV real backtest: primary (Family A, 24h, out-of-sample) plus 7 descriptive secondary cells, 20-symbol dataset, no new download | integration | TSREV-C | research/market_data | passed (gate NAO PASSA on primary: net PF 1.0143 vs 1.05, max drawdown 65719.66bps vs an 11003.94bps buy-and-hold benchmark; win rate 52.68% OOS nearly identical to 52.71% in-sample despite opposite-sign net PnL, validating the OOS-split methodology; secondary Family A 48h clears PF/PnL but still fails the same drawdown criterion, not promoted) | sim |
| Payoff Engineering diagnostic: loss-concentration first-crossing fraction (real bug fixed -- boolean-count over the whole monotonic series previously produced frac_50>frac_80, an impossible result) | unit | PAYOFF-D-1 | research | passed | sim |
| Payoff Engineering real diagnostic run: exact TSREV primary-cell trades (24h, OOS), no re-tuning, no gate | integration | PAYOFF-D-1 | research/market_data | passed (3941 resolved trades; loss diffuse, not outlier-driven, frac_50=19.0%<frac_80=45.5%; SHORT net +37938.31bps/WR 55.2% vs LONG -30248.16bps/WR 50.5%; BTC/ETH worst symbols) | sim |
| Cross-sectional momentum (CS-001): winners/losers selection by raw formation return, hand-computed gross return/weight, OPEN_AT_END not fabricated, causal independence (future bars never change an earlier rebalance's side), fail-closed config/duplicates/insufficient symbols, composite gate | unit | CS-E-1 | research | passed (14 tests) | sim |
| CS-001 real backtest: weekly momentum (168h), quintile K=4, 20-symbol dataset, no new download | integration | CS-E-1 | research/market_data | passed (gate NAO PASSA: net PF 0.98, net PnL -370.61bps over 408 OOS legs; gross PnL also negative, unlike every prior family; win rate ~50% both periods, noise-level) | sim |
| Cross-sectional mean reversion (CS-002): losers/winners side mirror of CS-001, hand-computed gross return, mathematical mirror-identity check (gross_reversal=-gross_momentum on the shared fixture), fail-closed config/duplicates/insufficient symbols, composite gate | unit | CS-E-2 | research | passed (15 tests) | sim |
| CS-002 real backtest: 24h mean reversion (deliberately distinct horizon from CS-001's 168h mirror, which is net-PnL-negative by mathematical construction), 20-symbol dataset, no new download | integration | CS-E-2 | research/market_data | passed (gate NAO PASSA across all 3 cuts: OOS PF 0.94, in-sample PF 1.00, full-sample PF 0.98; gross PnL also negative) | sim |
| Information-content diagnostic engine (Research Phase II infrastructure): Spearman rho hand-computed (perfect monotonic/inverse relationships), NaN row-dropping, sub-period boundary isolation, sign-consistency logic, magnitude threshold, fail-closed missing columns/mismatched boundaries/negative threshold | unit | ALT-II | research | passed (12 tests) | sim |
| Family G (Funding Structure) real diagnostic: 4 causal features vs 24h forward return, 3 non-overlapping ~12-month sub-periods, existing dataset, no new download | integration | ALT-II-G | research/market_data | passed (all 4 SEM_INFORMACAO per the pre-registered threshold; 3 show a sub-period sign flip; funding_price_divergence is sign-stable across all 3 periods, 0.0248 full-sample, a 0.0052 near-miss of the 0.03 threshold) | sim |
| Open Interest downloader/normalizer (Family F): daily-archive URL/path construction, half-open date range, hourly resample uses last-observation-in-hour (not mean, OI is a stock/level variable), epoch-ms conversion matches the project's known convention, empty-hour rows not fabricated | unit | ALT-II-F | research | passed (13 tests, no real-network mock -- same accepted precedent as historical_dataset.py) | sim |
| Family F (Open Interest) real download + diagnostic: ~21,920 daily archives (20 symbols x ~1096 days), all SHA256 checksum-verified, resampled to hourly, 5 causal features vs 24h forward return, same sub-periods/threshold as Family G | integration | ALT-II-F | research/market_data | passed (all 5 SEM_INFORMACAO; strongest, oi_delta, 0.0111 short of threshold; oi_delta/oi_acceleration show a monotonically decaying correlation magnitude across the 3 sub-periods, nearly zero in the most recent) | sim |
| Regime Detection diagnostic (Family J): future absolute-return target, feature panels for 6 causal OHLCV/context features, future-price mutation does not change current features, market context features repeat per symbol, fail-closed missing columns/duplicate rows | unit | ALT-II-J | research | passed (5 tests) | sim |
| Family J (Regime Detection) real diagnostic: 6 causal regime/context features vs future 24h absolute return, existing Sprint 7 normalized dataset, no new download | integration | ALT-II-J | research/market_data | passed (all 6 TEM_INFORMACAO; realized_vol_168h rho=0.3009, realized_vol_24h rho=0.2927, all signs positive/stable across the 3 sub-periods; result is volatility/regime information, not directional alpha) | sim |
| Regime-conditioned TSREV feasibility (TASK-ALT-004): high-volatility filter uses prior 90d q67 causally, missing regime blocks entry, future price mutation does not change current filter, trade filter keeps only explicit allow=True, filtered trades are inverse-vol renormalized | unit | ALT-II-J2 | research/backtest | passed (6 tests) | sim |
| TASK-ALT-004 real feasibility run: TSREV 24h OOS with entries blocked when realized_vol_168h exceeds causal q67, existing normalized dataset, no new download | integration | ALT-II-J2 | research/backtest | passed (gate NAO_PASSA: 2758 resolved filtered trades, net PF 0.982, net PnL -6110.64bps, max DD 61748.50bps vs 11003.94bps buy-and-hold; variant stops) | sim |
| TASK-ALT-005 funding_price_divergence new-OOS runner: causal 90d zscore, old data used only as context, rows before 2026-06-01 excluded from decision, last 24h without target dropped, data gate fails closed | unit | ALT-II-G2 | research | passed (7 tests; focused run with info_content total 18 passed) | sim |
| TASK-ALT-005 real new-OOS diagnostic: funding_price_divergence vs 24h forward return on complete months after 2026-05, with 20 symbols and checksum-verified monthly OHLCV/funding | integration | ALT-II-G2 | research/market_data | passed (100 monthly archives, 20 symbols x 5 families, checksum-verified; data_gate=PASS, full_sample_n=13920; rho=-0.118324, sign reversed vs the 3 original positive sub-periods; decision NAO_PROMOVE) | sim |
| Book depth downloader/normalizer (Family H): daily-archive URL/path construction, half-open date range, hourly resample uses last-observation-in-hour, all 12 percentage-band columns present even if absent in a tiny fixture (NaN, not fabricated), empty-hour rows not fabricated, epoch-ms conversion matches the project's known convention | unit | ALT-II-H | research | passed (9 tests, no real-network mock -- same accepted precedent as historical_dataset.py/download_alt_open_interest.py) | sim |
| Family H (Order Flow) real download + diagnostic: ~21,920 daily bookDepth archives (20 symbols x ~1096 days), all SHA256 checksum-verified, resampled to hourly, 5 causal features (book imbalance/depth concentration/depth change/imbalance-price divergence) vs 24h forward return, same sub-periods/threshold as Families G/F/J | integration | ALT-II-H | research/market_data | passed (all 5 SEM_INFORMACAO; closest near-miss, imbalance_price_divergence, 0.0092 short of threshold and the only pattern in the whole Research Phase II with a GROWING sub-period trajectory; book_imbalance_1pct/depth_concentration repeat Family F's decaying-signal pattern). Real disk-full data-corruption bug found and fixed mid-run (silent-swallow of local write failures as 404s); fixed identically in download_alt_open_interest.py. Retry-with-backoff added for genuine transient ConnectionResetError failures | sim |
| TASK-SIG-001 signal diagnostics: flatten canonical resolved trades only | unit | SIG-1 | research | passed (excludes UNRESOLVED_NO_DATA; fails if no resolved trades) | sim |
| TASK-SIG-001 signal diagnostics: fail-closed malformed payload | unit | SIG-1 | research/qa | passed (invalid status/side/outcome, bars_held<=0, |z|<2.0) | sim |
| TASK-SIG-001 signal diagnostics: required buckets materialized | unit | SIG-1 | research/backtest | passed (1h, 2-4h, 5-12h, 13-24h, 25h+ even when zero) | sim |
| TASK-SIG-001 real diagnostic run | integration | SIG-1 | research | passed (62,878 resolved trades, gross PF 0.987, report generated) | sim |
| TASK-SIG-001 formal review | documentation review | SIG-1 | research/backtest/qa | passed after Backtest and QA requested fixes were addressed | sim |
| TASK-SIG-002 baseline reproduction and fast-vertical causal variant | backtest | SIG-1 | backtest | passed (baseline exact, max_vertical_bars=4 worsens, STOP_FAST_REVERSION_PATH) | sim |
| TASK-SIG-002 confirming-bar regression with real resolver | unit | SIG-1 | backtest/research | passed (VERTICAL at budget boundary is not downgraded to NO_DATA) | sim |
| TASK-SIG-003 binding half-life grid and fail-closed baseline | backtest | SIG-1 | backtest/research | passed (Run 2 binding grid, STOP_SIGNAL_ITERATION) | sim |
| TASK-SIG-004 bar_duration_hours propagation to OU/funding/triple barrier | unit | SIG-1-pos | backtest/research | passed (sub-hour vertical barrier regression and default 1h preservation) | sim |
| TASK-SIG-004 intrahour real sanity run | integration | SIG-1-pos | backtest/research | passed (5m, 8 symbols, 9 pairs, 23,051 trades, gross PF 1.1343, net PF 0.4223) | sim |
| TASK-SIG-004 formal review and handoff closure | documentation review | SIG-1-pos | pm/backtest/qa | passed after unit bug and governance findings were addressed | sim |
| Kill switch trigger fails closed | live readiness | 14 | execution | pending | sim |

## Sprint 1 Review Checks

```text
docs/architecture.md defines every plane and forbidden dependency.
docs/state_machine.md defines inbound and outbound transitions for all required states.
docs/state_machine.md contains a negative transition matrix.
docs/state_machine.md maps each critical failure to RECONCILING, EXIT_LOCKDOWN, or ERROR_SAFE_MODE.
docs/event_contracts.md defines P0 events and idempotency keys.
docs/risk_limits.md defines MVP forbidden items and kill conditions.
docs/risk_limits.md documents Cross Margin, Kelly, 10x, live multi-exchange, and leverage before Sprint 26 as forbidden configurations.
docs/risk_limits.md documents stale book, ledger uncertainty, and ACK_UNKNOWN as entry blockers.
docs/risk_limits.md documents kill-switch triggers with owner, threshold, and action.
docs/risk_limits.md documents fail-closed behavior for missing or stale risk inputs.
docs/risk_limits.md documents that risk-reducing behavior cannot increase exposure and must prove new stress risk is lower than old stress risk.
docs/recovery_protocol.md defines recovery boot and reconciliation-first normal-entry blocking.
docs/recovery_protocol.md defines safe mode allowed actions as cancellation, reconciliation, and risk reduction only.
docs/recovery_protocol.md defines ACK_UNKNOWN resolution, orphan order handling, safe orphan cancel, REST 5xx, WebSocket missing event, cumulative executedQty, and FLAT_RECONCILED resume requirements.
```

## Sprint 2 Ledger Checks

```text
pytest tests/test_event_store.py
Result: passed, 7 tests.

Covered bootstrap migration, WAL, foreign_keys, required tables, EventStore append persistence, append-only events trigger behavior, duplicate idempotency no-op/readback, sequence gap rejection, failed append rollback, trade event loading, and open position loading.
```

## Sprint 3 Integration Checks

```text
pytest tests/test_client_order_id.py tests/test_idempotency.py tests/test_cumulative_reconciliation.py tests/test_ack_guard.py
Result: passed, 57 tests.

pytest tests
Result: passed, 64 tests.

Covered deterministic clientOrderId flowing into ORDER_INTENT_CREATED and ORDER_SENT idempotency keys, attempt/slice idempotency key domain separation, duplicate cumulative fill observations producing zero additional delta and stable idempotency keys, unresolved ORDER_SENT/ACK_UNKNOWN blocking blind retry and same-leg slices, and resolved no-order/no-fill retry only from explicit same-scope state.
```

## Sprint 4 Recovery Checks

```text
pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py tests/test_partial_fill_route.py --basetemp=pytest_temp_run_s4d -o cache_dir=pytest_temp_run_s4d/.pytest_cache
Result: passed, 29 tests.

pytest tests --basetemp=pytest_temp_run_all5 -o cache_dir=pytest_temp_run_all5/.pytest_cache
Result: passed, 93 tests.

Covered crash after durable ORDER_SENT routing to unresolved recovery state, recovery boot blocking normal entries until reconciled truth exists, and partial fill routing to HEDGING_REQUIRED only with risk-reducing proof or EXIT_LOCKDOWN otherwise.
```

## Sprint 5 Market Data Book Health Checks

```text
pytest tests/test_book_health.py
Result: passed, 20 tests.

pytest tests
Result: initial run hit a Windows permission error removing the default pytest_temp directory before EventStore tests.

pytest tests --basetemp=pytest_temp_run_s5_gate_all -o cache_dir=pytest_temp_run_s5_gate_all/.pytest_cache
Result: passed, 113 tests.

ruff check src\market_data tests\test_book_health.py
Result: passed.

Covered L2 update dataclass/model, book health status/reason enums, healthy in-sequence updates, sequence gap invalidation and entry blocking, stale book entry blocking, snapshot mismatch/incomplete snapshot resync, missing snapshot sequence resync, and healthy in-sequence no-resync behavior.
```

## Sprint 6 Execution Features and Slippage Checks

```text
pytest tests/test_execution_features.py
Result: passed, 10 tests.

pytest tests/test_slippage_estimator.py
Result: passed, 7 tests.

pytest tests --basetemp=pytest_temp_run_s6_p1_all -o cache_dir=pytest_temp_run_s6_p1_all/.pytest_cache
Result: passed, 130 tests.

ruff check src\features src\execution\slippage_estimator.py src\market_data\feature_cache.py tests\test_execution_features.py tests\test_slippage_estimator.py
Result: passed.

Covered BookExecutionFeatures model construction, spread_bps, mid_price, 5bps/10bps bid and ask depth, deterministic imbalance, zero-quantity level filtering, malformed book fail-closed behavior, rolling 1s/5s volatility without future data, stale/invalid/resync-required fail-closed usability, buy ask-side slippage, sell bid-side slippage, invalid-request handling, insufficient-liquidity failure reason, and FeatureCache stale fail-closed behavior.
```

## Sprint 5/6 Gate Correction Checks

```text
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_book_builder.py tests/test_book_health.py tests/test_execution_features.py tests/test_slippage_estimator.py --basetemp=pytest_temp_run_s5s6_gate_fix -o cache_dir=pytest_temp_run_s5s6_gate_fix/.pytest_cache
Result: passed, 47 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_s5s6_gate_fix_all -o cache_dir=pytest_temp_run_s5s6_gate_fix_all/.pytest_cache
Result: passed, 140 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check .
Result: passed.

Covered LocalOrderBook/BookBuilder snapshot application, in-sequence diff
application, old update discard, gap invalidation, zero-quantity level removal,
best bid/ask, book_age_ms, in_sync/valid/needs_resync, stale detection, empty
book invalidation, explicit BookExecutionFeatures book_age_ms/in_sync, feature
cache fail-closed behavior, and no DataFrame/Pandas hot path in market-data,
feature, slippage, or cache modules.
```

## Sprint 7 Research Base Checks

```text
Required commands:
pytest tests/test_pair_selection.py
pytest tests/test_stationarity.py
pytest tests/test_kalman.py
pytest tests/test_ou.py

Result:
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py --basetemp=pytest_temp_run_sprint7_final_core -o cache_dir=pytest_temp_run_sprint7_final_core/.pytest_cache
passed, 31 tests.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_final_all -o cache_dir=pytest_temp_run_sprint7_final_all/.pytest_cache
passed, 171 tests.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check src/research tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py
passed.

UV_CACHE_DIR=.uv-cache uv run python -c "<execute code cells for notebooks/01_pair_selection.ipynb and notebooks/02_kalman_ou.ipynb>"
passed, both notebook code-cell checks ok.

Required coverage:
pair selection rejects insufficient data and low correlation;
pair selection ranks candidates by score;
ADF/KPSS wrappers return standardized results;
preliminary half-life is calculated;
Kalman recovers approximate beta on synthetic data;
Kalman spread_t length matches input;
Kalman flags unstable beta;
OU estimates positive theta on mean-reverting synthetic data;
OU rejects or warns theta <= 0;
rolling z-score avoids look-ahead;
rolling correlation avoids look-ahead;
execution-cost filters fail closed when quality/tail evidence is incomplete;
OU sigma scales correctly for non-unit dt;
functions do not rely on mutable global DataFrame state.
```

## Sprint 7 Historical Loader Checks

```text
Required commands:
pytest tests/test_historical_dataset.py
pytest tests/test_pair_selection.py

Result:
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_focus -o cache_dir=pytest_temp_run_task00709_focus/.pytest_cache
passed, 21 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_gate_focus -o cache_dir=pytest_temp_run_task00709_gate_focus/.pytest_cache
passed, 22 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_real_gate_all -o cache_dir=pytest_temp_run_sprint7_real_gate_all/.pytest_cache
passed, 182 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py
passed.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py scripts/run_sprint7_research_gate.py
passed.

Real smoke:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT --start-month 2023-06 --end-month-exclusive 2023-07 --dataset-version sprint7_real_smoke_202306_btcusdt --data-root /tmp/crypto_pair_trading_sprint7_real_smoke --correlation-window 2
passed.
Downloaded and checksumed the 5 required Binance Public Data families for
BTCUSDT 2023-06, wrote 720 normalized bars plus header to
/tmp/crypto_pair_trading_sprint7_real_smoke/normalized/sprint7_real_smoke_202306_btcusdt_bars.csv,
and accepted BTCUSDT in the one-symbol statistical smoke summary.

Full real dataset:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT AVAXUSDT LINKUSDT LTCUSDT BCHUSDT DOTUSDT TRXUSDT ETCUSDT UNIUSDT ATOMUSDT APTUSDT ARBUSDT OPUSDT SUIUSDT --start-month 2023-06 --end-month-exclusive 2026-06 --dataset-version sprint7_binance_usdm_202306_202605 --data-root data/research/binance_public --correlation-window 168 --download-workers 12
passed.
Downloaded and checksumed Binance Public Data archives, wrote 526080 normalized
bars plus header, accepted 20 symbols, produced 41 statistical candidate pairs,
and rejected 149 pairs by pair-selection filters.

Real statistical research gate:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_research_gate.py --bars-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv --summary-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json --output-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json --output-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv
passed.
Evaluated 41 candidate pairs; 41 statistical-only accepts; 0 statistical
rejects; cost_gated_pass=false because verified historical top-of-book/L2
execution-cost evidence is unavailable.

Required coverage:
deterministic Binance Public Data archive paths;
SHA256 checksum parsing and exact verification, including sha256sum binary marker;
checksum mismatch blocks normalization before CSV parsing;
headerless public-data ZIPs preserve the first data row;
kline, mark, index, premium, and funding normalization;
funding joined as-of without future events;
missing hourly gaps do not forward-fill returns;
normalized archive plan feeds select_pairs;
runner script executes local no-download smoke and writes normalized CSV/summary.

Limit:
real statistical gate is complete, but cost-gated Sprint 7 PASS is blocked by
missing verified historical execution-cost evidence and pending Market Data
Agent + QA Agent review.
```
