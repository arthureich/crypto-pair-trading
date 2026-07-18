"""Tests for the pure helpers in scripts/run_tsm_liquidity_stress.py (TASK-TSM-015).

Only the pure classification/metric helpers are tested (the tier backtests reuse
the already-tested tsm_trend engine and read cached bars, same accepted precedent
as the other scripts). Guarantees: the liquidity proxy sums by day then takes the
median, the tercile split assigns ascending-liquidity thirds to LOW/MID/HIGH, and
_metrics reports Sharpe/maxDD/net (None on a flat stream).
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

_SPEC = importlib.util.spec_from_file_location(
    "run_tsm_liquidity_stress",
    Path(__file__).resolve().parents[1] / "scripts" / "run_tsm_liquidity_stress.py",
)
ls = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ls)

_DAY_MS = 86_400_000


def test_daily_dollar_volume_median_sums_by_day():
    # day 0: 100+200=300 ; day 1: 50 ; day 2: 100+100+200=400 -> median(300,50,400)=300
    df = pd.DataFrame(
        {
            "open_time": [0, 3_600_000, _DAY_MS, 2 * _DAY_MS, 2 * _DAY_MS + 1, 2 * _DAY_MS + 2],
            "quote_volume": [100.0, 200.0, 50.0, 100.0, 100.0, 200.0],
        }
    )
    assert math.isclose(ls.daily_dollar_volume_median(df), 300.0)


def test_daily_dollar_volume_median_ignores_nan_and_empty():
    df = pd.DataFrame({"open_time": [0, 3_600_000], "quote_volume": [np.nan, np.nan]})
    assert ls.daily_dollar_volume_median(df) == 0.0


def test_tercile_split_ascending_assigns_low_first():
    ranked = ["a", "b", "c", "d", "e", "f"]  # ascending liquidity
    tiers = ls.tercile_split(ranked)
    assert tiers["LOW"] == ["a", "b"]
    assert tiers["MID"] == ["c", "d"]
    assert tiers["HIGH"] == ["e", "f"]


def test_tercile_split_covers_all_symbols_no_overlap():
    ranked = [f"s{i}" for i in range(10)]
    tiers = ls.tercile_split(ranked)
    merged = tiers["LOW"] + tiers["MID"] + tiers["HIGH"]
    assert sorted(merged) == sorted(ranked)
    assert len(set(merged)) == len(ranked)


def test_metrics_basic():
    net = np.array([0.01, -0.02, 0.03, 0.005, -0.01])
    turn = np.array([0.4, 0.5, 0.3, 0.45, 0.5])
    m = ls._metrics(net, turn)
    a = net.astype(float)
    assert math.isclose(m["sharpe"], a.mean() / a.std(ddof=1) * ls._ANN, rel_tol=1e-9)
    assert math.isclose(m["net"], a.sum(), rel_tol=1e-9)
    assert m["max_dd"] >= 0.0
    assert math.isclose(m["mean_turnover"], turn.mean(), rel_tol=1e-9)


def test_metrics_flat_stream_returns_none_sharpe():
    m = ls._metrics(np.array([0.2, 0.2, 0.2]))
    assert m["sharpe"] is None


def test_metrics_too_few_points():
    m = ls._metrics(np.array([0.1]))
    assert m["sharpe"] is None and m["n"] == 1
