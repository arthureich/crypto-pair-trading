# Family J (Regime Detection) Information-Content Diagnostic

Research Phase II, TASK-ALT-003. Status: pure context/risk diagnostic, per `project_control/DECISIONS.md` ADR-0021. No strategy, no economic gate, no directional alpha claim.

Target: `future_abs_return_24h = abs(log_price[t+24h] - log_price[t])`. A positive result can only justify a future, separate regime/context task -- not SignalIntent or an execution change.

Forward horizon: 24h. Rolling causal window: 2160h (90 days). Magnitude threshold: 0.03.

## Results

| Feature | Full rho | Full N | 2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05 | Sign consistent | Has information |
|---|---:|---:|---:|---:|---:|---|---|
| realized_vol_24h | 0.2927 | 525100 | 0.3355 (n=175180) | 0.2742 (n=175200) | 0.2349 (n=174720) | True | True |
| realized_vol_168h | 0.3009 | 522220 | 0.3322 (n=172300) | 0.2662 (n=175200) | 0.2681 (n=174720) | True | True |
| trend_intensity_168h | 0.0690 | 522220 | 0.0845 (n=172300) | 0.0604 (n=175200) | 0.0608 (n=174720) | True | True |
| volume_shock_24h | 0.1369 | 481920 | 0.1969 (n=132000) | 0.1330 (n=175200) | 0.0989 (n=174720) | True | True |
| market_dispersion_24h | 0.1175 | 525120 | 0.1766 (n=175200) | 0.1029 (n=175200) | 0.0503 (n=174720) | True | True |
| market_abs_return_24h | 0.0799 | 525120 | 0.1032 (n=175200) | 0.0817 (n=175200) | 0.0282 (n=174720) | True | True |

## Interpretation

All 6 pre-registered regime features meet the information-content criterion against future absolute 24h returns. This is evidence of stable volatility/regime information, not directional edge. The strongest effects are realized-volatility persistence (`realized_vol_24h`, `realized_vol_168h`), consistent with ordinary volatility clustering. Any operational use must be designed in a future separately pre-registered task.
