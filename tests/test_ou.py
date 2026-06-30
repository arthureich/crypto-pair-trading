from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.ou import OUStatus, estimate_ou, full_sample_zscore, rolling_zscore


def _ou_series(
    *,
    length: int = 500,
    theta: float = 0.35,
    mu: float = 1.5,
) -> pd.Series:
    phi = math.exp(-theta)
    values = [mu]
    rng = np.random.default_rng(7)
    deterministic_noise = rng.normal(loc=0.0, scale=0.03, size=length)
    for index in range(1, length):
        values.append(mu + phi * (values[-1] - mu) + deterministic_noise[index])
    return pd.Series(values, dtype=float)


def test_ou_estimates_positive_theta_for_mean_reverting_synthetic_series() -> None:
    spread = _ou_series(theta=0.35, mu=1.5)

    result = estimate_ou(spread)

    assert result.status is OUStatus.MEAN_REVERTING
    assert result.mean_reverting is True
    assert result.theta == pytest.approx(0.35, abs=0.08)
    assert result.mu == pytest.approx(1.5, abs=0.2)
    assert result.sigma > 0
    assert result.half_life == pytest.approx(math.log(2) / result.theta)


def test_ou_rejects_or_warns_when_theta_is_not_positive() -> None:
    values = [1.0]
    for _ in range(1, 120):
        values.append(values[-1] * 1.02 + 0.01)

    result = estimate_ou(values)

    assert result.status is OUStatus.NOT_MEAN_REVERTING
    assert result.mean_reverting is False
    assert result.theta <= 0
    assert math.isinf(result.half_life)
    assert result.warning is not None


def test_ou_sigma_respects_non_unit_dt() -> None:
    spread = _ou_series(theta=0.35, mu=1.5)

    unit = estimate_ou(spread, dt=1.0)
    half = estimate_ou(spread, dt=0.5)

    assert half.theta == pytest.approx(unit.theta * 2.0)
    assert half.sigma == pytest.approx(unit.sigma * math.sqrt(2.0))


def test_rolling_zscore_uses_only_prior_window_statistics() -> None:
    spread = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])

    zscore = rolling_zscore(spread, window=3)

    assert zscore.attrs["lookahead_safe"] is True
    assert zscore.iloc[:3].isna().all()
    assert zscore.iloc[3] == pytest.approx((4.0 - 2.0) / 1.0)
    assert zscore.iloc[4] == pytest.approx((100.0 - 3.0) / 1.0)


def test_full_sample_zscore_is_marked_exploratory_not_lookahead_safe() -> None:
    zscore = full_sample_zscore([1.0, 2.0, 3.0, 4.0])

    assert zscore.attrs["lookahead_safe"] is False
    assert zscore.mean() == pytest.approx(0.0)


def test_ou_requires_enough_variable_observations() -> None:
    with pytest.raises(ValueError, match="at least"):
        estimate_ou([1.0, 1.1], min_observations=20)

    with pytest.raises(ValueError, match="positive variance"):
        estimate_ou([1.0] * 30)
