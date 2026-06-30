"""Stationarity research helpers for Sprint 7 pair analysis."""

from __future__ import annotations

import math
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.stattools import kpss as statsmodels_kpss

MIN_MEAN_REVERSION_SLOPE = -1e-12
MIN_VARIANCE_OBSERVATIONS = 2


class AnalysisScope(StrEnum):
    """Research scope marker used to separate exploratory and online-safe metrics."""

    FULL_SAMPLE_EXPLORATORY = "FULL_SAMPLE_EXPLORATORY"
    ROLLING_NO_LOOKAHEAD = "ROLLING_NO_LOOKAHEAD"


class StationarityStatus(StrEnum):
    """High-level pair decision from stationarity evidence."""

    ACCEPT = "ACCEPT"
    WARN = "WARN"
    REJECT = "REJECT"


class StationarityTestName(StrEnum):
    """Supported statistical test names."""

    ADF = "ADF"
    KPSS = "KPSS"


class InsufficientObservationsError(ValueError):
    """Raised when a stationarity metric cannot be computed safely."""


@dataclass(frozen=True, slots=True)
class StationarityTestResult:
    """Standardized result for ADF and KPSS wrappers."""

    test_name: StationarityTestName
    statistic: float
    p_value: float
    critical_values: dict[str, float]
    alpha: float
    stationary: bool
    lags: int
    nobs: int
    regression: str
    null_hypothesis: str
    alternative_hypothesis: str
    scope: AnalysisScope
    warning: str | None = None

    @property
    def is_stationary(self) -> bool:
        return self.stationary


@dataclass(frozen=True, slots=True)
class PreliminaryHalfLifeResult:
    """Preliminary AR(1) half-life estimate from a spread-like series."""

    half_life: float
    slope: float
    intercept: float
    nobs: int
    mean_reverting: bool
    scope: AnalysisScope
    warning: str | None = None

    @property
    def is_mean_reverting(self) -> bool:
        return self.mean_reverting


@dataclass(frozen=True, slots=True)
class SpreadStabilityResult:
    """Descriptive spread-stability metrics for research screening."""

    stable: bool
    nobs: int
    mean: float
    std: float
    coefficient_of_variation: float
    latest_zscore: float
    max_abs_zscore: float
    mean_crossing_rate: float
    rolling_mean_drift: float
    rolling_std_ratio: float
    scope: AnalysisScope
    reasons: tuple[str, ...]

    @property
    def unstable(self) -> bool:
        return not self.stable


@dataclass(frozen=True, slots=True)
class StationarityDecision:
    """Combined stationarity screen for a pair spread."""

    status: StationarityStatus
    accepted: bool
    reasons: tuple[str, ...]
    adf: StationarityTestResult
    kpss: StationarityTestResult
    half_life: PreliminaryHalfLifeResult
    stability: SpreadStabilityResult
    scope: AnalysisScope

    @property
    def rejected(self) -> bool:
        return self.status is StationarityStatus.REJECT

    @property
    def warned(self) -> bool:
        return self.status is StationarityStatus.WARN


def adf_test(
    series: Iterable[float] | pd.Series,
    *,
    alpha: float = 0.05,
    regression: str = "c",
    autolag: str | None = "AIC",
    min_observations: int = 20,
    scope: AnalysisScope | str = AnalysisScope.FULL_SAMPLE_EXPLORATORY,
) -> StationarityTestResult:
    """Run an Augmented Dickey-Fuller test with a stable return shape."""

    values = _clean_series(series, min_observations=min_observations, name="ADF")
    _validate_alpha(alpha)
    scope = _validate_scope(scope)

    warning = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        adf_values = adfuller(
            values.to_numpy(dtype=float),
            regression=regression,
            autolag=autolag,
        )
        statistic, p_value, used_lag, nobs, critical_values = adf_values[:5]
    if caught:
        warning = "; ".join(str(item.message) for item in caught)

    return StationarityTestResult(
        test_name=StationarityTestName.ADF,
        statistic=float(statistic),
        p_value=float(p_value),
        critical_values=_float_dict(critical_values),
        alpha=float(alpha),
        stationary=bool(p_value <= alpha),
        lags=int(used_lag),
        nobs=int(nobs),
        regression=regression,
        null_hypothesis="unit root / non-stationary",
        alternative_hypothesis="stationary",
        scope=scope,
        warning=warning,
    )


