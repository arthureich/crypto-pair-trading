"""Tests for the pure parse/normalize helpers in scripts/download_alt_onchain.py.

Only `tidy_rows` and `build_panel` are tested (the network fetch is not mocked,
same accepted precedent as the S3 downloaders). Uses a small fixture that mimics
a Coin Metrics community `timeseries/asset-metrics` response payload.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

_SPEC = importlib.util.spec_from_file_location(
    "download_alt_onchain",
    Path(__file__).resolve().parents[1] / "scripts" / "download_alt_onchain.py",
)
dl = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dl)


def _rows() -> list[dict]:
    return [
        {"asset": "btc", "time": "2023-06-01T00:00:00.000000000Z", "CapMVRVCur": "2.1"},
        {"asset": "btc", "time": "2023-06-02T00:00:00.000000000Z", "CapMVRVCur": "2.2"},
        {"asset": "eth", "time": "2023-06-01T00:00:00.000000000Z", "CapMVRVCur": "1.5"},
    ]


def test_tidy_rows_parses_day_and_numeric_value() -> None:
    tidy = dl.tidy_rows(_rows(), "CapMVRVCur")
    assert list(tidy.columns) == ["asset", "day", "CapMVRVCur"]
    assert len(tidy) == 3
    assert tidy["CapMVRVCur"].dtype.kind == "f"  # coerced to float
    assert tidy["day"].dt.tz is not None  # UTC-aware, floored to the day
    assert tidy.loc[tidy["asset"] == "eth", "CapMVRVCur"].iloc[0] == 1.5


def test_tidy_rows_drops_missing_and_empty() -> None:
    rows = [
        {"asset": "btc", "time": "2023-06-01T00:00:00Z", "CapMVRVCur": "2.1"},
        {"asset": "btc", "time": "2023-06-02T00:00:00Z", "CapMVRVCur": None},
        {"asset": "btc", "time": "2023-06-03T00:00:00Z"},  # key absent entirely
    ]
    tidy = dl.tidy_rows(rows, "CapMVRVCur")
    assert len(tidy) == 1  # only the valid numeric row survives
    assert dl.tidy_rows([], "CapMVRVCur").empty


def test_build_panel_outer_merges_on_asset_day_and_sorts() -> None:
    mvrv = dl.tidy_rows(_rows(), "CapMVRVCur")
    adr_rows = [
        {"asset": "btc", "time": "2023-06-01T00:00:00Z", "AdrActCnt": "900000"},
        {"asset": "eth", "time": "2023-06-02T00:00:00Z", "AdrActCnt": "500000"},  # new day
    ]
    adr = dl.tidy_rows(adr_rows, "AdrActCnt")
    panel = dl.build_panel([mvrv, adr])

    assert list(panel.columns) == ["asset", "day", "CapMVRVCur", "AdrActCnt"]
    # 3 mvrv (asset,day) keys + eth 2023-06-02 which mvrv lacks = 4 rows
    assert len(panel) == 4
    # eth 2023-06-02 has AdrActCnt but no MVRV (outer join keeps it, MVRV NaN)
    eth_0602 = panel[(panel["asset"] == "eth") & (panel["day"].dt.day == 2)]  # noqa: PLR2004
    assert pd.isna(eth_0602["CapMVRVCur"].iloc[0])
    assert eth_0602["AdrActCnt"].iloc[0] == 500000  # noqa: PLR2004
    # deterministic sort: (asset, day) ascending
    assert panel["asset"].is_monotonic_increasing


def test_build_panel_all_empty_returns_skeleton() -> None:
    empty = dl.build_panel([pd.DataFrame(columns=["asset", "day", "TxCnt"])])
    assert list(empty.columns) == ["asset", "day"]
    assert empty.empty
