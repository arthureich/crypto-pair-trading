# TASK-TSM-010 -- Multi-Universe Generalization of the Base TSM

Per `docs/pre_registers/TASK-TSM-010.md` (ADR-0031). The FIXED base TSM (FC-II-008, zero re-tune) across thematic Binance-USDM-perp universes. Primary = base TSM; combined (ERC+vol-target) is a caveated reference (TSM-009: overlays are universe-specific). Cross-asset breadth evidence, not a live promotion. AI/memecoins excluded (no 3y history on this window).

**Base TSM Sharpe > 0 AND > buy-and-hold in 6/6 universes** (positive Sharpe in 6/6).

| Universe | n | Base Sharpe | Combined | Buy-hold | Base maxDD |
|---|---:|---:|---:|---:|---:|
| large_cap | 219 | 0.987 | 1.076 | 0.139 | 0.419 |
| mid_alt_l1 | 219 | 0.650 | 0.610 | -0.557 | 0.769 |
| defi | 219 | 0.832 | 0.569 | -0.452 | 0.749 |
| gaming | 219 | 1.004 | 0.957 | -0.797 | 0.745 |
| old_guard | 219 | 0.462 | 0.562 | 0.062 | 0.571 |
| mid_tier_ref | 219 | 0.577 | 0.335 | -0.429 | 0.801 |

## Per-universe membership (post coverage gate)

- **large_cap**: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT, AVAXUSDT, DOGEUSDT, LINKUSDT, DOTUSDT
- **mid_alt_l1**: NEARUSDT, FILUSDT, ALGOUSDT, ICPUSDT, ATOMUSDT, APTUSDT, ARBUSDT, OPUSDT, SUIUSDT, EGLDUSDT
- **defi**: AAVEUSDT, CRVUSDT, UNIUSDT, SNXUSDT, COMPUSDT, SUSHIUSDT, 1INCHUSDT, YFIUSDT
- **gaming**: SANDUSDT, MANAUSDT, AXSUSDT, GALAUSDT, ENJUSDT, CHZUSDT, APEUSDT
- **old_guard**: LTCUSDT, BCHUSDT, ETCUSDT, XLMUSDT, XTZUSDT, DASHUSDT, ZECUSDT, NEOUSDT
- **mid_tier_ref**: NEARUSDT, FILUSDT, AAVEUSDT, ALGOUSDT, ICPUSDT, SANDUSDT, MANAUSDT, AXSUSDT, GRTUSDT, CRVUSDT

## Reading

Base TSM positive AND beats buy-hold in 6/6 universes (positive in 6/6). STRONG multi-universe generalization: the base TSM delivers a positive, buy-hold-beating Sharpe across the large majority of thematic universes with FIXED params and no retuning -- robust cross-asset breadth evidence that the trend edge is general, not universe-specific. The strongest anti-overfitting evidence in the project (out-of-sample in the ASSET dimension).
