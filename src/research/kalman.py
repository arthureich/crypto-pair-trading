"""Kalman filter helpers for dynamic pair hedge estimation.

The observation model is:

    y_t = beta_t * x_t + alpha_t + epsilon_t

with random-walk state theta_t = [beta_t, alpha_t]. The implementation is
sequential and only uses observations available at or before each timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class KalmanFilterConfig:
    """Noise and stability controls for dynamic hedge estimation."""

    observation_variance: float = 1e-3
    beta_state_variance: float = 1e-5
    alpha_state_variance: float = 1e-4
    initial_beta: float = 0.0
    initial_alpha: float = 0.0
    initial_state_variance: float = 1_000.0
    unstable_beta_abs_threshold: float = 10.0
    unstable_beta_step_threshold: float = 3.0
    unstable_covariance_trace_threshold: float = 1e8


@dataclass(frozen=True, slots=True)
class KalmanFilterResult:
    """Posterior Kalman estimates and stability flags."""

    beta: FloatArray
    alpha: FloatArray
    spread: FloatArray
    innovation: FloatArray
    innovation_variance: FloatArray
    state_covariance: FloatArray
    beta_unstable: bool
    unstable_points: BoolArray
    unstable_reasons: tuple[str, ...]

    @property
    def unstable_beta(self) -> bool:
        """Alias for callers that prefer adjective-first naming."""

        return self.beta_unstable


@dataclass(frozen=True, slots=True)
class _KalmanState:
    theta: FloatArray
    covariance: FloatArray


def fit_kalman_filter(
    y: ArrayLike,
    x: ArrayLike,
    config: KalmanFilterConfig | None = None,
) -> KalmanFilterResult:
    """Estimate dynamic beta, alpha, spread, and innovation for a pair.

    Args:
        y: Dependent series in the model y_t = beta_t * x_t + alpha_t + epsilon_t.
        x: Independent series with the same length as ``y``.
        config: Optional noise and stability controls.

    Returns:
        KalmanFilterResult with arrays of length ``len(y)`` and state covariance
        with shape ``(len(y), 2, 2)``.

    Raises:
        ValueError: If inputs are empty, non-finite, shape-mismatched, or if
            config values are invalid.
    """

    cfg = config or KalmanFilterConfig()
    y_values = _as_finite_vector(y, "y")
    x_values = _as_finite_vector(x, "x")
    _validate_inputs(y_values, x_values)
    _validate_config(cfg)

    state = _initial_state(cfg)
    process_covariance = np.diag([cfg.beta_state_variance, cfg.alpha_state_variance])
    arrays = _empty_result_arrays(len(y_values))

    for index, (y_t, x_t) in enumerate(zip(y_values, x_values, strict=True)):
        state, innovation, innovation_variance, spread = _kalman_update(
            state=state,
            y_t=float(y_t),
            x_t=float(x_t),
            process_covariance=process_covariance,
            observation_variance=cfg.observation_variance,
        )
        _store_step(arrays, index, state, innovation, innovation_variance, spread)

    unstable_points, unstable_reasons = _build_unstable_flags(arrays, cfg)
    return KalmanFilterResult(
        beta=arrays["beta"],
        alpha=arrays["alpha"],
        spread=arrays["spread"],
        innovation=arrays["innovation"],
        innovation_variance=arrays["innovation_variance"],
        state_covariance=arrays["state_covariance"],
        beta_unstable=bool(np.any(unstable_points)),
        unstable_points=unstable_points,
        unstable_reasons=unstable_reasons,
    )


def estimate_kalman_spread(
    y: ArrayLike,
    x: ArrayLike,
    config: KalmanFilterConfig | None = None,
) -> KalmanFilterResult:
    """Convenience alias for ``fit_kalman_filter``."""

    return fit_kalman_filter(y=y, x=x, config=config)


def _as_finite_vector(values: ArrayLike, name: str) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional series")
    if array.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array.copy()


def _validate_inputs(y_values: FloatArray, x_values: FloatArray) -> None:
    if y_values.shape != x_values.shape:
        raise ValueError("y and x must have the same length")


def _validate_config(config: KalmanFilterConfig) -> None:
    _require_positive("observation_variance", config.observation_variance)
    _require_non_negative("beta_state_variance", config.beta_state_variance)
    _require_non_negative("alpha_state_variance", config.alpha_state_variance)
    _require_positive("initial_state_variance", config.initial_state_variance)
    _require_finite("initial_beta", config.initial_beta)
    _require_finite("initial_alpha", config.initial_alpha)
    _require_positive("unstable_beta_abs_threshold", config.unstable_beta_abs_threshold)
    _require_positive("unstable_beta_step_threshold", config.unstable_beta_step_threshold)
    _require_positive(
        "unstable_covariance_trace_threshold",
        config.unstable_covariance_trace_threshold,
    )


def _require_finite(name: str, value: float) -> None:
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_positive(name: str, value: float) -> None:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be positive and finite")


def _require_non_negative(name: str, value: float) -> None:
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be non-negative and finite")


def _initial_state(config: KalmanFilterConfig) -> _KalmanState:
    return _KalmanState(
        theta=np.array([config.initial_beta, config.initial_alpha], dtype=np.float64),
        covariance=np.eye(2, dtype=np.float64) * config.initial_state_variance,
    )


def _empty_result_arrays(length: int) -> dict[str, FloatArray]:
    return {
        "beta": np.empty(length, dtype=np.float64),
        "alpha": np.empty(length, dtype=np.float64),
        "spread": np.empty(length, dtype=np.float64),
        "innovation": np.empty(length, dtype=np.float64),
        "innovation_variance": np.empty(length, dtype=np.float64),
        "state_covariance": np.empty((length, 2, 2), dtype=np.float64),
    }


def _kalman_update(
    *,
    state: _KalmanState,
    y_t: float,
    x_t: float,
    process_covariance: FloatArray,
    observation_variance: float,
) -> tuple[_KalmanState, float, float, float]:
    predicted_covariance = state.covariance + process_covariance
    design = np.array([x_t, 1.0], dtype=np.float64)
    prediction = float(design @ state.theta)
    innovation = y_t - prediction
    innovation_variance = float(design @ predicted_covariance @ design + observation_variance)

    if not np.isfinite(innovation_variance) or innovation_variance <= 0.0:
        raise ValueError("innovation variance must stay positive and finite")

    kalman_gain = predicted_covariance @ design / innovation_variance
    updated_theta = state.theta + kalman_gain * innovation
    updated_covariance = _joseph_covariance_update(
        predicted_covariance=predicted_covariance,
        design=design,
        kalman_gain=kalman_gain,
        observation_variance=observation_variance,
    )
    spread = y_t - float(design @ updated_theta)

    return (
        _KalmanState(theta=updated_theta, covariance=updated_covariance),
        innovation,
        innovation_variance,
        spread,
    )


def _joseph_covariance_update(
    *,
    predicted_covariance: FloatArray,
    design: FloatArray,
    kalman_gain: FloatArray,
    observation_variance: float,
) -> FloatArray:
    identity = np.eye(2, dtype=np.float64)
    projection = identity - np.outer(kalman_gain, design)
    covariance = projection @ predicted_covariance @ projection.T + observation_variance * np.outer(
        kalman_gain, kalman_gain
    )
    return (covariance + covariance.T) / 2.0


def _store_step(
    arrays: dict[str, FloatArray],
    index: int,
    state: _KalmanState,
    innovation: float,
    innovation_variance: float,
    spread: float,
) -> None:
    arrays["beta"][index] = state.theta[0]
    arrays["alpha"][index] = state.theta[1]
    arrays["spread"][index] = spread
    arrays["innovation"][index] = innovation
    arrays["innovation_variance"][index] = innovation_variance
    arrays["state_covariance"][index] = state.covariance


def _build_unstable_flags(
    arrays: dict[str, FloatArray],
    config: KalmanFilterConfig,
) -> tuple[BoolArray, tuple[str, ...]]:
    beta = arrays["beta"]
    covariance_trace = np.trace(arrays["state_covariance"], axis1=1, axis2=2)
    beta_step = np.concatenate(([0.0], np.abs(np.diff(beta))))

    masks = {
        "abs_beta_threshold": np.abs(beta) > config.unstable_beta_abs_threshold,
        "beta_step_threshold": beta_step > config.unstable_beta_step_threshold,
        "state_covariance_trace_threshold": (
            covariance_trace > config.unstable_covariance_trace_threshold
        ),
        "non_finite_estimate": _non_finite_mask(arrays, covariance_trace),
    }
    unstable_points = np.zeros(beta.shape, dtype=np.bool_)
    reasons: list[str] = []

    for reason, mask in masks.items():
        if bool(np.any(mask)):
            unstable_points |= mask
            reasons.append(reason)

    return unstable_points, tuple(reasons)


def _non_finite_mask(arrays: dict[str, FloatArray], covariance_trace: FloatArray) -> BoolArray:
    return (
        ~np.isfinite(arrays["beta"])
        | ~np.isfinite(arrays["alpha"])
        | ~np.isfinite(arrays["spread"])
        | ~np.isfinite(arrays["innovation"])
        | ~np.isfinite(arrays["innovation_variance"])
        | ~np.isfinite(covariance_trace)
    )


fit_dynamic_hedge_ratio = fit_kalman_filter


__all__ = [
    "KalmanFilterConfig",
    "KalmanFilterResult",
    "estimate_kalman_spread",
    "fit_dynamic_hedge_ratio",
    "fit_kalman_filter",
]
