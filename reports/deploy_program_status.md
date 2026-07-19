# Deployment Program Status -- TASK-DEPLOY-001 (ADR-0033) -- COMPLETE

All 7 phases done. This transforms the validated TSM into a forward-executable,
auditable, overfitting-guarded system, and -- per the completion criterion --
answers the 10 questions objectively. No alpha re-optimization; no economic
parameter changed; no real money.

## The 10 completion questions

1. **Exact canonical economic config?** `artifacts/tsm/canonical-config.json`
   (hash `ba5037fc...`, source commit `e0779b0`): sign of the 28d (672h) trailing
   log-return; per-leg inverse realized-vol (7d/168h); unit-gross long/short; 5d
   (120h) rebalance; 6 bps/leg; funding ON. The managed-vol overlay AND ERC are
   EXCLUDED from the core (they are the `combined-caveated` secondary).

2. **maxDD 0.80 = 80% or a unit error?** UNIT/framing (Phase 1, verdict B). The
   reported 0.31-0.80 were ADDITIVE fixed-notional (np.cumsum) numbers, which
   reproduce the legacy metric exactly. The `0.80` is a **57.8%** compounded
   equity drawdown, NOT 80%.

3. **Largest drawdown per universe?** Compounded: **31.0%-57.8%** across the 7
   crypto universes (original_20 31%, large_cap 36%, old_guard 45%, defi 56%,
   gaming 57%, mid_alt_l1 57%, mid_tier_ref 58%). Not "shallow" -- 58% is severe.

4. **Time underwater?** High: **79-89%** of the time below a prior peak, at MODEST
   depth (shallow-but-long grinds); worst peak-to-recovery **~415 days (~14mo)** in
   the mid/alt universes (mid_alt_l1, defi still unrecovered at window-end).

5. **How much theoretical return survives cost?** Almost all at deployable size:
   Sharpe **0.970 (theoretical) -> 0.966 (executable)** (~0.4% haircut); executable
   base cost 6.5 bps/leg vs 6.0 declared. Consistent with breakeven ~142 bps/leg.

6. **With how much capital does it stay executable?** Prudent capacity **~$10M**
   (single-symbol participation <=10% ADV) on the liquid majors. The Sharpe barely
   degrades to $100M, but that is the gentle linear slippage model -- the prudent
   participation limit is the honest number. Far less for low-liquidity universes.

7. **Which assets limit capacity?** The least-liquid member of the universe --
   here **TRXUSDT** among the original 20. Broadly, the low-liquidity universes
   (TSM-015 tier) cap total capacity.

8. **Which operational failures could cause unforeseen losses?** Enumerated and
   controlled (Phase 5 / `production_risk_policy.md`): stale data, zero/negative
   price, impossible price deviation, incomplete bar, missing funding, abnormal
   spread, API down, delisting, spec change, symbol-mapping, partial fill, clock
   skew, restart mid-rebalance, local-state divergence. Kill switches trip on the
   critical ones; **safe action = halt, do NOT open new exposure** (no auto-
   liquidation). Idempotent by deterministic decision_id.

9. **How much should the Sharpe be cut for multiple testing?** (Phase 6) PSR vs 0
   = **0.957** and DSR deflated for all 24 program hypotheses = **0.80** -> the lead
   SURVIVES selection. BUT the honest deflators are sobering: the block-bootstrap
   Sharpe CI is **[-0.05, 1.94] (includes zero)**; the 7 universes are 0.83-
   correlated -> **~1.17 effective independent** (so "7/7" is ~1 bet, not 7); PnL
   is concentrated (**71%** in the top 3 months). Net: a **real but modest,
   dependence-discounted edge**, thinner than the raw headline.

10. **Is the executable forward tracking the backtest within tolerance?** Too early
    to say (Phase 7): 5 OOS rebalances = **operational-diagnostic horizon, NOT a
    verdict**. The machinery is in place (immutable ledger + 3 streams + monitor +
    alert criteria); no alerts tripped; config-hash matches the frozen canonical.
    A verdict needs the 12-18mo horizon.

## Honest bottom line

The canonical TSM is a **real but modest** crypto edge whose theoretical Sharpe
(~0.97) survives realistic execution at small size and multiple-testing selection,
but whose **effective statistical weight is much thinner** than the validation
headline (one effective universe, a single-stream CI touching zero, episodic PnL)
and whose **drawdowns are genuinely deep and long** (31-58%, up to ~14mo). Prudent
capacity on the majors is ~$10M. Whether the edge is real out-of-sample is now a
question only the accruing forward track can answer.

## Stop policy (now in force)

The TSM family is FROZEN. Only the forward track continues. No new variants on the
same window. New ideas go to backlog and require a NEW hypothesis, a NEW pre-
registration, and genuinely independent data before any test. Success was never
"raise the historical Sharpe" -- it was to find out honestly whether the edge can
survive the real world; that verdict now rests with the forward ledger.

## Artifacts

Config: `artifacts/tsm/canonical-config.json`, `frozen-configs.json`,
`attempt_ledger.json`, `forward/canonical_ledger.jsonl`. Reports:
`metric_units_audit.md`, `per_universe_drawdown_audit.{csv,json}`,
`theoretical_vs_executable.md`, `capacity_analysis.md`, `production_risk_policy.md`,
`multiple_testing_haircut.md`, `forward_monitor.md`. Modules: `drawdown.py`,
`forward_ledger.py`, `execution_model.py`, `capacity.py`, `production_controls.py`,
`multiple_testing.py`, `forward_monitor.py` (+ per-symbol weights on the backtest
result). 639 tests.
