"""Tests for src/research/meta_model_selection.py (TASK-ML-001 CV selection).

Uses a deterministic dummy model (no XGBoost) so the orchestration is
tested in isolation: purged folds, per-fold span evaluation, threshold
sweep, and the min-kept-rebalances floor.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research import meta_labeling
from src.research.funding_carry import FundingCarryConfig
from src.research.meta_labeling import FEATURE_NAMES
from src.research.meta_model_selection import (
    CvSelectionResult,
    MetaModelSelectionError,
    select_meta_model_via_cv,
)

HOUR_MS = 3_600_000
STEP_MS = 8 * HOUR_MS
_RANK_IDX = FEATURE_NAMES.index("cross_sectional_rank")


class _DummyModel:
    """Deterministic stand-in: P = the (clipped) cross_sectional_rank feature."""

    def __init__(self, **hyperparams: float | int) -> None:
        self.hyperparams = hyperparams

    def fit(self, x: np.ndarray, y: np.ndarray) -> _DummyModel:  # noqa: ARG002
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        p = np.clip(x[:, _RANK_IDX], 0.05, 0.95)
        return np.column_stack([1.0 - p, p])


def _dummy_factory(**hyperparams: float | int) -> _DummyModel:
    return _DummyModel(**hyperparams)


def _swap_heavy_bars() -> pd.DataFrame:
    # 3 symbols, K=1. C stays highest (short). A and B alternate as the lowest
    # funding by > the 6bps swap threshold, forcing a long swap almost every
    # rebalance -> many post-warm-up entries at distinct times.
    rows = []
    for i in range(48):
        t = i * STEP_MS
        a_rate = -0.02 if i % 2 == 0 else -0.01
        b_rate = -0.01 if i % 2 == 0 else -0.02
        rows.append((t, "AAA", 0.02 * (i % 4), 1000.0 + 50 * (i % 4), a_rate))
        rows.append((t, "BBB", 0.02 * ((i + 1) % 4), 1000.0 + 50 * ((i + 1) % 4), b_rate))
        rows.append((t, "CCC", 0.02 * ((i + 2) % 4), 1000.0 + 50 * ((i + 2) % 4), 0.02))
    return pd.DataFrame(
        rows, columns=["open_time", "symbol", "log_price", "quote_volume", "funding_rate_asof"]
    )


@pytest.fixture
def _small_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meta_labeling, "FORWARD_HORIZON_HOURS", 2)
    monkeypatch.setattr(meta_labeling, "WEEK_HOURS", 3)
    monkeypatch.setattr(meta_labeling, "ROLLING_WINDOW_HOURS", 4)


def test_selects_a_hyperparameter_and_threshold_from_the_grid(_small_windows: None) -> None:
    result = select_meta_model_via_cv(
        _swap_heavy_bars(),
        FundingCarryConfig(k=1),
        model_factory=_dummy_factory,
        hyperparameter_grid=[{"max_depth": 2}, {"max_depth": 3}],
        thresholds=[0.2, 0.5, 0.8],
        n_splits=2,
        embargo_ms=STEP_MS,
        min_kept_rebalances=1,
    )

    assert isinstance(result, CvSelectionResult)
    assert result.best_hyperparams in ({"max_depth": 2}, {"max_depth": 3})
    assert result.best_threshold in (0.2, 0.5, 0.8)
    assert result.n_folds == 2
    assert len(result.per_fold) == 2
    assert np.isfinite(result.mean_filtered_profit_factor)
    # Every reported fold met the kept-rebalances floor.
    assert all(m.kept_rebalances >= 1 for m in result.per_fold)


def test_fails_closed_when_no_candidate_meets_the_kept_floor(_small_windows: None) -> None:
    with pytest.raises(MetaModelSelectionError, match="kept >="):
        select_meta_model_via_cv(
            _swap_heavy_bars(),
            FundingCarryConfig(k=1),
            model_factory=_dummy_factory,
            hyperparameter_grid=[{"max_depth": 2}],
            thresholds=[0.5],
            n_splits=2,
            embargo_ms=STEP_MS,
            min_kept_rebalances=10_000,  # impossibly high
        )


def test_fails_closed_on_empty_grid_or_thresholds(_small_windows: None) -> None:
    with pytest.raises(MetaModelSelectionError, match="hyperparameter_grid"):
        select_meta_model_via_cv(
            _swap_heavy_bars(),
            FundingCarryConfig(k=1),
            model_factory=_dummy_factory,
            hyperparameter_grid=[],
            thresholds=[0.5],
            n_splits=2,
            embargo_ms=STEP_MS,
            min_kept_rebalances=1,
        )
    with pytest.raises(MetaModelSelectionError, match="thresholds"):
        select_meta_model_via_cv(
            _swap_heavy_bars(),
            FundingCarryConfig(k=1),
            model_factory=_dummy_factory,
            hyperparameter_grid=[{"max_depth": 2}],
            thresholds=[],
            n_splits=2,
            embargo_ms=STEP_MS,
            min_kept_rebalances=1,
        )
