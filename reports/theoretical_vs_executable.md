# Theoretical vs Executable -- canonical TSM (TASK-DEPLOY-001, Phase 3)

Pre-declared conservative execution model (taker fee + half-spread + participation slippage), applied as a cost overlay on the causal backtest (we have klines, not tick/bid-ask data -- a limitation). Characterization on the dev-window original-20 stream. No strategy/parameter change.

## Three streams (dev-window original-20, n=219)

| Stream | Sharpe | net (return units) |
|---|---:|---:|
| A theoretical (6.0bps declared) | 0.970 | 1.267 |
| B executable (6.5bps base) | 0.966 | 1.262 |
| C conservative (50% risk budget) | 0.966 | 0.631 |

## Cost breakdown (bps per leg, on turnover)

- Declared (backtest): 6.0 bps
- Executable base: 6.5 bps (fee 4.5 + half-spread 2.0 + slippage 0.0 at base size)

## Execution shortfall (A - B)

- Return units: 0.0050
- As bps of gross: 37.705
- USD at $100,000 reference capital: $500

## Reading (fact / estimate / assumption / limitation)

- FACT: at deployable (small) size the executable base cost (6.5 bps/leg) is barely above the declared 6.0 bps -> the theoretical-executable gap is small, consistent with the strategy's documented cost-insensitivity (FC-II-007 breakeven ~142 bps/leg). The Sharpe gap A->B is minor.
- ESTIMATE: slippage at base size is ~0; it grows with participation and is quantified against real volume in Phase 4 (capacity).
- ASSUMPTION: conservative stream C = 50% risk budget (a-priori), so its Sharpe ~ B and its absolute return is halved; production-control drag is added in Phase 5.
- LIMITATION: frictions are a cost overlay on causal returns, not a tick fill simulation (no bid/ask data); spread/fee are conservative constants.

## Immutable ledger (OOS forward): 5 new event(s) appended

Ledger at `C:\Users\arthu\Desktop\Aula\Projects\Crypto-Pair-Trading\artifacts\tsm\forward\canonical_ledger.jsonl` (append-only; re-running is idempotent). OOS total rebalances: 5.
