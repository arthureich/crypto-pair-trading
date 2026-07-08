"""Tests for the pure-computation parts of scripts/download_alt_book_depth.py.

Deliberately excludes the real-network download path (no mock) --
consistent with this project's accepted precedent for other Binance
downloaders (see project_control/RISKS.md).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.download_alt_book_depth import (
    PERCENTAGE_LEVELS,
    DailyBookDepthSpec,
    _resample_to_hourly,
    daterange,
)


def test_daterange_half_open():
    days = daterange(date(2023, 6, 1), date(2023, 6, 4))
    assert days == (date(2023, 6, 1), date(2023, 6, 2), date(2023, 6, 3))


def test_daily_book_depth_spec_paths_and_urls():
    spec = DailyBookDepthSpec("BTCUSDT", date(2025, 6, 1))
    assert spec.filename == "BTCUSDT-bookDepth-2025-06-01.zip"
    assert (
        spec.relative_path
        == "data/futures/um/daily/bookDepth/BTCUSDT/BTCUSDT-bookDepth-2025-06-01.zip"
    )
    assert spec.url == (
        "https://data.binance.vision/data/futures/um/daily/bookDepth/BTCUSDT/"
        "BTCUSDT-bookDepth-2025-06-01.zip"
    )
    assert spec.checksum_url == f"{spec.url}.CHECKSUM"
    root = Path("/tmp/raw")
    assert spec.archive_path(root) == root / spec.relative_path
    assert spec.checksum_path(root) == root / f"{spec.relative_path}.CHECKSUM"


def _event_frame(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime([r[0] for r in rows], utc=True),
            "percentage": [r[1] for r in rows],
            "notional": [r[2] for r in rows],
        }
    )


def test_resample_to_hourly_uses_last_observation_in_hour():
    rows = [
        ("2025-06-01 00:00:00", "-1.00", 100.0),
        ("2025-06-01 00:30:00", "-1.00", 110.0),
        ("2025-06-01 00:55:00", "-1.00", 120.0),  # last value in the 00:xx hour
        ("2025-06-01 01:00:00", "-1.00", 130.0),
    ]
    events = _event_frame(rows)
    hourly = _resample_to_hourly(events)
    assert list(hourly["notional_-1.00"]) == [120.0, 130.0]


def test_resample_to_hourly_open_time_matches_epoch_ms_convention():
    events = _event_frame([("2023-06-01 00:00:00", "1.00", 1.0)])
    hourly = _resample_to_hourly(events)
    assert hourly["open_time"].iloc[0] == 1685577600000


def test_resample_to_hourly_includes_all_percentage_columns_even_if_absent():
    events = _event_frame([("2025-06-01 00:00:00", "-1.00", 100.0)])
    hourly = _resample_to_hourly(events)
    for level in PERCENTAGE_LEVELS:
        assert f"notional_{level}" in hourly.columns
    # Levels never observed in this tiny fixture are NaN, not fabricated.
    assert pd.isna(hourly["notional_5.00"].iloc[0])
    assert hourly["notional_-1.00"].iloc[0] == 100.0


def test_resample_to_hourly_drops_fully_empty_hours():
    events = _event_frame(
        [
            ("2025-06-01 00:00:00", "-1.00", 100.0),
            ("2025-06-01 02:00:00", "-1.00", 200.0),
        ]
    )
    hourly = _resample_to_hourly(events)
    assert len(hourly) == 2
    assert list(hourly["notional_-1.00"]) == [100.0, 200.0]


@pytest.mark.parametrize("start,end", [(date(2023, 6, 2), date(2023, 6, 1))])
def test_daterange_rejects_inverted_range_by_returning_empty(start, end):
    assert daterange(start, end) == ()
