"""Tests for basis data helpers (TASK-BASIS-001). Pure; a synthetic ZIP for parse."""

from __future__ import annotations

import datetime as dt
import io
import zipfile

from src.research.basis_data import (
    expiry_symbol,
    last_friday,
    months_ending_at,
    parse_klines,
    quarterly_expiries,
)


def test_last_friday_known_values():
    assert last_friday(2024, 6) == dt.date(2024, 6, 28)  # matches the probed contract
    assert last_friday(2023, 3) == dt.date(2023, 3, 31)
    assert last_friday(2024, 12) == dt.date(2024, 12, 27)


def test_quarterly_expiries_range():
    exps = quarterly_expiries((2024, 1), (2024, 12))
    assert exps == [
        dt.date(2024, 3, 29),
        dt.date(2024, 6, 28),
        dt.date(2024, 9, 27),
        dt.date(2024, 12, 27),
    ]


def test_quarterly_expiries_respects_bounds():
    exps = quarterly_expiries((2024, 4), (2024, 10))  # only Jun and Sep in-range
    assert exps == [dt.date(2024, 6, 28), dt.date(2024, 9, 27)]


def test_expiry_symbol_format():
    assert expiry_symbol("BTCUSDT", dt.date(2024, 6, 28)) == "BTCUSDT_240628"


def test_months_ending_at_wraps_year():
    assert months_ending_at(dt.date(2024, 2, 23), 4) == ["2023-11", "2023-12", "2024-01", "2024-02"]


def _zip(rows: list[list], header: bool) -> bytes:
    buf = io.StringIO()
    if header:
        buf.write("open_time,open,high,low,close,volume,close_time,quote_volume,count,tb,tbq,ig\n")
    for r in rows:
        buf.write(",".join(str(x) for x in r) + "\n")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("k.csv", buf.getvalue())
    return out.getvalue()


def _row(ot, close):
    return [ot, 1, 1, 1, close, 1, ot + 3599999, 1, 1, 1, 1, 0]


def test_parse_klines_with_header_ms():
    raw = _zip([_row(1714521600000, 61116.1), _row(1714525200000, 61200.0)], header=True)
    df = parse_klines(raw)
    assert list(df["open_time"]) == [1714521600000, 1714525200000]
    assert df["close"].iloc[0] == 61116.1


def test_parse_klines_no_header():
    raw = _zip([_row(1714521600000, 100.0)], header=False)
    df = parse_klines(raw)
    assert df["open_time"].iloc[0] == 1714521600000
    assert df["close"].iloc[0] == 100.0


def test_parse_klines_microseconds_normalized_to_ms():
    raw = _zip([_row(1714521600000000, 100.0)], header=True)  # microseconds
    df = parse_klines(raw)
    assert df["open_time"].iloc[0] == 1714521600000  # divided by 1000
