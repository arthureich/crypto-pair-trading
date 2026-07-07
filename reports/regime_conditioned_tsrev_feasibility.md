# Regime-Conditioned TSREV Feasibility Diagnostic

TASK-ALT-004, ADR-0022. Feasibility only: the OOS window used here (2025-06 through 2026-05) has already been analyzed elsewhere, so a PASSA would still require future new-OOS validation.

**GATE (filtered feasibility): NAO_PASSA**

Filter: block TSREV 24h entries when `realized_vol_168h[t]` is above the symbol's causal 90-day 67th percentile. Missing regime data blocks entry. Remaining trades are renormalized by the original inverse-vol sizing convention.

Buy-and-hold benchmark max drawdown (OOS): 11003.94 bps.

## Results

| Cell | Trades | Win rate | Net PnL (bps) | Net PF | Max DD (bps) | Gate |
|---|---:|---:|---:|---:|---:|---|
| Original TSREV 24h OOS | 3941 | 52.68% | 7690.14 | 1.01 | 65719.66 | NAO_PASSA |
| Regime-filtered TSREV 24h OOS | 2758 | 51.78% | -6110.64 | 0.98 | 61748.50 | NAO_PASSA |

## Trade Flow

- Total OOS trades before filter: 3946
- Kept after regime filter: 2759
- Blocked by regime/missing-regime: 1187

## Interpretation

This diagnostic tests whether regime information can plausibly reduce TSREV's drawdown problem. It is not a clean confirmation because the same OOS year has already informed prior project decisions.

Result: the pre-registered high-volatility block does not solve the problem. It reduces the original TSREV max drawdown only modestly, keeps drawdown far above the buy-and-hold benchmark, and flips net PnL negative. This regime-conditioning variant stops here.
