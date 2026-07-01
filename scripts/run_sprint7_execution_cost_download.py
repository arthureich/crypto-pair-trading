#!/usr/bin/env python3
"""Download and normalize real Binance bookTicker archives for a bounded pilot.

This script is intentionally scoped: full 2023-06 through 2026-05 bookTicker
coverage does not exist on Binance Public Data (see TASK-007-10), and even the
verified ~11-month sub-window is hundreds of GB across 20 symbols. This script
downloads real, checksum-verified bookTicker archives for a caller-supplied
symbol list and month range, normalizes them, and aggregates hourly spread
statistics -- producing genuine (not fabricated or sampled-away) execution-cost
evidence for whatever scope was requested.

Uses DAILY archives, not monthly. A monthly bookTicker archive for a mid-cap
USD-M symbol decompresses into multiple GB of tick-level CSV; loading one
month into memory at once (as the first version of this script did) triggers
an OOM kill. A daily archive is roughly 1/30th of that size, so this script
downloads, verifies, normalizes, and aggregates one symbol-day at a time and
frees the raw frame before moving to the next day, bounding peak memory to
one symbol-day of tick data regardless of how many symbols or days are
requested.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.execution_cost_evidence import (  # noqa: E402
    HOURLY_COST_COLUMNS,
    aggregate_book_ticker_hourly,
    normalize_book_ticker_frame,
)
from src.research.historical_dataset import (  # noqa: E402
    BINANCE_PUBLIC_DATA_BASE_URL,
    HistoricalDatasetError,
    read_zip_csv,
    sha256_file,
    verify_checksum_file,
)

DEFAULT_STALE_GAP_MS = 60_000
DECEMBER = 12


def main() -> int:
    args = _parse_args()
    days = _day_range(args.start_month, args.end_month_exclusive)
    symbols = tuple(sorted({symbol.strip().upper() for symbol in args.symbols}))
    print(f"planned {len(symbols)} symbols x {len(days)} days", file=sys.stderr)

    hourly_frames = []
    for symbol in symbols:
        for day in days:
            hourly_frames.append(
                _process_one_symbol_day(
                    symbol,
                    day,
                    data_root=args.data_root,
                    dataset_version=args.dataset_version,
                    overwrite=args.overwrite,
                    timeout_seconds=args.timeout_seconds,
                    stale_gap_threshold_ms=args.stale_gap_threshold_ms,
                )
            )
    hourly = (
        pd.concat(hourly_frames, ignore_index=True)
        .sort_values(["symbol", "open_time"], kind="mergesort")
        .reset_index(drop=True)
        if hourly_frames
        else pd.DataFrame(columns=HOURLY_COST_COLUMNS)
    )
    args.output_hourly_csv.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(args.output_hourly_csv, index=False)
    print(
        f"wrote {len(hourly)} hourly cost rows for "
        f"{hourly['symbol'].nunique() if not hourly.empty else 0} symbols "
        f"to {args.output_hourly_csv}",
        file=sys.stderr,
    )
    return 0


def _process_one_symbol_day(
    symbol: str,
    day: date,
    *,
    data_root: Path,
    dataset_version: str,
    overwrite: bool,
    timeout_seconds: float,
    stale_gap_threshold_ms: int,
) -> pd.DataFrame:
    filename = f"{symbol}-bookTicker-{day.isoformat()}.zip"
    relative_path = f"data/futures/um/daily/bookTicker/{symbol}/{filename}"
    archive_path = data_root / relative_path
    checksum_path = data_root / f"{relative_path}.CHECKSUM"
    base_url = BINANCE_PUBLIC_DATA_BASE_URL.rstrip("/")
    _download_url(f"{base_url}/{relative_path}", archive_path, overwrite, timeout_seconds)
    _download_url(
        f"{base_url}/{relative_path}.CHECKSUM", checksum_path, overwrite, timeout_seconds
    )
    verify_checksum_file(archive_path, checksum_path)

    raw = read_zip_csv(archive_path)
    normalized = normalize_book_ticker_frame(
        raw,
        symbol,
        source_path=str(archive_path),
        source_checksum=sha256_file(archive_path),
        dataset_version=dataset_version,
    )
    hourly = aggregate_book_ticker_hourly(
        normalized,
        stale_gap_threshold_ms=stale_gap_threshold_ms,
    )
    print(
        f"{symbol} {day.isoformat()}: {len(raw)} raw rows, "
        f"{len(normalized)} verified quotes, {len(hourly)} hourly rows",
        file=sys.stderr,
    )
    del raw, normalized
    return hourly


def _download_url(url: str, path: Path, overwrite: bool, timeout_seconds: float) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310
            path.write_bytes(response.read())
    except OSError as exc:
        raise HistoricalDatasetError(f"failed to download {url}: {exc}") from exc


def _day_range(start_month: str, end_month_exclusive: str) -> tuple[date, ...]:
    start = _month_start(start_month)
    end = _month_start(end_month_exclusive)
    if start >= end:
        raise ValueError("start_month must be earlier than end_month_exclusive")
    days = []
    current = start
    while current < end:
        days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def _month_start(month: str) -> date:
    year_text, month_text = month.split("-", maxsplit=1)
    return date(int(year_text), int(month_text), 1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--start-month", required=True)
    parser.add_argument("--end-month-exclusive", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--output-hourly-csv", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--stale-gap-threshold-ms", type=int, default=DEFAULT_STALE_GAP_MS)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
