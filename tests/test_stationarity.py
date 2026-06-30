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

from src.research import (
    AnalysisScope,
    InsufficientObservationsError,
    StationarityStatus,
    StationarityTestName,
    adf_test,
    assess_stationarity,
    kpss_test,
    preliminary_half_life,
    rolling_correlation,
    spread_stability,
)


def _mean_reverting_series(length: int = 260) -> pd.Series:
    values = [0.0]
    seasonal = np.sin(np.arange(length) / 3.0) * 0.03
    for index in range(1, length):
        values.append(0.74 * values[-1] + seasonal[index])
    return pd.Series(values, dtype=float)


def _random_walk(length: int = 260) -> pd.Series:
    increments = 0.03 + np.sin(np.arange(length) / 7.0) * 0.01
    return pd.Series(np.cumsum(increments), dtype=float)


def test_adf_and_kpss_wrappers_return_standardized_results() -> None:
    spread = _mean_reverting_series()

    adf = adf_test(spread)
    kpss = kpss_test(spread)

    assert adf.test_name is StationarityTestName.ADF
    assert kpss.test_name is StationarityTestName.KPSS
    assert adf.scope is AnalysisScope.FULL_SAMPLE_EXPLORATORY
    assert kpss.scope is AnalysisScope.FULL_SAMPLE_EXPLORATORY
    assert isinstance(adf.critical_values, dict)
    assert isinstance(kpss.critical_values, dict)
    assert adf.nobs > 0
    assert kpss.nobs == len(spread)
    assert adf.stationary is True
    assert kpss.stationary is True


def test_insufficient_observations_are_explicit() -> None:
    with pytest.raises(InsufficientObservationsError, match="requires at least"):
        adf_test([1.0, 1.1], min_observations=20)

    with pytest.raises(InsufficientObservationsError, match="rolling correlation"):
        rolling_correlation([1.0, 2.0], [1.0, 2.0], window=5)


def test_preliminary_half_life_is_calculated_for_mean_reverting_spread() -> None:
    result = preliminary_half_life(_mean_reverting_series())

    assert result.mean_reverting is True
    assert result.slope < 0
    assert math.isfinite(result.half_life)
    assert result.half_life > 0
    assert result.scope is AnalysisScope.FULL_SAMPLE_EXPLORATORY


def test_preliminary_half_life_warns_when_series_is_not_mean_reverting() -> None:
    result = preliminary_half_life(pd.Series(np.linspace(1.0, 20.0, 120)))

    assert result.mean_reverting is False
    assert math.isinf(result.half_life)
    assert result.warning is not None


def test_rolling_correlation_uses_only_observations_available_at_each_point() -> None:
    left = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0, 200.0])
    right = pd.Series([1.0, 2.0, 3.0, 4.0, -100.0, -200.0])

    base = rolling_correlation(left, right, window=4)
    truncated = rolling_correlation(left.iloc[:4], right.iloc[:4], window=4)

    assert pd.isna(base.iloc[3])
    assert pd.isna(truncated.iloc[3])
    assert base.iloc[4] == pytest.approx(1.0)
    assert base.iloc[5] < 1.0


def test_rolling_correlation_marks_no_lookahead_scope_by_contract() -> None:
    left = pd.Series(np.arange(10, dtype=float))
    right = left * 2.0

    result = rolling_correlation(left, right, window=5)

    assert result.name == "rolling_correlation"
    assert result.attrs["scope"] is AnalysisScope.ROLLING_NO_LOOKAHEAD
    assert result.attrs["lookahead_safe"] is True
    assert result.iloc[5] == pytest.approx(1.0)
    assert result.iloc[:5].isna().all()


def test_spread_stability_returns_descriptive_metrics_and_reasons() -> None:
    stable = spread_stability(_mean_reverting_series())
    unstable = spread_stability(
        pd.Series([0.0] * 60 + [10.0] * 60 + [-10.0] * 60),
        max_rolling_mean_drift=0.2,
    )

    assert stable.stable is True
    assert stable.nobs == 260
    assert stable.mean_crossing_rate > 0
    assert unstable.stable is False
    assert unstable.reasons


def test_assess_stationarity_accepts_stationary_spread_and_rejects_random_walk() -> None:
    accepted = assess_stationarity(_mean_reverting_series(), max_half_life=40)
    rejected = assess_stationarity(_random_walk(), max_half_life=40)

    assert accepted.status is not StationarityStatus.REJECT
    assert accepted.accepted is True
    assert rejected.status is StationarityStatus.REJECT
    assert rejected.accepted is False
    assert any("ADF" in reason or "KPSS" in reason for reason in rejected.reasons)


def test_scope_can_mark_full_sample_or_rolling_no_lookahead() -> None:
    spread = _mean_reverting_series()

    exploratory = adf_test(spread, scope=AnalysisScope.FULL_SAMPLE_EXPLORATORY)
    rolling_safe = kpss_test(spread, scope=AnalysisScope.ROLLING_NO_LOOKAHEAD)

    assert exploratory.scope is AnalysisScope.FULL_SAMPLE_EXPLORATORY
    assert rolling_safe.scope is AnalysisScope.ROLLING_NO_LOOKAHEAD
