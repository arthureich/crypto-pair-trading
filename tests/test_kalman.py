from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (
    KalmanFilterConfig,
    estimate_kalman_spread,
    fit_dynamic_hedge_ratio,
    fit_kalman_filter,
)


def _synthetic_pair(
    *,
    length: int = 240,
    beta: float = 1.75,
    alpha: float = -0.35,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.linspace(10.0, 20.0, length)
    deterministic_noise = np.sin(np.arange(length) / 5.0) * 0.01
    y = beta * x + alpha + deterministic_noise
    return y.astype(float), x.astype(float)


def test_kalman_recovers_known_synthetic_beta_and_alpha() -> None:
    y, x = _synthetic_pair(beta=1.8, alpha=-0.4)

    result = fit_kalman_filter(
        y,
        x,
        KalmanFilterConfig(
            observation_variance=1e-3,
            beta_state_variance=1e-7,
            alpha_state_variance=1e-6,
            unstable_beta_abs_threshold=5.0,
        ),
    )

    assert result.beta[-1] == pytest.approx(1.8, abs=0.03)
    assert result.alpha[-1] == pytest.approx(-0.4, abs=0.5)
    assert result.beta_unstable is False
    assert result.unstable_reasons == ()


def test_kalman_outputs_have_same_length_as_input_series() -> None:
    y, x = _synthetic_pair(length=80)

    result = estimate_kalman_spread(y, x)

    assert result.beta.shape == (80,)
    assert result.alpha.shape == (80,)
    assert result.spread.shape == (80,)
    assert result.innovation.shape == (80,)
    assert result.innovation_variance.shape == (80,)
    assert result.state_covariance.shape == (80, 2, 2)
    assert np.all(np.isfinite(result.spread))


def test_kalman_flags_explosive_beta_jump() -> None:
    x = np.linspace(1.0, 30.0, 120)
    y = 1.2 * x
    y[80:] = 25.0 * x[80:]

    result = fit_kalman_filter(
        y,
        x,
        KalmanFilterConfig(
            observation_variance=1e-4,
            beta_state_variance=5e-2,
            alpha_state_variance=1e-4,
            unstable_beta_abs_threshold=10.0,
            unstable_beta_step_threshold=2.0,
        ),
    )

    assert result.beta_unstable is True
    assert result.unstable_points.any()
    assert "abs_beta_threshold" in result.unstable_reasons


def test_kalman_rejects_invalid_inputs_and_config() -> None:
    y, x = _synthetic_pair(length=10)

    with pytest.raises(ValueError, match="same length"):
        fit_kalman_filter(y, x[:-1])

    with pytest.raises(ValueError, match="finite"):
        fit_kalman_filter([1.0, np.nan], [1.0, 2.0])

    with pytest.raises(ValueError, match="observation_variance"):
        fit_kalman_filter(y, x, KalmanFilterConfig(observation_variance=0.0))


def test_dynamic_hedge_ratio_alias_matches_primary_function() -> None:
    y, x = _synthetic_pair(length=40)

    primary = fit_kalman_filter(y, x)
    alias = fit_dynamic_hedge_ratio(y, x)

    np.testing.assert_allclose(primary.beta, alias.beta)
    np.testing.assert_allclose(primary.spread, alias.spread)
