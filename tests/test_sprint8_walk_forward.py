from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (
    WalkForwardSplitConfig,
    WalkForwardSplitError,
    build_walk_forward_splits,
)


def test_build_walk_forward_splits_are_causal_and_non_overlapping() -> None:
    bars = pd.DataFrame({"open_time": list(range(10)) + [3]})
    config = WalkForwardSplitConfig(train_bars=4, test_bars=2, step_bars=2)

    folds = build_walk_forward_splits(bars, config)

    assert [(fold.train_start_time, fold.train_end_time) for fold in folds] == [
        (0, 3),
        (2, 5),
        (4, 7),
    ]
    assert [(fold.test_start_time, fold.test_end_time) for fold in folds] == [
        (4, 5),
        (6, 7),
        (8, 9),
    ]
    assert all(fold.train_end_time < fold.test_start_time for fold in folds)
    assert all(fold.train_rows == 4 and fold.test_rows == 2 for fold in folds)


def test_build_walk_forward_splits_fails_when_history_is_too_short() -> None:
    config = WalkForwardSplitConfig(train_bars=4, test_bars=2, step_bars=1)

    with pytest.raises(WalkForwardSplitError, match="need at least 6 unique bars"):
        build_walk_forward_splits([1, 2, 3], config)


def test_walk_forward_config_rejects_zero_windows() -> None:
    with pytest.raises(ValueError, match="positive"):
        WalkForwardSplitConfig(train_bars=0, test_bars=2, step_bars=1)
