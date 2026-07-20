# Cash-and-Carry delta-neutral -- BTC/ETH (TASK-BASIS-001, ADR-0034)

Buy spot + short the same-asset quarterly future at a fixed ~90d lead, hold to expiry, capture basis convergence net of conservative costs (taker + half-spread = 6.5 bps/leg x 4 legs round trip). BTC/ETH only; no ex-post selection. Binance-only.

## BINANCE-ONLY -- CONDITIONAL, not an approval

The locked criterion #1 requires net-positive on Binance AND Bybit AND OKX. This first cut is Binance-only, so it CANNOT pass yet -- it is a conditional read to decide whether cross-exchange work is warranted.

## Result across 16 quarterly contracts (BTCUSDT, ETHUSDT)

- **Net APR**: mean 11.3%, median 8.7%, min 2.5%, max 31.3%, positive **100%**
- **Return on capital employed** (per ~90d trade, spot+10% margin): mean 2.5%, min 0.5%
- **Worst adverse MTM** before convergence: mean -0.6%, worst -1.6%
- **Rolled equity** (16 sequential quarters): compounded 53.4%, **maxDD 0.0%**
- **Observed delta** (corr of carry return vs underlying spot move): **-0.1407853239275202** (target ~0)

## Per-contract

| Contract | days | entry APR | net APR | worst MTM | final basis | spot move |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT_240329 | 88 | 21.0% | 19.8% | -1.0% | 0.12% | 64.2% |
| BTCUSDT_240628 | 89 | 32.5% | 31.1% | 0.0% | 2.01% | -15.4% |
| BTCUSDT_240927 | 88 | 12.1% | 11.0% | -0.1% | -0.46% | 4.4% |
| BTCUSDT_241227 | 87 | 7.5% | 6.4% | -1.6% | -0.65% | 50.7% |
| BTCUSDT_250328 | 86 | 13.7% | 12.6% | -0.3% | -0.02% | -9.7% |
| BTCUSDT_250627 | 87 | 4.3% | 3.2% | -0.3% | 0.05% | 29.5% |
| BTCUSDT_250926 | 87 | 4.1% | 2.9% | -0.8% | -0.52% | 2.0% |
| BTCUSDT_251226 | 87 | 7.0% | 5.9% | -0.4% | 1.30% | -23.3% |
| ETHUSDT_240329 | 88 | 19.6% | 18.4% | -1.0% | 0.42% | 53.9% |
| ETHUSDT_240628 | 89 | 32.6% | 31.3% | 0.0% | 1.62% | -6.5% |
| ETHUSDT_240927 | 88 | 12.5% | 11.3% | -0.2% | -0.32% | -22.5% |
| ETHUSDT_241227 | 87 | 6.0% | 4.9% | -1.5% | -0.56% | 28.3% |
| ETHUSDT_250328 | 86 | 13.0% | 11.9% | -0.3% | 0.22% | -43.3% |
| ETHUSDT_250627 | 87 | 3.6% | 2.5% | -0.2% | -0.27% | 33.7% |
| ETHUSDT_250926 | 87 | 4.1% | 3.0% | -1.3% | -0.43% | 57.8% |
| ETHUSDT_251226 | 87 | 6.4% | 5.3% | -0.5% | 1.18% | -29.3% |

## Reading vs the locked criteria (fact / limitation)

- DELTA-NEUTRAL: carry return vs spot move correlation ~-0.1407853239275202 and the final basis converges to ~0 -> the return is basis-driven, not directional (criterion #4).
- DRAWDOWN: every one of the 16 contract-trades was net POSITIVE, so any ordering has maxDD **0.0%** vs the TSM's 31-58% compounded -> the direction-risk problem is addressed (criterion #3). CAVEAT: this rolled curve concatenates BTC+ETH contracts, so it is an all-positive-sequence proxy, not a live overlapping-portfolio equity curve; the real intra-trade risk is the worst adverse MTM above (<=1.6%).
- CONCENTRATION / capacity / no-leverage: per-contract APRs above; capacity on BTC/ETH spot+quarterly is deep (majors).
- LIMITATION: Binance-only (criterion #1 unmet -> NOT approved); costs are a conservative constant, not real fills; margin/liquidation of the short in an extreme move and exchange/custody risk are real (see pre-register). Entry at a fixed lead (no timing). Cross-exchange (Bybit/OKX) is the next step if the net APR here is materially above costs.
