# Spot x Perp funding-neutral carry -- cross-exchange (TASK-BASIS-001, criterion #1)

Cross-exchange dated cash-and-carry is data-gated (OKX/Bybit drop expired contracts), so the SAME delta-neutral family is tested on spot x PERP (long spot + short perp, delta ~0; the short receives funding). Carry = cumulative funding net of a one-time round-trip (6.5bps/leg). Basis drift is second-order over a continuous hold. Paper only.

## Verdict (nuanced -- honest)

- **Binance + Bybit, FULL depth (~3y)**: CONFIRMED -- both venues positive for both assets (see table), near-identical -> the delta-neutral funding carry is NOT a single-venue artifact.
- **OKX**: free funding-history is DEPTH-LIMITED (~recent months only; a 2024 request returns empty), so a strict 3-venue FULL-depth test is not possible.
- **Common recent window (apples-to-apples, all 3)**: mixed/low -- on OKX's short available span funding is compressed EVERYWHERE (current regime), so the three venues agree at low levels; this neither confirms nor refutes OKX at depth.
- => Criterion #1 (net-positive on all 3 at comparable depth) is **partially met**: strong 2-venue confirmation (Binance+Bybit), OKX inconclusive by DATA limitation, not by a venue-specific negative.

## Full available depth per venue

| Venue | Asset | settlements | window | gross APR | **net APR** | % settl + | cum-funding maxDD |
|---|---|---:|---|---:|---:|---:|---:|
| binance | BTC | 3378 | 2023-06-01..2026-06-30 | 7.3% | **7.2%** | 85% | 0.4% |
| binance | ETH | 3378 | 2023-06-01..2026-06-30 | 7.5% | **7.5%** | 85% | 0.6% |
| bybit | BTC | 3439 | 2023-06-01..2026-07-21 | 7.6% | **7.5%** | 83% | 0.2% |
| bybit | ETH | 3439 | 2023-06-01..2026-07-21 | 7.5% | **7.5%** | 81% | 0.2% |
| okx | BTC | 294 | 2026-04-14..2026-07-21 | 2.2% | **1.2%** | 67% | 0.1% |
| okx | ETH | 294 | 2026-04-14..2026-07-21 | 2.2% | **1.2%** | 66% | 0.2% |

## Common recent window (apples-to-apples)

### BTC (2026-04-14..2026-06-30)

| Venue | Asset | settlements | window | gross APR | **net APR** | % settl + | cum-funding maxDD |
|---|---|---:|---|---:|---:|---:|---:|
| binance | BTC | 233 | 2026-04-14..2026-06-30 | 1.2% | **-0.0%** | 63% | 0.3% |
| bybit | BTC | 233 | 2026-04-14..2026-06-30 | 0.8% | **-0.5%** | 58% | 0.2% |
| okx | BTC | 233 | 2026-04-14..2026-06-30 | 1.2% | **-0.1%** | 59% | 0.1% |

### ETH (2026-04-14..2026-06-30)

| Venue | Asset | settlements | window | gross APR | **net APR** | % settl + | cum-funding maxDD |
|---|---|---:|---|---:|---:|---:|---:|
| binance | ETH | 233 | 2026-04-14..2026-06-30 | 0.9% | **-0.3%** | 60% | 0.2% |
| bybit | ETH | 233 | 2026-04-14..2026-06-30 | 0.7% | **-0.5%** | 60% | 0.1% |
| okx | ETH | 233 | 2026-04-14..2026-06-30 | 1.9% | **0.7%** | 63% | 0.2% |

## Reading (fact / limitation)

- LOW directional risk / LOW path-dependence (long spot + short perp, equal notional) PROVIDED both legs stay operational and adequately margined -- the return is the funding the short earns, not a price bet, but it is NOT risk-free.
- LIMITATION: this is the PERP construction (funding), NOT the dated cash-and-carry of Phase 1 (which stays Binance-only, data-gated cross-exchange). Funding turns NEGATIVE in sustained bear regimes (short perp then PAYS) -> the cum-funding drawdown column is the real risk. Funding has COMPRESSED over 2025-2026 (consistent with the dated-basis compression in Phase 1) -- the carry is real but thinning. Costs are a conservative constant; borrow/withdrawal/custody and short-leg liquidation risks stand. No real money.
