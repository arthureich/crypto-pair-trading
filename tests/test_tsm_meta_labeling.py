"""Tests for src/research/tsm_meta_labeling.py (TASK-TSM-004 meta-labeling filter)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.tsm_meta_labeling import (
    FEATURE_NAMES,
    KEEP_THRESHOLD,
    MetaLabelingCvResult,
    TsmMetaLabelingError,
    build_leg_panel,
    run_meta_labeled_cv,
)
from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest

HOUR_MS = 3_600_000


def _bars(n: int) -> pd.DataFrame:
    # Includes BTCUSDT because the btc_trailing feature reads it (the real
    # universe always has it); other names trend up / down / choppy.
    rows = []
    for i in range(n):
        t = i * HOUR_MS
        rows.append((t, "BTCUSDT", 0.001 * i + 0.0005 * (i % 2)))
        rows.append((t, "ETHUSDT", -0.001 * i + 0.001 * (i % 3)))
        rows.append((t, "XRPUSDT", 0.002 * (i % 4)))
    return pd.DataFrame(rows, columns=["open_time", "symbol", "log_price"])


def _cfg() -> TsmTrendConfig:
    return TsmTrendConfig(lookback_hours=5, vol_window_hours=3, hold_hours=4)


def test_build_leg_panel_has_features_binary_label_and_causal_span() -> None:
    panel = build_leg_panel(_bars(80), _cfg())
    assert not panel.empty
    for col in (*FEATURE_NAMES, "label", "decision_time_ms", "label_end_ms", "leg_pnl"):
        assert col in panel.columns
    assert set(panel["label"].unique()).issubset({0, 1})
    # label span ends exactly one hold after the decision time (causal purge basis)
    assert (panel["label_end_ms"] - panel["decision_time_ms"] == 4 * HOUR_MS).all()
    # label matches the sign of the leg pnl (trend called the leg right)
    assert (panel["label"] == (panel["leg_pnl"] > 0).astype(int)).all()


def test_build_leg_panel_fails_closed_on_missing_columns() -> None:
    with pytest.raises(TsmMetaLabelingError, match="missing required columns"):
        build_leg_panel(pd.DataFrame({"open_time": [0], "symbol": ["A"]}), _cfg())


def test_build_leg_panel_features_are_causal() -> None:
    # Mutating bars strictly after a rebalance's label window must not change that
    # rebalance's features (they use only trailing data).
    bars = _bars(80)
    panel = build_leg_panel(bars, _cfg())
    early_t = panel["rebalance_time"].min()
    mutated = bars.copy()
    mutated.loc[mutated["open_time"] >= 70 * HOUR_MS, "log_price"] = 5.0
    panel2 = build_leg_panel(mutated, _cfg())
    a = panel[panel["rebalance_time"] == early_t].set_index("symbol")[list(FEATURE_NAMES)]
    b = panel2[panel2["rebalance_time"] == early_t].set_index("symbol")[list(FEATURE_NAMES)]
    for col in FEATURE_NAMES:
        for sym in a.index:
            assert a.loc[sym, col] == pytest.approx(b.loc[sym, col])


def test_run_meta_labeled_cv_returns_valid_mask_and_folds() -> None:
    panel = build_leg_panel(_bars(200), _cfg())
    res = run_meta_labeled_cv(panel, _cfg(), n_splits=3)
    assert isinstance(res, MetaLabelingCvResult)
    # mask is 0/1 only
    vals = pd.unique(res.keep_mask.to_numpy().ravel())
    assert set(np.nan_to_num(vals, nan=1.0)).issubset({0.0, 1.0})
    # fold metrics reference the frozen threshold and are within [0,1] fractions
    for fm in res.fold_metrics:
        assert 0.0 <= fm.kept_fraction <= 1.0
        assert 0.0 <= fm.base_precision <= 1.0


def test_run_meta_labeled_cv_fails_closed_on_empty_panel() -> None:
    empty = pd.DataFrame(columns=[*FEATURE_NAMES, "label", "decision_time_ms", "label_end_ms"])
    with pytest.raises(TsmMetaLabelingError, match="empty"):
        run_meta_labeled_cv(empty, _cfg())


def test_keep_mask_feeds_backtest_and_all_ones_mask_matches_base() -> None:
    # An all-ones keep mask must leave the base book unchanged (the mask only
    # renormalizes survivors, and keeping everything is a no-op up to unit-gross).
    bars = _bars(120)
    cfg = _cfg()
    base = run_tsm_trend_backtest(bars, cfg)
    ones = pd.DataFrame(
        1.0, index=list(base.rebalance_times), columns=["BTCUSDT", "ETHUSDT", "XRPUSDT"]
    )
    masked = run_tsm_trend_backtest(bars, cfg, keep_mask=ones)
    for a, b in zip(base.tsm_net, masked.tsm_net, strict=True):
        assert a == pytest.approx(b)


def test_threshold_constant_is_half() -> None:
    assert KEEP_THRESHOLD == 0.5
