"""Multiple-testing statistical haircut (TASK-DEPLOY-001, Phase 6).

How much of the canonical TSM's Sharpe survives once we account for (a) the
higher moments and finite sample, and (b) the number of hypotheses the whole
program tried. Pure, stdlib-only (statistics.NormalDist for the normal CDF/PPF).

- Probabilistic Sharpe Ratio (PSR, Bailey & Lopez de Prado): P(true SR > SR*)
  given the observed SR, sample size, skew and kurtosis. SR values are PER-PERIOD
  (not annualized).
- Expected maximum Sharpe under N trials, and the Deflated Sharpe Ratio (DSR) =
  PSR against that expected-max benchmark -> corrects for selection across trials.
- Effective number of trials given average cross-trial correlation (so 7
  correlated crypto universes are NOT counted as 7 independent experiments).
"""

from __future__ import annotations

import math
from statistics import NormalDist

__all__ = [
    "deflated_sharpe_ratio",
    "effective_trials",
    "expected_max_sharpe",
    "probabilistic_sharpe_ratio",
]

_N = NormalDist()
_EULER_MASCHERONI = 0.5772156649015329


def probabilistic_sharpe_ratio(
    sr: float, n_obs: int, skew: float, kurtosis: float, sr_benchmark: float = 0.0
) -> float:
    """P(true per-period SR > sr_benchmark). `kurtosis` is non-excess (normal = 3)."""
    if n_obs < 2:  # noqa: PLR2004
        raise ValueError("n_obs must be >= 2")
    denom = 1.0 - skew * sr + ((kurtosis - 1.0) / 4.0) * sr * sr
    if denom <= 0.0:
        return float("nan")
    z = (sr - sr_benchmark) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    return float(_N.cdf(z))


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """E[max of N i.i.d. trial Sharpes] (Bailey & Lopez de Prado 2014).

    sr_variance = variance of the per-period Sharpe ESTIMATES across the trials.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if sr_variance <= 0.0:
        return 0.0
    sigma = math.sqrt(sr_variance)
    if n_trials == 1:
        return 0.0
    a = _N.inv_cdf(1.0 - 1.0 / n_trials)
    b = _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return float(sigma * ((1.0 - _EULER_MASCHERONI) * a + _EULER_MASCHERONI * b))


def deflated_sharpe_ratio(
    sr: float, n_obs: int, skew: float, kurtosis: float, n_trials: int, sr_variance: float
) -> dict:
    """DSR = PSR against the expected-max-Sharpe benchmark for N trials."""
    sr0 = expected_max_sharpe(n_trials, sr_variance)
    dsr = probabilistic_sharpe_ratio(sr, n_obs, skew, kurtosis, sr_benchmark=sr0)
    return {"expected_max_sharpe_benchmark": sr0, "deflated_sharpe_ratio": dsr}


def effective_trials(n_trials: int, avg_correlation: float) -> float:
    """Effective independent trials given average pairwise correlation.

    N_eff = N / (1 + (N-1) * rho), rho clipped to [0, 1). Correlated trials count
    for less; rho=0 -> N_eff=N, rho->1 -> N_eff->1.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    rho = min(max(avg_correlation, 0.0), 0.999999)
    return float(n_trials / (1.0 + (n_trials - 1) * rho))
