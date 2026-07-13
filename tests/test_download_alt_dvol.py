"""Tests for the pure parse helper in scripts/download_alt_dvol.py (TASK-ALT-011).

Only `tidy_dvol` is tested (the network fetch is not mocked, same accepted
precedent as the other downloaders). Fixture mimics a Deribit
`get_volatility_index_data` OHLC row list.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "download_alt_dvol",
    Path(__file__).resolve().parents[1] / "scripts" / "download_alt_dvol.py",
)
dl = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dl)


def _rows() -> list[list]:
    # [ts_ms, open, high, low, close]
    return [
        [1685577600000, 43.86, 44.06, 41.54, 42.13],
        [1685664000000, 42.13, 43.0, 41.0, 42.5],
    ]


def test_tidy_dvol_parses_close_and_lowercases_asset() -> None:
    tidy = dl.tidy_dvol(_rows(), "BTC")
    assert list(tidy.columns) == ["asset", "day", "dvol_close"]
    assert (tidy["asset"] == "btc").all()  # base_asset convention
    assert tidy["day"].dt.tz is not None  # UTC-aware, floored to the day
    assert tidy["dvol_close"].iloc[0] == 42.13  # noqa: PLR2004
    assert len(tidy) == 2  # noqa: PLR2004


def test_tidy_dvol_empty_returns_skeleton() -> None:
    empty = dl.tidy_dvol([], "ETH")
    assert list(empty.columns) == ["asset", "day", "dvol_close"]
    assert empty.empty
