"""Tests for the pure-computation parts of scripts/download_alt_open_interest.py.

Deliberately excludes the real-network download path (no mock) --
consistent with this project's accepted precedent for other Binance
downloaders (see project_control/RISKS.md: real-network paths in
historical_dataset.py have the same documented gap).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.download_alt_open_interest import (
    DailyMetricsSpec,
    _resample_to_hourly,
    daterange,
)


def test_daterange_half_open():
    days = daterange(date(2023, 6, 1), date(2023, 6, 4))
    assert days == (date(2023, 6, 1), date(2023, 6, 2), date(2023, 6, 3))


def test_daterange_empty_when_start_equals_end():
    assert daterange(date(2023, 6, 1), date(2023, 6, 1)) == ()


def test_daily_metrics_spec_paths_and_urls():
    spec = DailyMetricsSpec("BTCUSDT", date(2025, 6, 1))
    assert spec.filename == "BTCUSDT-metrics-2025-06-01.zip"
    assert (
        spec.relative_path == "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2025-06-01.zip"
    )
    assert spec.url == (
        "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/"
        "BTCUSDT-metrics-2025-06-01.zip"
    )
    assert spec.checksum_url == f"{spec.url}.CHECKSUM"
    root = Path("/tmp/raw")
    assert spec.archive_path(root) == root / spec.relative_path
    assert spec.checksum_path(root) == root / f"{spec.relative_path}.CHECKSUM"


def _five_min_frame(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "create_time": pd.to_datetime([r[0] for r in rows], utc=True),
            "sum_open_interest": [r[1] for r in rows],
            "sum_open_interest_value": [r[1] * 10.0 for r in rows],
            "count_toptrader_long_short_ratio": [1.0] * len(rows),
            "sum_toptrader_long_short_ratio": [1.0] * len(rows),
            "count_long_short_ratio": [1.0] * len(rows),
            "sum_taker_long_short_vol_ratio": [1.0] * len(rows),
        }
    )


def test_resample_to_hourly_uses_last_observation_in_hour():
    frame = _five_min_frame(
        [
            ("2025-06-01 00:00:00", 100.0),
            ("2025-06-01 00:30:00", 110.0),
            ("2025-06-01 00:55:00", 120.0),  # last value in the 00:xx hour
            ("2025-06-01 01:00:00", 130.0),
        ]
    )
    hourly = _resample_to_hourly(frame)
    assert list(hourly["sum_open_interest"]) == [120.0, 130.0]


def test_resample_to_hourly_open_time_matches_epoch_ms_convention():
    frame = _five_min_frame([("2023-06-01 00:00:00", 1.0)])
    hourly = _resample_to_hourly(frame)
    # 2023-06-01T00:00:00Z is the same epoch boundary already used
    # throughout this project's TSREV/CS fixtures.
    assert hourly["open_time"].iloc[0] == 1685577600000


def test_resample_to_hourly_drops_fully_empty_hours():
    frame = _five_min_frame(
        [
            ("2025-06-01 00:00:00", 100.0),
            ("2025-06-01 02:00:00", 200.0),
        ]
    )
    hourly = _resample_to_hourly(frame)
    # The 01:xx hour has no observations and must not be fabricated.
    assert len(hourly) == 2
    assert list(hourly["sum_open_interest"]) == [100.0, 200.0]


@pytest.mark.parametrize("start,end", [(date(2023, 6, 2), date(2023, 6, 1))])
def test_daterange_rejects_inverted_range_by_returning_empty(start, end):
    # timedelta(days=negative) would never iterate -- range(negative) is
    # empty in Python, so this is naturally safe, not a raised error.
    assert daterange(start, end) == ()
