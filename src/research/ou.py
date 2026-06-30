"""Ornstein-Uhlenbeck estimation helpers for Sprint 7 spread research."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd

MIN_OU_OBSERVATIONS = 20
MIN_ZSCORE_WINDOW = 2


class OUStatus(StrEnum):
    """High-level OU fit status."""

    MEAN_REVERTING = "MEAN_REVERTING"
    NOT_MEAN_REVERTING = "NOT_MEAN_REVERTING"


@dataclass(frozen=True, slots=True)
class OUFitResult:
    """Continuous-time OU parameters estimated from a discrete spread series."""

    theta: float
    mu: float
    sigma: float
    half_life: float
    phi: float
    intercept: float
    residual_std: float
    nobs: int
    status: OUStatus
    warning: str | None = None

    @property
    def mean_reverting(self) -> bool:
        return self.status is OUStatus.MEAN_REVERTING


def estimate_ou(
    spread: Iterable[float] | pd.Series,
    *,
    dt: float = 1.0,
    min_observations: int = MIN_OU_OBSERVATIONS,
) -> OUFitResult:
    """Estimate OU parameters from ``x_t = intercept + phi * x_{t-1} + eps``."""

    _positive_float("dt", dt)
    values = _clean_series(spread, min_observations=min_observations)
    lagged = values.shift(1).dropna()
    current = values.iloc[1:]
    aligned = pd.concat([lagged.rename("lagged"), current.rename("current")], axis=1).dropna()
    if len(aligned) < max(MIN_ZSCORE_WINDOW, min_observations - 1):
        raise ValueError("OU estimation requires enough aligned lag/current observations")

    x_lag = aligned["lagged"].to_numpy(dtype=float)
    x_now = aligned["current"].to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x_lag)), x_lag])
    intercept, phi = np.linalg.lstsq(design, x_now, rcond=None)[0]
    intercept = float(intercept)
    phi = float(phi)
    residuals = x_now - (intercept + phi * x_lag)
    residual_std = float(np.std(residuals, ddof=1))

    if 0.0 < phi < 1.0:
        theta = float(-math.log(phi) / dt)
        mu = float(intercept / (1.0 - phi))
        sigma = _continuous_ou_sigma(residual_std=residual_std, theta=theta, phi=phi)
        half_life = float(math.log(2.0) / theta)
        return OUFitResult(
            theta=theta,
            mu=mu,
            sigma=sigma,
            half_life=half_life,
            phi=phi,
            intercept=intercept,
            residual_std=residual_std,
            nobs=int(len(aligned)),
            status=OUStatus.MEAN_REVERTING,
        )

    theta = float(-math.log(phi) / dt) if phi > 0.0 else 0.0
    return OUFitResult(
        theta=theta,
        mu=math.nan,
        sigma=math.nan,
        half_life=math.inf,
        phi=phi,
        intercept=intercept,
        residual_std=residual_std,
        nobs=int(len(aligned)),
        status=OUStatus.NOT_MEAN_REVERTING,
        warning="theta <= 0 or phi outside (0, 1); spread is not useful mean-reverting OU",
    )


def rolling_zscore(
    spread: Iterable[float] | pd.Series,
    *,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    """Return z-score using trailing statistics shifted one row to avoid look-ahead."""

    if window < MIN_ZSCORE_WINDOW:
        raise ValueError("window must be at least 2")
    periods = window if min_periods is None else min_periods
    if periods < MIN_ZSCORE_WINDOW:
        raise ValueError("min_periods must be at least 2")
    if periods > window:
        raise ValueError("min_periods must be less than or equal to window")

    values = _as_numeric_series(spread)
    trailing_mean = values.rolling(window=window, min_periods=periods).mean().shift(1)
    trailing_std = values.rolling(window=window, min_periods=periods).std(ddof=1).shift(1)
    zscore = (values - trailing_mean) / trailing_std
    zscore = zscore.where(trailing_std > 0)
    zscore.name = "zscore"
    zscore.attrs["lookahead_safe"] = True
    return zscore


def full_sample_zscore(spread: Iterable[float] | pd.Series) -> pd.Series:
    """Return exploratory full-sample z-score for reports only."""

    values = _as_numeric_series(spread)
    std = float(values.std(ddof=1))
    if not math.isfinite(std) or std <= 0.0:
        raise ValueError("z-score requires positive standard deviation")
    zscore = (values - float(values.mean())) / std
    zscore.name = "zscore"
    zscore.attrs["lookahead_safe"] = False
    return zscore


def _continuous_ou_sigma(*, residual_std: float, theta: float, phi: float) -> float:
    denominator = 1.0 - phi**2
    if denominator <= 0.0:
        return math.nan
    return float(residual_std * math.sqrt((2.0 * theta) / denominator))


def _clean_series(
    spread: Iterable[float] | pd.Series,
    *,
    min_observations: int,
) -> pd.Series:
    if min_observations < MIN_ZSCORE_WINDOW:
        raise ValueError("min_observations must be at least 2")
    values = _as_numeric_series(spread)
    if len(values) < min_observations:
        raise ValueError(
            f"OU estimation requires at least {min_observations} finite observations; "
            f"got {len(values)}"
        )
    if values.nunique(dropna=True) <= 1:
        raise ValueError("OU estimation requires positive variance")
    return values


def _as_numeric_series(spread: Iterable[float] | pd.Series) -> pd.Series:
    if isinstance(spread, pd.Series):
        values = spread.copy()
    else:
        values = pd.Series(list(spread), dtype="float64")
    values = pd.to_numeric(values, errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        raise ValueError("series requires at least one finite observation")
    return values.astype(float)


def _positive_float(field_name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field_name} must be numeric")
    if not math.isfinite(float(value)) or float(value) <= 0.0:
        raise ValueError(f"{field_name} must be positive and finite")
    return float(value)


estimate_ou_parameters = estimate_ou
zscore_rolling = rolling_zscore


__all__ = [
    "OUFitResult",
    "OUStatus",
    "estimate_ou",
    "estimate_ou_parameters",
    "full_sample_zscore",
    "rolling_zscore",
    "zscore_rolling",
]
