"""Basis data helpers: quarterly-expiry math + klines parsing (TASK-BASIS-001).

Pure and network-free (the fetch lives in the runner). Handles the two Binance
public-kline gotchas: an optional header row, and open_time that is milliseconds
in older files but microseconds in some newer ones.
"""

from __future__ import annotations

import calendar
import datetime as _dt
import io
import zipfile

import pandas as pd

__all__ = [
    "expiry_symbol",
    "last_friday",
    "months_ending_at",
    "parse_klines",
    "quarterly_expiries",
]

_QUARTER_MONTHS = (3, 6, 9, 12)
_MS_DIGITS_MAX = 1e14  # open_time above this is microseconds, not milliseconds


def last_friday(year: int, month: int) -> _dt.date:
    """Last Friday of the given month (Binance quarterly settlement convention)."""
    last_day = calendar.monthrange(year, month)[1]
    d = _dt.date(year, month, last_day)
    return d - _dt.timedelta(days=(d.weekday() - 4) % 7)


def quarterly_expiries(start: tuple[int, int], end: tuple[int, int]) -> list[_dt.date]:
    """Last-Friday expiry dates for Mar/Jun/Sep/Dec within [start, end] (inclusive
    of month), sorted ascending."""
    (sy, sm), (ey, em) = start, end
    out = []
    for year in range(sy, ey + 1):
        for month in _QUARTER_MONTHS:
            if (year, month) < (sy, sm) or (year, month) > (ey, em):
                continue
            out.append(last_friday(year, month))
    return sorted(out)


def expiry_symbol(base: str, expiry: _dt.date) -> str:
    """Binance dated-contract symbol, e.g. ('BTCUSDT', 2024-06-28) -> BTCUSDT_240628."""
    return f"{base}_{expiry:%y%m%d}"


def months_ending_at(expiry: _dt.date, n_months: int) -> list[str]:
    """The n calendar months ending at the expiry month, as 'YYYY-MM' strings."""
    out = []
    y, m = expiry.year, expiry.month
    for _ in range(n_months):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return sorted(out)


def parse_klines(raw_zip_bytes: bytes) -> pd.DataFrame:
    """Parse a Binance kline monthly ZIP -> DataFrame[open_time(ms int64), close].

    Detects and drops a header row; normalizes microsecond open_time to ms.
    """
    z = zipfile.ZipFile(io.BytesIO(raw_zip_bytes))
    df = pd.read_csv(z.open(z.namelist()[0]), header=None)
    if str(df.iloc[0, 0]).strip() == "open_time":
        df = df.iloc[1:].reset_index(drop=True)
    open_time = pd.to_numeric(df[0], errors="raise").astype("int64")
    if open_time.iloc[0] > _MS_DIGITS_MAX:  # microseconds -> milliseconds
        open_time = open_time // 1000
    close = pd.to_numeric(df[4], errors="raise").astype(float)
    return pd.DataFrame({"open_time": open_time, "close": close}).sort_values("open_time")
