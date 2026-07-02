from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_sprint8_backtest.py"
_SPEC = importlib.util.spec_from_file_location("run_sprint8_backtest", _SCRIPT_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

HOUR_MS = 60 * 60 * 1000


def _intent(*, side_a: str, side_b: str, beta: float, created_at: int) -> SimpleNamespace:
    return SimpleNamespace(side_a=side_a, side_b=side_b, beta=beta, created_at=created_at)


def _pair_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open_time": [0, HOUR_MS, 2 * HOUR_MS],
            "log_price_a": [0.0, 0.01, 0.03],
            "log_price_b": [0.0, 0.02, 0.05],
        }
    )


def test_one_hour_gross_edge_weights_leg_b_by_beta() -> None:
    intent = _intent(side_a="SELL", side_b="BUY", beta=2.0, created_at=0)

    edge, exit_time = _MODULE._one_hour_gross_edge_bps(intent, _pair_bars())

    return_a_bps = 0.01 * 10_000.0
    return_b_bps = 0.02 * 10_000.0
    expected = -return_a_bps + 2.0 * return_b_bps
    assert edge == pytest.approx(expected)
    assert exit_time == HOUR_MS


def test_one_hour_gross_edge_returns_none_without_next_bar() -> None:
    intent = _intent(side_a="SELL", side_b="BUY", beta=1.0, created_at=2 * HOUR_MS)

    result = _MODULE._one_hour_gross_edge_bps(intent, _pair_bars())

    assert result is None


def test_one_hour_gross_edge_returns_none_when_signal_bar_missing() -> None:
    intent = _intent(side_a="SELL", side_b="BUY", beta=1.0, created_at=999)

    result = _MODULE._one_hour_gross_edge_bps(intent, _pair_bars())

    assert result is None


def test_is_in_test_window_is_inclusive_of_fold_boundaries() -> None:
    fold = SimpleNamespace(test_start_time=100, test_end_time=200)

    assert _MODULE._is_in_test_window(100, (fold,)) is True
    assert _MODULE._is_in_test_window(200, (fold,)) is True
    assert _MODULE._is_in_test_window(99, (fold,)) is False
    assert _MODULE._is_in_test_window(201, (fold,)) is False


def test_round_trip_symbol_cost_map_sums_entry_and_exit() -> None:
    hourly_cost = pd.DataFrame(
        {
            "symbol": ["ARBUSDT", "ARBUSDT", "OPUSDT", "OPUSDT"],
            "cost_available_time": [0, HOUR_MS, 0, HOUR_MS],
            "median_spread_bps_1h": [1.0, 1.5, 2.0, 2.5],
        }
    )

    cost_map = _MODULE._round_trip_symbol_cost_map(
        hourly_cost, "ARBUSDT/OPUSDT", entry_time=0, exit_time=HOUR_MS
    )

    assert cost_map == {"ARBUSDT": 1.0 + 1.5, "OPUSDT": 2.0 + 2.5}


def test_latest_symbol_cost_fails_closed_without_causal_row() -> None:
    hourly_cost = pd.DataFrame(
        {
            "symbol": ["ARBUSDT"],
            "cost_available_time": [HOUR_MS],
            "median_spread_bps_1h": [1.0],
        }
    )

    with pytest.raises(ValueError, match="no causal cost available"):
        _MODULE._latest_symbol_cost_bps(hourly_cost, "ARBUSDT", created_at=0)
