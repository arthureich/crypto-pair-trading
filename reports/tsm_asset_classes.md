# TASK-TSM-012 -- Cross-Asset-Class Generalization of the TSM

Per `docs/pre_registers/TASK-TSM-012.md` (ADR-0031). The TSM with the SAME economic horizons (28d trend / 7d vol / 5d hold), in DAILY bars, on non-crypto classes (Yahoo daily, zero cost). Is the edge trend-following (multi-asset; Hurst-Ooi-Pedersen) or crypto-specific? Not a live promotion (continuous-futures roll bias; different execution).

**TSM Sharpe > 0 AND > buy-and-hold in 0/4 asset classes.**

| Asset class | n | TSM Sharpe | Buy-hold | TSM maxDD | TSM net |
|---|---:|---:|---:|---:|---:|
| indices | 155 | -0.294 | 1.116 | 0.204 | -0.110 |
| commodities | 150 | 0.176 | 0.665 | 0.115 | 0.058 |
| forex | 155 | -0.157 | 0.439 | 0.073 | -0.020 |
| etfs | 150 | 0.126 | 1.438 | 0.142 | 0.026 |

## Sub-period TSM Sharpe

| Class | 2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05 |
|---|---:|---:|---:|
| indices | -0.544 | -0.732 | 0.478 |
| commodities | 0.499 | -0.171 | 0.132 |
| forex | -0.089 | 0.846 | -1.704 |
| etfs | 0.284 | -0.841 | 1.133 |

## Membership

- **indices**: ^DJI, ^FTSE, ^GDAXI, ^GSPC, ^N225, ^NDX, ^RUT
- **commodities**: CL=F, GC=F, HG=F, NG=F, SI=F, ZC=F, ZS=F, ZW=F
- **forex**: AUDUSD=X, EURUSD=X, GBPUSD=X, JPY=X, NZDUSD=X, USDCAD=X, USDCHF=X
- **etfs**: DIA, EEM, EFA, GLD, IEF, IWM, QQQ, SLV, SPY, TLT, XLE, XLF

## Reading

PRE-REGISTERED VERDICT: TSM positive AND beats buy-hold in 0/4 TradFi classes -> by the locked criterion it does NOT generalize to TradFi on this window (0/4). Absolute Sharpe: weakly positive in commodities (+0.18) and ETFs (+0.13), negative in indices (-0.29) and forex (-0.16).

LITERATURE CHECK (rule #6 -- done BEFORE any interpretation): the observed behavior AGREES with recent evidence, it does not contradict it. 2023-2024 was a DOCUMENTED WEAK period for TradFi trend/CTAs (equity bull, below-average 'trendiness', rate-cut/election chop; SG Trend flat-to-down) -- Capstone, Auspice, HedgeNordic, Quantica. And the ROLE of trend is crisis-alpha / diversification (asymmetric gains when assets suffer stress), NOT beating buy-hold in a bull -- so the 'beats buy-hold' bar is adverse-by-construction for TradFi here, and the test window is a known weak trend regime.

HONEST CONCLUSION (limit, not refutation): the TSM's STRONG performance is, on this window, CRYPTO-SPECIFIC -- plausibly because crypto 2023-2026 was a high-dispersion, high-vol, negative-alt-drift regime (ideal for long/short trend) while TradFi was a smooth low-dispersion bull (adverse). This does NOT refute the crypto edge (validated across 7 crypto universes + 2 exchanges) -- it BOUNDS the claim: we have shown crypto multi-universe + cross-exchange robustness, NOT cross-asset-class generalization. Per rule #6, NO strategy change is made; the divergence is a regime/benchmark effect, not a flaw. A FAIR future test (separate pre-registration) would use a longer window (spanning 2022-style stress), a large POOLED multi-asset universe (~50+), and a diversification/absolute-return bar rather than beats-buy-hold. Caveat: Yahoo continuous futures carry roll bias; TradFi execution/costs differ -- generalization evidence, not a deployable backtest.
