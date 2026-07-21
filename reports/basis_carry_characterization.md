# Carry time-profile characterization (TASK-BASIS-001 (b))

Fixed windows, no optimization. Answers: **when did the spot x perp funding carry stop compensating the operational + counterparty risks?** Return on TOTAL capital (spot + margin) vs an a-priori hurdle (NOT fit to the data).

## A-priori operational hurdle

- **Hurdle APR = 11.0%** = opportunity_cost_of_capital 4.0% + exchange_counterparty 3.0% + stablecoin_custody 1.0% + fees_and_slippage_annualized 0.5% + funding_inversion_safety 2.0% + two_leg_maintenance 0.5%
- Deploy rule: net forward APR on total capital > hurdle AND >= 180 settlements (causal, conservative; hurdle set from first principles, not chosen to make the strategy pass).

## Headline: last calendar window clearing the hurdle on ALL venues/assets = **NONE**

Return on total capital (net APR / (1+margin)) by window:

| Window | Binance BTC | Binance ETH | Bybit BTC | Bybit ETH | clears hurdle? |
|---|---:|---:|---:|---:|---|
| 2023(H2) | 7.2% | 7.5% | 8.7% | 8.0% | no |
| 2024 | 10.6% | 11.6% | 10.7% | 11.1% | some |
| 2025 | 4.4% | 4.2% | 4.4% | 4.2% | no |
| 2026_YTD | 0.5% | -0.1% | 1.1% | 1.1% | no |
| rolling_90d | 0.5% | 0.0% | 1.2% | 0.9% | no |
| rolling_180d | -0.0% | -0.8% | 0.8% | 0.8% | no |
| rolling_365d | 2.7% | 2.1% | 2.9% | 2.4% | no |

## Detail (Binance BTC, per window)

| Window | gross APR | net APR | ROC | % settl + | neg months | worst cum-fund DD | best-month share |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023(H2) | 8.3% | 7.9% | 7.2% | 88% | 0/7 | 0.0% | 35% |
| 2024 | 11.9% | 11.7% | 10.6% | 92% | 0/12 | 0.1% | 26% |
| 2025 | 5.1% | 4.9% | 4.4% | 87% | 0/12 | 0.1% | 14% |
| 2026_YTD | 1.1% | 0.6% | 0.5% | 62% | 3/6 | 0.4% | 82% |
| rolling_90d | 1.9% | 0.6% | 0.5% | 68% | 1/3 | 0.1% | 63% |
| rolling_180d | 0.6% | -0.0% | -0.0% | 58% | 3/6 | 0.4% | 90% |
| rolling_365d | 3.3% | 3.0% | 2.7% | 75% | 3/12 | 0.4% | 19% |

## Binance-Bybit dispersion (net APR abs diff)

| Window | BTC | ETH |
|---|---:|---:|
| 2023(H2) | 1.68% | 0.55% |
| 2024 | 0.06% | 0.50% |
| 2025 | 0.01% | 0.10% |
| 2026_YTD | 0.59% | 1.31% |
| rolling_90d | 0.71% | 0.94% |
| rolling_180d | 0.88% | 1.75% |
| rolling_365d | 0.15% | 0.38% |

OKX (recent, depth-limited): BTC ROC 1.1%, ETH ROC 1.1% (n=294).

## Reading -- when did the carry stop compensating the risks?

- The carry cleared the ~11% operational hurdle (on TOTAL capital) on all venues/assets only through **no full window**; it has been BELOW the hurdle since. The high APR is front-loaded in the rich-funding 2023-2024 regime and has COMPRESSED toward ~0 (matching the dated-basis compression). So even though it is net-positive over the full sample, on a risk-adjusted, capital-employed, hurdle basis it stopped being deployable well before today.
- HURDLE SENSITIVITY (honest): the verdict depends on the hurdle. Under the full ~11% hurdle (all costs incl. counterparty/custody) it clears in NO full calendar window (2024 peaks at ~10.6% ROC, just under). Under a LEANER ~5% marginal hurdle (capital already on-venue, marginal costs only) 2023-2024 clear but 2025 (~4.4%) and 2026 (~0.5%) do not -> the crossing is ~2025. Either way the carry stopped compensating around 2025 and is ~0 now.
- RISK FRAMING (softened): the position has LOW directional risk and LOW path-dependence PROVIDED both legs stay operational and adequately margined. It is NOT risk-free: funding can invert (short then pays), the spot-perp spread can widen, the two legs can have separate margins / liquidation, a leg can fail, plus exchange / index / ADL / custody risk.
- CONCLUSION for the family: **real but currently compressed** -- the mechanism is genuine and cross-exchange-consistent (Binance+Bybit), but at today's funding it does not clear a conservative operational hurdle. PAUSE; revisit only if forward funding rises back above the hurdle for a sustained run (the deploy rule).