def kpss_test(
    series: Iterable[float] | pd.Series,
    *,
    alpha: float = 0.05,
    regression: str = "c",
    nlags: str | int = "auto",
    min_observations: int = 20,
    scope: AnalysisScope | str = AnalysisScope.FULL_SAMPLE_EXPLORATORY,
) -> StationarityTestResult:
    """Run a KPSS test with the same result shape as :func:`adf_test`."""

    values = _clean_series(series, min_observations=min_observations, name="KPSS")
    _validate_alpha(alpha)
    scope = _validate_scope(scope)

    warning = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        statistic, p_value, used_lag, critical_values = statsmodels_kpss(
            values.to_numpy(dtype=float),
            regression=regression,
            nlags=nlags,
        )
    if caught:
        warning = "; ".join(str(item.message) for item in caught)

    return StationarityTestResult(
        test_name=StationarityTestName.KPSS,
        statistic=float(statistic),
        p_value=float(p_value),
        critical_values=_float_dict(critical_values),
        alpha=float(alpha),
        stationary=bool(p_value > alpha),
        lags=int(used_lag),
        nobs=int(values.size),
        regression=regression,
        null_hypothesis="level or trend stationary",
        alternative_hypothesis="unit root / non-stationary",
        scope=scope,
        warning=warning,
    )


def preliminary_half_life(
    series: Iterable[float] | pd.Series,
    *,
    min_observations: int = 20,
    scope: AnalysisScope | str = AnalysisScope.FULL_SAMPLE_EXPLORATORY,
) -> PreliminaryHalfLifeResult:
    """Estimate preliminary mean-reversion half-life from ``delta x ~ x_lag``."""

    values = _clean_series(series, min_observations=min_observations, name="half-life")
    scope = _validate_scope(scope)
    if values.nunique(dropna=True) <= 1:
        raise ValueError("half-life requires positive series variance")

    lagged = values.shift(1).dropna()
    delta = values.diff().dropna()
    lagged_values, delta_values = _align_two_series(lagged, delta)
    if len(lagged_values) < MIN_VARIANCE_OBSERVATIONS:
        raise InsufficientObservationsError("half-life requires at least 2 aligned deltas")

    design = np.column_stack([np.ones(len(lagged_values)), lagged_values.to_numpy(dtype=float)])
    intercept, slope = np.linalg.lstsq(design, delta_values.to_numpy(dtype=float), rcond=None)[0]
    slope = float(slope)
    intercept = float(intercept)

    warning = None
    mean_reverting = slope < MIN_MEAN_REVERSION_SLOPE
    if mean_reverting:
        half_life = float(-math.log(2) / slope)
    else:
        half_life = math.inf
        warning = "half-life is infinite because AR(1) slope is non-negative"

    return PreliminaryHalfLifeResult(
        half_life=half_life,
        slope=slope,
        intercept=intercept,
        nobs=int(len(lagged_values)),
        mean_reverting=mean_reverting,
        scope=scope,
        warning=warning,
    )


