"""Tests for the pure stat helpers in scripts/run_tsm_stat_characterization.py
(TASK-TSM-013).

Only the pure aggregation helpers are tested (the script's data collection reads
committed JSON artifacts, same accepted precedent as the other scripts). The key
guarantee is that the bootstrap CI is REPRODUCIBLE (fixed seed) -- the
pre-register claims determinism.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "run_tsm_stat_characterization",
    Path(__file__).resolve().parents[1] / "scripts" / "run_tsm_stat_characterization.py",
)
sc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sc)


def test_describe_basic_stats():
    d = sc._describe([1.0, 2.0, 3.0, 4.0])
    assert d["n"] == 4
    assert math.isclose(d["mean"], 2.5)
    assert math.isclose(d["median"], 2.5)
    assert math.isclose(d["min"], 1.0)
    assert math.isclose(d["max"], 4.0)
    # sample std (ddof=1) of 1..4
    assert math.isclose(d["std"], 1.2909944487358056, rel_tol=1e-9)


def test_describe_single_element_zero_std():
    d = sc._describe([0.7])
    assert d["n"] == 1
    assert d["std"] == 0.0
    assert d["mean"] == d["median"] == d["min"] == d["max"] == 0.7


def test_bd_extracts_three_fields():
    out = sc._bd({"sharpe": 1.1, "max_dd": 0.3, "net": 2.0, "extra": 9})
    assert out == {"sharpe": 1.1, "max_dd": 0.3, "net": 2.0}


def test_boot_ci_is_reproducible_and_brackets_mean():
    x = [0.462, 0.577, 0.650, 0.832, 0.970, 0.987, 1.004]
    ci1 = sc._boot_ci(x)
    ci2 = sc._boot_ci(x)
    assert ci1 == ci2  # fixed seed -> identical across calls
    lo, hi = ci1
    assert lo < sum(x) / len(x) < hi
    assert lo <= hi


def test_t_ci_matches_hand_computation():
    x = [1.0, 2.0, 3.0]  # n=3, df=2, tcrit=4.303
    lo, hi = sc._t_ci(x)
    mean = 2.0
    se = 1.0 / math.sqrt(3)  # sample std = 1.0
    assert math.isclose(lo, mean - 4.303 * se, rel_tol=1e-6)
    assert math.isclose(hi, mean + 4.303 * se, rel_tol=1e-6)


def test_t_ci_degenerate_single_point():
    assert sc._t_ci([0.5]) == [0.5, 0.5]
