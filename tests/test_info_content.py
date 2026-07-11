"""Tests for src/research/info_content.py (TASK-ALT-001 infrastructure)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.research.info_content import (
    InformationContentError,
    evaluate_information_content,
    partial_spearman_rho,
    spearman_rho,
)

HOUR_MS = 3_600_000


def test_spearman_rho_perfect_monotonic_relationship():
    feature = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    target = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    rho, n = spearman_rho(feature, target)
    assert rho == pytest.approx(1.0)
    assert n == 5


def test_spearman_rho_perfect_inverse_relationship():
    feature = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    target = pd.Series([50.0, 40.0, 30.0, 20.0, 10.0])
    rho, n = spearman_rho(feature, target)
    assert rho == pytest.approx(-1.0)
    assert n == 5


def test_spearman_rho_drops_nan_rows():
    feature = pd.Series([1.0, float("nan"), 3.0, 4.0, 5.0])
    target = pd.Series([10.0, 20.0, 30.0, float("nan"), 50.0])
    rho, n = spearman_rho(feature, target)
    # Row-wise NaN in either column drops that row: index 1 (feature NaN)
    # and index 3 (target NaN) are dropped; indices 0, 2, 4 survive.
    assert n == 3
    assert rho == pytest.approx(1.0)


def test_spearman_rho_insufficient_data_returns_nan():
    rho, n = spearman_rho(pd.Series([1.0]), pd.Series([1.0]))
    assert math.isnan(rho)
    assert n == 1


def _panel_with_sign(sign_per_period: tuple[float, float, float]) -> pd.DataFrame:
    # 3 sub-periods, each with 5 rows, feature/target monotonic with the
    # given sign in each period.
    rows = []
    for period_index, sign in enumerate(sign_per_period):
        base_time = period_index * 100 * HOUR_MS
        for i in range(5):
            feature = float(i)
            target = sign * float(i)
            rows.append(
                {"open_time": base_time + i * HOUR_MS, "feature": feature, "target": target}
            )
    return pd.DataFrame(rows)


def _boundaries() -> tuple[int, ...]:
    return (0, 100 * HOUR_MS, 200 * HOUR_MS, 300 * HOUR_MS)


def _labels() -> tuple[str, ...]:
    return ("P1", "P2", "P3")


def test_sign_consistent_positive_across_all_periods_has_information():
    panel = _panel_with_sign((1.0, 1.0, 1.0))
    result = evaluate_information_content(
        panel, "test_feature", _boundaries(), _labels(), magnitude_threshold=0.03
    )
    assert result.sign_consistent is True
    assert result.has_information is True
    assert result.full_sample_rho == pytest.approx(1.0)
    assert len(result.sub_periods) == 3
    for sub in result.sub_periods:
        assert sub.spearman_rho == pytest.approx(1.0)
        assert sub.n_obs == 5


def test_sign_flip_across_periods_fails_consistency():
    panel = _panel_with_sign((1.0, -1.0, 1.0))
    result = evaluate_information_content(
        panel, "test_feature", _boundaries(), _labels(), magnitude_threshold=0.03
    )
    assert result.sign_consistent is False
    assert result.has_information is False


def test_magnitude_below_threshold_fails_even_if_sign_consistent():
    panel = _panel_with_sign((1.0, 1.0, 1.0))
    result = evaluate_information_content(
        panel, "test_feature", _boundaries(), _labels(), magnitude_threshold=1.5
    )
    # full_sample_rho is 1.0, which is < 1.5 threshold.
    assert result.sign_consistent is True
    assert result.has_information is False


def test_sub_period_boundaries_isolate_correct_rows():
    panel = _panel_with_sign((1.0, 1.0, 1.0))
    result = evaluate_information_content(
        panel, "test_feature", _boundaries(), _labels(), magnitude_threshold=0.03
    )
    # Each sub-period should only see its own 5 rows, not bleed into others.
    assert [sub.n_obs for sub in result.sub_periods] == [5, 5, 5]
    assert result.full_sample_n == 15


def test_missing_column_fail_closed():
    panel = pd.DataFrame({"open_time": [0], "feature": [1.0]})
    with pytest.raises(InformationContentError, match="missing required columns"):
        evaluate_information_content(panel, "x", _boundaries(), _labels())


def test_mismatched_boundaries_and_labels_fail_closed():
    panel = _panel_with_sign((1.0, 1.0, 1.0))
    with pytest.raises(InformationContentError, match="period_boundaries_ms"):
        evaluate_information_content(panel, "x", (0, 1, 2), ("P1", "P2", "P3"))


def test_negative_magnitude_threshold_fail_closed():
    panel = _panel_with_sign((1.0, 1.0, 1.0))
    with pytest.raises(InformationContentError, match="magnitude_threshold"):
        evaluate_information_content(panel, "x", _boundaries(), _labels(), magnitude_threshold=-0.1)


def test_partial_spearman_removes_only_the_control_shared_effect() -> None:
    # feature == target (perfectly related); control has only mild rank
    # correlation with them -> partial should stay ~1 (control removes little).
    feature = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    target = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    control = pd.Series([4.0, 1.0, 5.0, 2.0, 6.0, 3.0])
    rho, n = partial_spearman_rho(feature, target, control)
    assert n == 6
    assert rho == pytest.approx(1.0)


def test_partial_spearman_is_nan_when_feature_equals_control() -> None:
    # Feature perfectly collinear (in rank) with the control -> no independent
    # variation -> undefined (NaN), i.e. no measurable incremental information.
    z = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    target = pd.Series([2.0, 1.0, 4.0, 3.0, 5.0])
    rho, n = partial_spearman_rho(z, target, z)
    assert n == 5
    assert math.isnan(rho)


def test_partial_spearman_nan_on_insufficient_observations() -> None:
    one = pd.Series([1.0])
    rho, n = partial_spearman_rho(one, one, one)
    assert n == 1
    assert math.isnan(rho)


def test_partial_spearman_drops_nan_rows_jointly() -> None:
    feature = pd.Series([1.0, 2.0, 3.0, 4.0, float("nan")])
    target = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    control = pd.Series([9.0, 1.0, 8.0, 2.0, 7.0])
    rho, n = partial_spearman_rho(feature, target, control)
    assert n == 4  # the NaN row is dropped across all three
    assert math.isfinite(rho)