def rolling_correlation(
    left: Iterable[float] | pd.Series,
    right: Iterable[float] | pd.Series,
    *,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    """Return trailing rolling correlation using observations through each row only."""

    if window < MIN_VARIANCE_OBSERVATIONS:
        raise ValueError("window must be at least 2")
    minimum = window if min_periods is None else min_periods
    if minimum < MIN_VARIANCE_OBSERVATIONS:
        raise ValueError("min_periods must be at least 2")
    if minimum > window:
        raise ValueError("min_periods must be less than or equal to window")

    left_values = _as_numeric_series(left, name="left")
    right_values = _as_numeric_series(right, name="right")
    left_values, right_values = _align_two_series(left_values, right_values)
    if len(left_values) < minimum:
        raise InsufficientObservationsError(
            f"rolling correlation requires at least {minimum} aligned observations"
        )
    if left_values.nunique(dropna=True) <= 1 or right_values.nunique(dropna=True) <= 1:
        raise ValueError("rolling correlation requires positive variance in both series")

    result = left_values.rolling(window=window, min_periods=minimum).corr(right_values).shift(1)
    result.name = "rolling_correlation"
    result.attrs["scope"] = AnalysisScope.ROLLING_NO_LOOKAHEAD
    result.attrs["lookahead_safe"] = True
    return result


def spread_stability(
    spread: Iterable[float] | pd.Series,
    *,
    window: int = 24,
    min_observations: int = 30,
    max_abs_latest_zscore: float = 4.0,
    max_abs_zscore: float = 8.0,
    max_rolling_mean_drift: float = 3.0,
    max_rolling_std_ratio: float = 5.0,
    min_mean_crossing_rate: float = 0.01,
    scope: AnalysisScope | str = AnalysisScope.FULL_SAMPLE_EXPLORATORY,
) -> SpreadStabilityResult:
    """Compute descriptive stability checks for a spread series."""

    if window < MIN_VARIANCE_OBSERVATIONS:
        raise ValueError("window must be at least 2")
    values = _clean_series(spread, min_observations=min_observations, name="spread stability")
    scope = _validate_scope(scope)
    if values.nunique(dropna=True) <= 1:
        raise ValueError("spread stability requires positive series variance")

    std = float(values.std(ddof=1))
    mean = float(values.mean())
    if not math.isfinite(std) or std <= 0:
        raise ValueError("spread stability requires positive standard deviation")

    zscores = (values - mean) / std
    latest_zscore = float(zscores.iloc[-1])
    max_abs_seen_zscore = float(zscores.abs().max())
    coefficient = float(abs(std / mean)) if mean != 0 else math.inf
    crossing_rate = _mean_crossing_rate(values, mean=mean)
    rolling_mean_drift = _rolling_mean_drift(values, mean=mean, std=std, window=window)
    rolling_std_ratio = _rolling_std_ratio(values, std=std, window=window)

    reasons: list[str] = []
    if abs(latest_zscore) > max_abs_latest_zscore:
        reasons.append("latest z-score exceeds stability threshold")
    if max_abs_seen_zscore > max_abs_zscore:
        reasons.append("historical z-score outlier exceeds stability threshold")
    if rolling_mean_drift > max_rolling_mean_drift:
        reasons.append("rolling mean drift exceeds stability threshold")
    if rolling_std_ratio > max_rolling_std_ratio:
        reasons.append("rolling standard deviation ratio exceeds stability threshold")
    if crossing_rate < min_mean_crossing_rate:
        reasons.append("spread crosses its full-sample mean too rarely")

    return SpreadStabilityResult(
        stable=not reasons,
        nobs=int(values.size),
        mean=mean,
        std=std,
        coefficient_of_variation=coefficient,
        latest_zscore=latest_zscore,
        max_abs_zscore=max_abs_seen_zscore,
        mean_crossing_rate=crossing_rate,
        rolling_mean_drift=rolling_mean_drift,
        rolling_std_ratio=rolling_std_ratio,
        scope=scope,
        reasons=tuple(reasons),
    )


def assess_stationarity(
    spread: Iterable[float] | pd.Series,
    *,
    alpha: float = 0.05,
    max_half_life: float = 240.0,
    min_observations: int = 30,
    stability_window: int = 24,
    scope: AnalysisScope | str = AnalysisScope.FULL_SAMPLE_EXPLORATORY,
) -> StationarityDecision:
    """Combine ADF, KPSS, half-life, and stability checks into one decision."""

    _validate_alpha(alpha)
    scope = _validate_scope(scope)
    adf_result = adf_test(
        spread,
        alpha=alpha,
        min_observations=min_observations,
        scope=scope,
    )
    kpss_result = kpss_test(
        spread,
        alpha=alpha,
        min_observations=min_observations,
        scope=scope,
    )
    half_life_result = preliminary_half_life(
        spread,
        min_observations=min_observations,
        scope=scope,
    )
    stability_result = spread_stability(
        spread,
        window=stability_window,
        min_observations=min_observations,
        scope=scope,
    )

    reject_reasons: list[str] = []
    warn_reasons: list[str] = []
    if not adf_result.stationary:
        reject_reasons.append("ADF did not reject unit-root null")
    if not kpss_result.stationary:
        reject_reasons.append("KPSS rejected stationarity null")
    if not half_life_result.mean_reverting:
        reject_reasons.append("preliminary half-life is not mean-reverting")
    elif half_life_result.half_life > max_half_life:
        warn_reasons.append("preliminary half-life exceeds operational threshold")
    if not stability_result.stable:
        warn_reasons.extend(stability_result.reasons)

    if reject_reasons:
        status = StationarityStatus.REJECT
    elif warn_reasons:
        status = StationarityStatus.WARN
    else:
        status = StationarityStatus.ACCEPT

    return StationarityDecision(
        status=status,
        accepted=status is not StationarityStatus.REJECT,
        reasons=tuple(reject_reasons + warn_reasons),
        adf=adf_result,
        kpss=kpss_result,
        half_life=half_life_result,
        stability=stability_result,
        scope=scope,
    )


def reject_non_stationary_pair(
    spread: Iterable[float] | pd.Series,
    **kwargs: Any,
) -> StationarityDecision:
    """Alias for callers that want a fail-closed pair screen name."""

    return assess_stationarity(spread, **kwargs)


def _as_numeric_series(series: Iterable[float] | pd.Series, *, name: str) -> pd.Series:
    if isinstance(series, pd.Series):
        values = series.copy()
    else:
        values = pd.Series(list(series), dtype="float64")
    values = pd.to_numeric(values, errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        raise InsufficientObservationsError(f"{name} requires at least one finite observation")
    return values.astype(float)


def _clean_series(
    series: Iterable[float] | pd.Series,
    *,
    min_observations: int,
    name: str,
) -> pd.Series:
    if min_observations < MIN_VARIANCE_OBSERVATIONS:
        raise ValueError("min_observations must be at least 2")
    values = _as_numeric_series(series, name=name)
    if len(values) < min_observations:
        raise InsufficientObservationsError(
            f"{name} requires at least {min_observations} finite observations; got {len(values)}"
        )
    return values


def _align_two_series(left: pd.Series, right: pd.Series) -> tuple[pd.Series, pd.Series]:
    aligned = pd.concat([left.rename("left"), right.rename("right")], axis=1, join="inner").dropna()
    return aligned["left"].astype(float), aligned["right"].astype(float)


def _mean_crossing_rate(values: pd.Series, *, mean: float) -> float:
    centered = values - mean
    signs = np.sign(centered.to_numpy(dtype=float))
    crossings = np.count_nonzero(signs[1:] * signs[:-1] < 0)
    return float(crossings / max(len(values) - 1, 1))


def _rolling_mean_drift(values: pd.Series, *, mean: float, std: float, window: int) -> float:
    rolling_mean = values.rolling(window=window, min_periods=window).mean().dropna()
    if rolling_mean.empty:
        return 0.0
    return float(((rolling_mean - mean).abs() / std).max())


def _rolling_std_ratio(values: pd.Series, *, std: float, window: int) -> float:
    rolling_std = values.rolling(window=window, min_periods=window).std(ddof=1).dropna()
    rolling_std = rolling_std[rolling_std > 0]
    if rolling_std.empty:
        return math.inf
    return float(max(rolling_std.max() / std, std / rolling_std.min()))


def _float_dict(values: dict[str, float]) -> dict[str, float]:
    return {str(key): float(value) for key, value in values.items()}


def _validate_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")


def _validate_scope(scope: AnalysisScope | str) -> AnalysisScope:
    return AnalysisScope(scope)


adf = adf_test
kpss = kpss_test
half_life = preliminary_half_life
calculate_half_life = preliminary_half_life
evaluate_spread_stability = spread_stability
evaluate_stationarity = assess_stationarity


__all__ = [
    "AnalysisScope",
    "InsufficientObservationsError",
    "PreliminaryHalfLifeResult",
    "SpreadStabilityResult",
    "StationarityDecision",
    "StationarityStatus",
    "StationarityTestName",
    "StationarityTestResult",
    "adf",
    "adf_test",
    "assess_stationarity",
    "calculate_half_life",
    "evaluate_spread_stability",
    "evaluate_stationarity",
    "half_life",
    "kpss",
    "kpss_test",
    "preliminary_half_life",
    "reject_non_stationary_pair",
    "rolling_correlation",
    "spread_stability",
]
