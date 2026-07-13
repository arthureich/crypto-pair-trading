# TASK-ALT-011 Economic Check -- vrp_z@7d: tradeable edge or just information?

Pre-registered follow-up for the ALT-011 hit (info != edge; FC-II-003 lesson). Pooled BTC/ETH (asset, day) obs sorted into 10 deciles by the causal `vrp_z`; mean 7d forward return per decile; top-minus-bottom GROSS spread vs a ~12 bps round-trip cost. Descriptive only -- no strategy, no pivot.

Observations: 1936. Horizon: 7d.

## Mean 7d forward return by vrp_z decile (bps)

| Decile (0=low VRP, 9=high) | Mean fwd return (bps/7d) |
|---:|---:|
| 0 | -89.0 |
| 1 | -56.8 |
| 2 | +79.3 |
| 3 | -165.1 |
| 4 | +141.7 |
| 5 | +24.2 |
| 6 | +37.8 |
| 7 | +81.0 |
| 8 | +275.1 |
| 9 | +107.7 |

## Reading

Top-decile +107.7 bps vs bottom-decile -89.0 bps -> **gross spread +196.8 bps/7d**; decile monotonicity (corr of decile vs mean return) +0.67. Net of ~12 bps round-trip cost: **+184.8 bps**.

CLEARS COST (descriptive): the gross top-vs-bottom spread is many times the round-trip cost with a positive decile tilt -- unlike the FC-II-003 micro-signal (1-2 bps vs cost), the VRP is not just information but a plausible economic edge. This is the FIRST signal in the project to pass BOTH the information bar (ALT-011) and the gross-economics bar.

### Honest caveats (why this is a LEAD, not a validated edge)

- The decile pattern is TAIL-DRIVEN, not cleanly monotone (low VRP -> negative forward, high VRP -> positive, but the middle deciles are noisy) -- the edge concentrates in high-VRP episodes (post-stress fear -> rebound).
- Overlapping 7d holds sampled DAILY: the top/bottom deciles are NOT independent trades, so the raw spread overstates a weekly-rebalanced strategy's real edge.
- IN-SAMPLE dev window; BTC/ETH-only (2 assets).

Mandatory next step (separate, pre-registered): a PROPER strategy backtest (weekly-rebalanced BTC/ETH VRP timing, realistic cost, drawdown) with an OOS gate -- NOT a decile sort. Or use vrp_z as one feature inside the perp book. The Angle-A VRP-harvesting (options book) remains a separate user decision. No strategy opened here.
