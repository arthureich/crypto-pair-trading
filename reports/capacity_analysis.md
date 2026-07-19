# Capacity / Liquidity / Impact -- canonical TSM (TASK-DEPLOY-001, Phase 4)

How much capital the canonical core can run before market impact erodes the edge. Per-symbol participation = order notional / trailing-24h dollar-volume; slippage from the pre-declared execution model. Capital grid + impact scenarios are for CHARACTERIZATION, never to pick a capital. Original-20 universe, dev window. Estimates, not guarantees.

Small-size net Sharpe (moderate impact): **0.966**; buy-hold **-0.143**. BRL at 5.5 BRL/USD (assumption).

## Moderate-impact scenario (capital grid)

| Capital (USD) | Capital (BRL) | mean part % | max part % | eff cost bps/leg | net Sharpe | net return | limiting symbol |
|---|---|---:|---:|---:|---:|---:|---|
| $1.0k | R$5.5k | 0.00% | 0.0% | 6.5 | 0.966 | 1.262 | TRXUSDT (0%) |
| $5.0k | R$27.5k | 0.00% | 0.0% | 6.5 | 0.966 | 1.262 | TRXUSDT (0%) |
| $10.0k | R$55.0k | 0.00% | 0.0% | 6.5 | 0.966 | 1.262 | TRXUSDT (0%) |
| $50.0k | R$275.0k | 0.00% | 0.0% | 6.5 | 0.966 | 1.262 | TRXUSDT (0%) |
| $100.0k | R$550.0k | 0.00% | 0.1% | 6.5 | 0.966 | 1.262 | TRXUSDT (0%) |
| $250.0k | R$1.4M | 0.00% | 0.2% | 6.5 | 0.966 | 1.262 | TRXUSDT (0%) |
| $500.0k | R$2.8M | 0.01% | 0.5% | 6.5 | 0.966 | 1.262 | TRXUSDT (0%) |
| $1.0M | R$5.5M | 0.02% | 1.0% | 6.5 | 0.966 | 1.262 | TRXUSDT (1%) |
| $5.0M | R$27.5M | 0.09% | 4.9% | 6.5 | 0.966 | 1.262 | TRXUSDT (5%) |
| $10.0M | R$55.0M | 0.19% | 9.8% | 6.6 | 0.965 | 1.261 | TRXUSDT (10%) |
| $50.0M | R$275.0M | 0.93% | 49.0% | 6.9 | 0.963 | 1.258 | TRXUSDT (49%) |
| $100.0M | R$550.0M | 1.87% | 98.0% | 7.3 | 0.959 | 1.254 | TRXUSDT (98%) |

## Capacity by impact scenario

- **Prudent capacity (HEADLINE)** = largest capital keeping single-symbol participation <= 10% ADV. Model-INDEPENDENT (does not rely on the gentle linear slippage model), so it is the number to trust.
- **Soft (Sharpe)** = net Sharpe >= 90% of small-size Sharpe; **Hard (Sharpe)** = edge still exists (net Sharpe > 0 and > buy-hold). These are OPTIMISTIC -- the linear slippage caps at 100% ADV and badly understates real impact at high participation, so they read far higher than prudent.

| Impact | **prudent (<=10% ADV)** | soft (Sharpe) | hard (Sharpe) |
|---|---|---|---|
| none | **$10.0M** | $100.0M | $100.0M |
| low | **$10.0M** | $100.0M | $100.0M |
| moderate | **$10.0M** | $100.0M | $100.0M |
| severe | **$10.0M** | $100.0M | $100.0M |

## Reading (fact / estimate / assumption / limitation)

- FACT: participation is computed per symbol from real trailing-24h dollar-volume and the per-symbol traded fraction. The binding symbol is the least-liquid member of the universe (here TRXUSDT among the 20).
- FACT: net Sharpe barely moves across the whole grid (0.966 -> ~0.96 at $100M) BECAUSE the linear slippage model is gentle -- this is exactly why the Sharpe-based capacity is NOT trustworthy and the prudent (<=10% ADV) limit (~$10.0M) is the headline.
- ESTIMATE: prudent capacity depends on the ADV cap (10%); at 5% it halves, at 20% it doubles.
- ASSUMPTION: trailing-24h volume is the executable liquidity; BRL/USD fixed for display; unit-gross weights so |dw| is the traded fraction.
- LIMITATION: dev-window original-20 (the MOST liquid tier) -> this is an UPPER bound; the low-liquidity universes (TSM-015) have far smaller capacity. No order-book depth / real spread (klines only); impact is a model, not measured fills; the linear-capped slippage understates impact above ~20-30% ADV.
- DECISION: deploy well inside the prudent capacity (~$10.0M on the liquid majors at moderate impact); scale down materially for less-liquid universes. Do NOT rely on the Sharpe-based figures -- they are model-optimistic.
