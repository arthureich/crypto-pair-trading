"""Tests for the pure temporal helpers in scripts/run_tsm_temporal_robustness.py
(TASK-TSM-014).

Only the pure metric helpers are tested (the script's stream reconstruction reads
cached bars and reuses the already-tested tsm_trend backtest, same accepted
precedent as the other scripts). The guarantees: sub-period slicing respects the
fixed edges, rolling-window stats and negative-run detection are correct, and
drawdown-duration counts peak-to-recovery.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

_SPEC = importlib.util.spec_from_file_location(
    "run_tsm_temporal_robustness",
    Path(__file__).resolve().parents[1] / "scripts" / "run_tsm_temporal_robustness.py",
)
tr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tr)


def test_sharpe_matches_formula():
    x = np.array([0.01, -0.02, 0.03, 0.005, -0.01])
    a = x.astype(float)
    expected = a.mean() / a.std(ddof=1) * tr._ANN
    assert math.isclose(tr._sharpe(x), expected, rel_tol=1e-9)


def test_sharpe_none_when_too_few_or_zero_var():
    assert tr._sharpe([0.5]) is None
    assert tr._sharpe([0.2, 0.2, 0.2]) is None  # zero variance


def test_sub_period_sharpe_slices_on_fixed_edges():
    # one point in each of the 3 fixed sub-periods + boundary check
    def ms(ts: str) -> int:
        return int(pd.Timestamp(ts, tz="UTC").value // 1_000_000)

    times = np.array([ms("2023-07-01"), ms("2023-09-01"), ms("2024-09-01"), ms("2025-09-01")])
    pnl = np.array([0.01, 0.02, -0.01, 0.03])
    out = tr.sub_period_sharpe(times, pnl)
    # period 1 has 2 points -> a Sharpe; periods 2 and 3 have 1 point -> None
    assert out[tr._LABELS[0]] is not None
    assert out[tr._LABELS[1]] is None
    assert out[tr._LABELS[2]] is None


def test_sub_period_boundary_is_half_open():
    # a point exactly on 2024-06-01 belongs to period 2, not period 1
    edge = int(pd.Timestamp("2024-06-01", tz="UTC").value // 1_000_000)
    just_before = int(pd.Timestamp("2024-05-31 23:00", tz="UTC").value // 1_000_000)
    times = np.array([just_before, edge, edge + 1])
    pnl = np.array([0.01, 0.02, 0.03])
    out = tr.sub_period_sharpe(times, pnl)
    assert out[tr._LABELS[0]] is None  # only 1 point before the edge
    assert out[tr._LABELS[1]] is not None  # 2 points at/after the edge


def test_rolling_sharpe_length_and_window():
    pnl = np.arange(1, 11, dtype=float) * 0.01
    r = tr.rolling_sharpe(pnl, window=4)
    assert r.size == len(pnl) - 4 + 1
    # monotone increasing pnl -> every window has positive mean -> positive Sharpe
    assert np.all(r > 0)


def test_rolling_sharpe_empty_when_shorter_than_window():
    assert tr.rolling_sharpe(np.array([0.1, 0.2]), window=5).size == 0


def test_longest_neg_run():
    assert tr._longest_neg_run(np.array([1.0, -1, -1, 2, -1, -1, -1, 3])) == 3
    assert tr._longest_neg_run(np.array([1.0, 2, 3])) == 0
    assert tr._longest_neg_run(np.array([-1.0, -1, -1])) == 3


def test_rolling_stats_fields():
    pnl = np.array([0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.04, -0.03])
    s = tr.rolling_stats(pnl, window=3)
    assert s["n_windows"] == len(pnl) - 3 + 1
    assert 0.0 <= s["frac_positive"] <= 1.0
    assert s["min"] <= s["median"] <= s["max"]
    assert s["longest_negative_run"] >= 0


def test_drawdown_duration_simple():
    # equity: rise to peak at idx2, fall for 3 steps, recover at idx6
    pnl = np.array([1.0, 1.0, 1.0, -1.0, -1.0, 0.5, 2.0])
    d = tr.drawdown_duration(pnl)
    # peak at idx2 (equity 3); underwater idx3,4,5; recovers idx6 -> max dur = 6-2 = 4
    assert d["max_duration_rebalances"] == 4
    assert d["max_duration_days"] == 20  # 4 * 5
    assert 0.0 < d["frac_underwater"] < 1.0


def test_drawdown_duration_no_drawdown():
    d = tr.drawdown_duration(np.array([1.0, 1.0, 1.0]))
    assert d["max_duration_rebalances"] == 0
    assert d["frac_underwater"] == 0.0
