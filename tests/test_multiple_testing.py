"""Tests for the multiple-testing statistics (TASK-DEPLOY-001, Phase 6)."""

from __future__ import annotations

import math

import pytest

from src.research.multiple_testing import (
    deflated_sharpe_ratio,
    effective_trials,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
)


def test_psr_half_when_sr_equals_benchmark():
    # SR exactly at benchmark, normal moments -> P = 0.5
    p = probabilistic_sharpe_ratio(0.1, 100, skew=0.0, kurtosis=3.0, sr_benchmark=0.1)
    assert math.isclose(p, 0.5, abs_tol=1e-9)


def test_psr_increases_with_sample_size():
    lo = probabilistic_sharpe_ratio(0.1, 30, 0.0, 3.0)
    hi = probabilistic_sharpe_ratio(0.1, 500, 0.0, 3.0)
    assert hi > lo  # more data -> more confident SR>0


def test_psr_negative_skew_and_fat_tails_reduce_confidence():
    base = probabilistic_sharpe_ratio(0.15, 200, 0.0, 3.0)
    worse = probabilistic_sharpe_ratio(0.15, 200, -1.0, 8.0)  # neg skew, fat tails
    assert worse < base


def test_expected_max_sharpe_grows_with_trials():
    e10 = expected_max_sharpe(10, sr_variance=0.01)
    e100 = expected_max_sharpe(100, sr_variance=0.01)
    assert e100 > e10 > 0.0


def test_expected_max_sharpe_zero_variance_or_single_trial():
    assert expected_max_sharpe(50, 0.0) == 0.0
    assert expected_max_sharpe(1, 0.01) == 0.0


def test_deflated_sharpe_below_psr_against_zero():
    # deflating for many trials must not be MORE favorable than PSR vs 0
    sr, n, sk, ku = 0.15, 200, 0.0, 3.0
    psr0 = probabilistic_sharpe_ratio(sr, n, sk, ku, 0.0)
    dsr = deflated_sharpe_ratio(sr, n, sk, ku, n_trials=50, sr_variance=0.01)
    assert dsr["deflated_sharpe_ratio"] <= psr0
    assert dsr["expected_max_sharpe_benchmark"] > 0.0


def test_effective_trials_bounds():
    assert math.isclose(effective_trials(30, 0.0), 30.0)  # independent
    assert effective_trials(30, 0.5) < 30.0  # correlated -> fewer
    assert effective_trials(30, 0.99) < 2.0  # near-perfectly correlated -> ~1


def test_effective_trials_clips_negative_correlation():
    assert math.isclose(effective_trials(10, -0.5), 10.0)  # neg rho clipped to 0


def test_psr_rejects_tiny_sample():
    with pytest.raises(ValueError, match="n_obs"):
        probabilistic_sharpe_ratio(0.1, 1, 0.0, 3.0)
