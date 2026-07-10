# TASK-FC-II-001 -- Risk-Based Position Sizing (development)

Per `docs/pre_registers/TASK-FC-II-001.md` / ADR-0027. **Development window, NO verdict.** Inverse-vol weighting within side + whole-book vol-targeting (self-referential), overlay on the unchanged K=5 signal. Uniform vol-targeting is PF-invariant, so this targets Sharpe / max drawdown, not PF. The promotion gate is on untouched OOS.

## Development metrics (equal-weight baseline vs sized)

| Metric | Baseline (1/2K) | Sized (inverse-vol + vol-target) |
|---|---:|---:|
| Net PnL (bps) | 5482.1 | 5776.2 |
| Sharpe (annualized) | 0.993 | 1.042 |
| Max drawdown (bps) | 1582 | 1725 |
| Rebalances | 3287 | 3287 |

## Interpretation limits

These are in-development numbers on the SAME window the K=5 near-miss was found on -- not evidence and not a gate. Sizing cannot create edge; if the base signal is noise, better sizing only reshapes the variance of losing. The admissible test is the pre-registered OOS gate: sized Sharpe >= baseline + 0.15 AND max drawdown not worse, on >= 500 untouched-OOS rebalances.

## Development finding (2026-07-10)

Even in development, the overlay does NOT meet its own pre-registered gate: Sharpe improves only +0.049 (0.993 -> 1.042), far below the +0.15 margin, and max drawdown gets WORSE (1582 -> 1725 bps), violating the "drawdown not worse" condition. Vol-targeting scaling up in calm regimes plausibly amplified a later drawdown. So the risk overlay shows no clear benefit even on the window it was designed on -- a cautionary/negative development signal, the same pattern as the meta-labeling CV. It lowers the prior that it clears the OOS gate; it settles nothing (only untouched OOS can).
