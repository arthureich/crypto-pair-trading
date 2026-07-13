"""Tests for src/research/vol_target.py (TASK-TSM-007 vol-target overlay)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.vol_target import (
    VolTargetError,
    apply_vol_target,
    vol_target_scale,
)


def test_scale_is_causal_future_return_does_not_change_earlier_scale() -> None:
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0, 1, 60))
    s1 = vol_target_scale(r, window=5)
    mutated = r.copy()
    mutated.iloc[40:] = 99.0
    s2 = vol_target_scale(mutated, window=5)
    # scales strictly before the mutation are unchanged (shift(1) + trailing only)
    for i in range(40):
        assert s1.iloc[i] == pytest.approx(s2.iloc[i])


def test_scale_downweights_high_vol_and_upweights_low_vol() -> None:
    # Low-vol stretch then high-vol stretch; once past warm-up, the low-vol
    # regime should carry a larger scale than the high-vol regime.
    low = np.full(30, 0.2) * np.array([1, -1] * 15)  # small swings
    high = np.full(30, 3.0) * np.array([1, -1] * 15)  # large swings
    r = pd.Series(np.concatenate([low, high]))
    s = vol_target_scale(r, window=6, cap=10.0)
    assert s.iloc[20] > s.iloc[55]  # low-vol period scaled up vs high-vol period


def test_scale_respects_cap_and_is_nonnegative() -> None:
    r = pd.Series([0.0] * 10 + [5.0, -5.0] * 10)  # near-zero vol then jumps
    s = vol_target_scale(r, window=4, cap=2.5)
    assert (s <= 2.5 + 1e-9).all()
    assert (s >= 0.0).all()


def test_warmup_scale_is_one() -> None:
    r = pd.Series(np.arange(10.0))
    s = vol_target_scale(r, window=5)
    assert s.iloc[0] == pytest.approx(1.0)  # sigma undefined at the start -> 1.0


def test_apply_vol_target_scales_returns() -> None:
    r = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02, 0.0, 0.01, -0.03, 0.02, 0.01])
    scaled = apply_vol_target(r, window=3, cap=3.0)
    s = vol_target_scale(r, window=3, cap=3.0)
    for a, b, sc in zip(scaled, r, s, strict=True):
        assert a == pytest.approx(b * sc)


def test_fail_closed_on_bad_params() -> None:
    r = pd.Series([0.1, 0.2, 0.3])
    with pytest.raises(VolTargetError, match="window"):
        vol_target_scale(r, window=1)
    with pytest.raises(VolTargetError, match="cap"):
        vol_target_scale(r, cap=0.0)
