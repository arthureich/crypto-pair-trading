# TASK-TSM-015 -- Liquidity-stress test of the base TSM

Per `docs/pre_registers/TASK-TSM-015.md` (ADR-0031). Union of cached survivors segmented into liquidity terciles (median daily dollar-volume); FIXED base TSM (FC-II-008, include_funding, zero re-tune) per tier under a cost sweep. Offline; causal; descriptive. See the survivorship caveat.

Covered symbols (coverage gate 0.95): 45. Cost bars: 6, 12, 20, 30 bps/leg.

## Sharpe by tier x cost

| Tier | n | median $vol/day | 6bps | 12bps | 20bps | 30bps | buy-hold |
|---|---:|---:|---:|---:|---:|---:|---:|
| HIGH | 15 | 2.644e+08 | 0.769 | 0.725 | 0.667 | 0.593 | 0.062 |
| MID | 15 | 7.442e+07 | 0.934 | 0.899 | 0.851 | 0.792 | -0.512 |
| LOW | 15 | 1.726e+07 | 0.842 | 0.810 | 0.767 | 0.714 | -0.510 |

## maxDD / turnover by tier (at 6bps and 20bps)

| Tier | maxDD@6 | turn@6 | maxDD@20 | turn@20 |
|---|---:|---:|---:|---:|
| HIGH | 0.471 | 0.464 | 0.489 | 0.464 |
| MID | 0.468 | 0.436 | 0.490 | 0.436 |
| LOW | 0.686 | 0.445 | 0.715 | 0.445 |

## Tier membership (ascending liquidity within tier)

- **HIGH**: DOTUSDT, NEARUSDT, FILUSDT, BCHUSDT, LTCUSDT, AVAXUSDT, LINKUSDT, ADAUSDT, SUIUSDT, BNBUSDT, DOGEUSDT, XRPUSDT, SOLUSDT, ETHUSDT, BTCUSDT
- **MID**: ALGOUSDT, ICPUSDT, SANDUSDT, APEUSDT, XLMUSDT, ATOMUSDT, TRXUSDT, GALAUSDT, ETCUSDT, CRVUSDT, UNIUSDT, APTUSDT, AAVEUSDT, OPUSDT, ARBUSDT
- **LOW**: YFIUSDT, ENJUSDT, DASHUSDT, EGLDUSDT, 1INCHUSDT, XTZUSDT, NEOUSDT, SNXUSDT, COMPUSDT, SUSHIUSDT, ZECUSDT, MANAUSDT, GRTUSDT, CHZUSDT, AXSUSDT

## Reading

LIQUIDITY-ROBUST (within survivors): the base TSM edge survives at the lower-liquidity end at realistic cost.

By tier @6bps: HIGH 0.769, MID 0.934, LOW 0.842 (HIGH-LOW gap -0.073). LOW tier across cost: 6bps 0.842, 12bps 0.810, 20bps 0.767, 30bps 0.714; LOW buy-hold -0.510. Decision bar: LOW must beat buy-hold at >= 20bps -> LOW@20bps 0.767.

SURVIVORSHIP CAVEAT (central): truly illiquid/microcap perps lack 3y history and are ABSENT -- this covers only the lower-liquidity END of 45 survivors, an OPTIMISTIC lower bound on the liquidity question, not the real microcap tail. quote_volume is a coarse proxy (no spread/book depth). Fixed params, a-priori tiers/costs; offline; descriptive, no live promotion.
