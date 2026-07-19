# Production Risk Policy -- canonical TSM (TASK-DEPLOY-001, Phase 5)

Controls added by OPERATIONAL justification, never to improve a backtest. Enforced
by `src/research/production_controls.py` (10 tests). All limits are a-priori and
conservative; values are the defaults in `RiskPolicy`. This is paper/research
policy -- no real money is authorized.

## Layer 1 -- Pre-trade limits (reject the offending order; system keeps running)

| Control | Default | Rationale |
|---|---|---|
| max_gross_exposure | 1.0 | unit-gross deploy; no accidental gearing |
| max_net_exposure | 0.30 | the L/S book is near market-neutral; cap directional drift |
| max_leverage | 2.0 | hard ceiling on notional/equity |
| max_exposure_per_symbol | 0.20 | no single name dominates the book |
| max_participation | 0.10 | 10% ADV -- the Phase 4 prudent capacity cap |
| min_liquidity_usd | 1,000,000 | do not trade a symbol below this trailing-24h dollar-volume |
| max_daily_turnover | 2.0 | churn ceiling (the strategy's own turnover ~0.46/rebalance) |

A breach blocks THAT order and is logged; other symbols/rebalances continue.

## Layer 2 -- Data-quality failure modes (flagged; critical ones escalate)

| Failure mode | Flag | Escalates to kill? |
|---|---|---|
| Stale data (bar older than 1h) | `stale_data` | YES |
| Zero / negative price | `non_positive_price` | YES |
| Impossible price deviation (>20% vs reference) | `price_deviation` | YES |
| Incomplete candle | `incomplete_bar` | no (skip bar) |
| Missing funding | `missing_funding` | no (skip funding accrual) |
| Abnormal spread (>1%) | `abnormal_spread` | no (widen cost, may block on participation) |

Also handled operationally (not a price signal): API unavailable, connection drop,
asset suspended, contract delisted, spec change, symbol-mapping error, partial
fill, clock skew, restart mid-rebalance -> all resolve to "do not open new
exposure until state is reconciled".

## Layer 3 -- Kill switches (system-level HALT)

Trip a halt when: `config_hash_mismatch` (running config != frozen canonical
hash), `margin_below_buffer` (< 30%), `local_state_divergence` (computed exposure
!= exchange), or any critical data flag (`stale_data` / `non_positive_price` /
`price_deviation`).

**Safe action = `HALT_NO_NEW_EXPOSURE`.** The system stops opening new exposure and
alerts. It does **NOT** auto-liquidate -- forced liquidation into a bad/illiquid
tape can be worse than holding; any liquidation needs an explicit, separately
tested policy and a human decision.

## Idempotency

Every order is keyed by the deterministic `decision_id` (config-hash | exchange |
symbol | signal-timestamp, Phase 2). Re-processing after a restart re-derives the
same ids, so `is_duplicate` suppresses re-emission -- no duplicated orders or P&L.
The forward ledger is append-only; corrections are new events, never edits.

## Fact / assumption / limitation

- FACT: the checks and their thresholds are enforced in code and unit-tested
  (each limit rejects when breached; each failure mode is flagged; each kill
  switch trips; dedup works).
- ASSUMPTION: thresholds are conservative a-priori operational choices, not tuned;
  they should be reviewed against a specific venue's margin/rate-limit rules
  before any real deployment.
- LIMITATION: this is a policy + enforcement library, not a live trading loop;
  wiring it to a real order router / exchange session is out of scope (and
  explicitly not authorized). No real money.
