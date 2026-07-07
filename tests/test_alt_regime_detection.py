"""Tests for scripts/diagnostic_alt_regime_detection.py (TASK-ALT-003)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from scripts.diagnostic_alt_regime_detection import (
    FORWARD_HORIZON_HOURS,
    RegimeDetectionDiagnosticError,
    _build_feature_panels,
)

HOUR_MS = 3_600_000


def _linear_bars() -> pd.DataFrame:
    rows = []
    for symbol, direction in (("UP", 1.0), ("DOWN", -1.0)):
        for hour in range(80):
            rows.append(
                {
                    "symbol": symbol,
                    "open_time": hour * HOUR_MS,
                    "log_price": direction * 0.01 * hour,
                    "quote_volume": 1_000.0 + hour,
                }
            )
    return pd.DataFrame(rows)


def _synthetic_bars(n_hours: int = 2300) -> pd.DataFrame:
    rows = []
    for symbol_index, symbol in enumerate(("A", "B", "C")):
        direction = -1.0 if symbol == "B" else 1.0
        for hour in range(n_hours):
            trend = direction * 0.0005 * hour
            wave = 0.01 * math.sin(hour / 24.0 + symbol_index)
            rows.append(
                {
                    "symbol": symbol,
                    "open_time": hour * HOUR_MS,
                    "log_price": trend + wave,
                    "quote_volume": 1_000.0 + 10.0 * symbol_index + (hour % 24),
                }
            )
    return pd.DataFrame(rows)


def test_target_is_absolute_future_return_not_signed():
    panels = _build_feature_panels(_linear_bars())
    panel = panels["realized_vol_24h"]
    open_time = 30 * HOUR_MS

    targets = sorted(panel.loc[panel["open_time"] == open_time, "target"].tolist())

    expected_abs_return = 0.01 * FORWARD_HORIZON_HOURS
    assert targets == pytest.approx([expected_abs_return, expected_abs_return])


def test_future_price_mutation_does_not_change_current_features():
    baseline = _synthetic_bars()
    mutated = baseline.copy()
    open_time = 2200 * HOUR_MS
    mutated.loc[mutated["open_time"] > open_time, "log_price"] += 99.0

    baseline_panels = _build_feature_panels(baseline)
    mutated_panels = _build_feature_panels(mutated)

    for feature_name, baseline_panel in baseline_panels.items():
        baseline_features = (
            baseline_panel.loc[baseline_panel["open_time"] == open_time]
            .sort_values("symbol")["feature"]
            .reset_index(drop=True)
        )
        mutated_features = (
            mutated_panels[feature_name]
            .loc[mutated_panels[feature_name]["open_time"] == open_time]
            .sort_values("symbol")["feature"]
            .reset_index(drop=True)
        )
        pd.testing.assert_series_equal(baseline_features, mutated_features)


def test_market_context_features_are_repeated_for_each_symbol():
    panels = _build_feature_panels(_synthetic_bars(n_hours=100))
    panel = panels["market_dispersion_24h"]
    features = panel.loc[panel["open_time"] == 50 * HOUR_MS, "feature"].tolist()

    assert len(features) == 3
    assert len({round(value, 12) for value in features}) == 1


def test_duplicate_rows_fail_closed():
    bars = _linear_bars()
    duplicated = pd.concat([bars, bars.iloc[[0]]], ignore_index=True)

    with pytest.raises(RegimeDetectionDiagnosticError, match="duplicate"):
        _build_feature_panels(duplicated)


def test_missing_column_fail_closed():
    bars = _linear_bars().drop(columns=["quote_volume"])

    with pytest.raises(RegimeDetectionDiagnosticError, match="missing required columns"):
        _build_feature_panels(bars)
