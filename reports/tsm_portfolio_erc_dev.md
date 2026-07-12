# TASK-TSM-003 -- ERC Portfolio Construction Dev Run (DEVELOPMENT, no verdict)

Per `docs/pre_registers/TASK-TSM-003.md` (ADR-0031, Line 3). Base = vol-targeted TSM with funding (naive inverse-vol within each sleeve); ERC = equal risk contribution within each sleeve (correlation-aware, 90d causal covariance), preserving base direction and L/S gross. Params fixed a priori. **Development-window result -- NOT a promotion; promotion is OOS-gated.** ERC is more complex (covariance + solver), so per ADR-0031 the gain must justify the complexity.

## Headline (full dev window)

| Metric | Base | ERC |
|---|---:|---:|
| Sharpe | 0.970 | 1.039 |
| Max drawdown | 0.3470 | 0.3257 |
| Net PnL | 1.2672 | 1.3539 |
| Mean turnover | 0.4570 | 0.3962 |
| Rebalances | 219 | 219 |

## Sub-period stability (Sharpe)

| Period | Base | ERC |
|---|---:|---:|
| 2023-06_2024-05 | 1.556 | 1.618 |
| 2024-06_2025-05 | 0.586 | 0.663 |
| 2025-06_2026-05 | 0.975 | 1.058 |

## BTC regime (Sharpe)

| Regime | Base | ERC |
|---|---:|---:|
| BTC_up | 0.874 | 0.997 |
| BTC_down | 1.096 | 1.093 |

## Cost sensitivity (Sharpe)

| Cost bps/leg | Base | ERC |
|---|---:|---:|
| 0 | 1.016 | 1.079 |
| 6 | 0.970 | 1.039 |
| 15 | 0.901 | 0.979 |
| 30 | 0.786 | 0.879 |
| 60 | 0.556 | 0.678 |

## Funding sensitivity (Sharpe)

| include_funding | Base | ERC |
|---|---:|---:|
| False | 1.038 | 1.106 |
| True | 0.970 | 1.039 |

## Reading

ERC vs base: Sharpe 0.970 -> 1.039 (delta +0.069); maxDD 0.3470 -> 0.3257 (delta -0.0213). Sharpe consistent across sub-periods AND BTC regimes: False; drawdown better everywhere: True. REJECTED as a dev candidate: no CONSISTENT risk-adjusted improvement that justifies the covariance+solver complexity (ADR-0031 prefers simple robust gains). Per the pre-registration, a gain seen only in aggregate or one regime is treated as a likely false positive. Hypothesis closed with this negative result; proceed to Line 4 (meta-labeling / ML as an operation filter).

## Analyst note (post-run, transparent -- numbers and the mechanical verdict above are UNCHANGED)

The mechanical verdict applies the strict letter of the locked rule (Sharpe up
AND maxDD not worse in EVERY cut). ERC misses it on exactly ONE cut: BTC-down
Sharpe 1.096 -> 1.093, a **-0.003** difference (noise level) -- and in that same
cut drawdown still IMPROVED. On every other axis ERC is a broad, economically
coherent improvement, categorically unlike the Line 1/2 rejections (which were
worse on the headline itself):

- Headline Sharpe 0.970 -> 1.039 (+0.069); maxDD 0.347 -> 0.326; net PnL up.
- **Turnover 0.457 -> 0.396 (LOWER)** -- exactly the mechanism the ERC/risk-parity
  literature predicts (better-diversified book churns less), so the gain is
  economically explained, not a curve-fit.
- Better in ALL 3 sub-periods (1.556->1.618, 0.586->0.663, 0.975->1.058).
- Better at EVERY cost level (and by more as cost rises, consistent with the
  turnover reduction) and with/without funding.
- Drawdown better in EVERY cut, including BTC-down.
- Not concentrated in one sub-period/regime -- the opposite of the false-positive
  signature the rule guards against.

So ERC satisfies the INTENT of the robustness battery (broad, stable,
economically justified, not concentrated) while missing the strict LETTER by a
noise-level -0.003 in one regime cut. The one genuine cost is COMPLEXITY
(covariance estimate + iterative solver) for a +0.069 dev Sharpe.

This is NOT a promotion (promotion is OOS-gated regardless). The open decision is
whether to carry ERC forward as the TSM's ONE pre-registered OOS candidate
(bounded search) despite the strict-letter miss, or hold the locked bar and close
it. That is a research-integrity judgment flagged for the user; the criterion was
NOT relaxed here.
