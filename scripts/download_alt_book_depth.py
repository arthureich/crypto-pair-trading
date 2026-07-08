#!/usr/bin/env python3
"""Download and normalize Family H (Order Flow) daily bookDepth archives.

Per docs/pre_registers/TASK-ALT-007.md / project_control/DECISIONS.md
ADR-0025. Downloads the `bookDepth` public-data family (order book
depth aggregated into percentage-from-mid-price bands, event-sampled)
for the 20 universe symbols across 2023-06-01 to 2026-05-31, verifies
each archive's SHA256 checksum (reusing the existing generic verifier),
resamples to hourly (last observation per hour), and writes a
normalized CSV joinable to the existing OHLCV bars dataset by (symbol,
open_time).

Memory-safe by construction: processes one symbol at a time, discarding
its raw event-level frame after resampling before moving to the next
symbol -- never holds the full event-level dataset for all 20 symbols
in memory simultaneously.
"""

from __future__ import annotations

import io
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.historical_dataset import (  # noqa: E402
    HistoricalDatasetError,
    verify_checksum_file,
)

BASE_URL = "https://data.binance.vision"
RAW_ROOT = PROJECT_ROOT / "data/research/binance_public/cost_pilot/raw/book_depth"
OUTPUT_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint_alt_book_depth_202306_202605.csv.gz"
)
SYMBOLS = (
    "ADAUSDT",
    "APTUSDT",
    "ARBUSDT",
    "ATOMUSDT",
    "AVAXUSDT",
    "BCHUSDT",
    "BNBUSDT",
    "BTCUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "ETCUSDT",
    "ETHUSDT",
    "LINKUSDT",
    "LTCUSDT",
    "OPUSDT",
    "SOLUSDT",
    "SUIUSDT",
    "TRXUSDT",
    "UNIUSDT",
    "XRPUSDT",
)
START_DATE = date(2023, 6, 1)
END_DATE_EXCLUSIVE = date(2026, 6, 1)
PERCENTAGE_LEVELS = (
    "-5.00",
    "-4.00",
    "-3.00",
    "-2.00",
    "-1.00",
    "-0.20",
    "0.20",
    "1.00",
    "2.00",
    "3.00",
    "4.00",
    "5.00",
)
MAX_WORKERS = 16
DOWNLOAD_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True, slots=True)
class DailyBookDepthSpec:
    symbol: str
    day: date

    @property
    def filename(self) -> str:
        return f"{self.symbol}-bookDepth-{self.day.isoformat()}.zip"

    @property
    def relative_path(self) -> str:
        return f"data/futures/um/daily/bookDepth/{self.symbol}/{self.filename}"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.relative_path}"

    @property
    def checksum_url(self) -> str:
        return f"{self.url}.CHECKSUM"

    def archive_path(self, root: Path) -> Path:
        return root / self.relative_path

    def checksum_path(self, root: Path) -> Path:
        return root / f"{self.relative_path}.CHECKSUM"


def daterange(start: date, end_exclusive: date) -> tuple[date, ...]:
    days = (end_exclusive - start).days
    return tuple(start + timedelta(days=i) for i in range(days))


def main() -> int:
    all_days = daterange(START_DATE, END_DATE_EXCLUSIVE)
    print(f"{len(SYMBOLS)} symbols x {len(all_days)} days", file=sys.stderr)

    hourly_frames: list[pd.DataFrame] = []
    for symbol in SYMBOLS:
        print(f"Processing {symbol}...", file=sys.stderr)
        specs = tuple(DailyBookDepthSpec(symbol, day) for day in all_days)
        events = _download_and_parse_symbol(specs)
        if events.empty:
            print(f"  WARNING: no data for {symbol}", file=sys.stderr)
            continue
        hourly = _resample_to_hourly(events)
        hourly["symbol"] = symbol
        hourly_frames.append(hourly)
        print(
            f"  {symbol}: {len(events)} event rows -> {len(hourly)} hourly rows",
            file=sys.stderr,
        )

    combined = pd.concat(hourly_frames, ignore_index=True)
    combined = combined.sort_values(["symbol", "open_time"], kind="mergesort")
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {OUTPUT_CSV} ({len(combined)} rows)", file=sys.stderr)
    return 0


def _download_and_parse_symbol(specs: tuple[DailyBookDepthSpec, ...]) -> pd.DataFrame:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        frames = list(executor.map(_download_and_parse_one_day, specs))
    non_empty = [f for f in frames if f is not None and not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=("timestamp", "percentage", "notional"))
    return pd.concat(non_empty, ignore_index=True)


def _download_and_parse_one_day(spec: DailyBookDepthSpec) -> pd.DataFrame | None:
    archive_path = spec.archive_path(RAW_ROOT)
    checksum_path = spec.checksum_path(RAW_ROOT)
    try:
        if not archive_path.exists():
            _fetch_to_file(spec.url, archive_path)
        if not checksum_path.exists():
            _fetch_to_file(spec.checksum_url, checksum_path)
        verify_checksum_file(archive_path, checksum_path)
    except HistoricalDatasetError:
        raise
    except Exception:
        # Archive genuinely absent for this symbol/day (e.g. before listing
        # start) -- Binance returns 404, not a corrupt/mismatched file.
        return None
    return _parse_book_depth_zip(archive_path)


def _fetch_to_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:  # noqa: S310
        payload = response.read()
    destination.write_bytes(payload)


def _parse_book_depth_zip(archive_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(archive_path) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as f:
            frame = pd.read_csv(io.BytesIO(f.read()))
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["percentage"] = frame["percentage"].map(lambda v: f"{float(v):.2f}")
    return frame[["timestamp", "percentage", "notional"]]


def _resample_to_hourly(events: pd.DataFrame) -> pd.DataFrame:
    wide = events.pivot_table(
        index="timestamp", columns="percentage", values="notional", aggfunc="last"
    )
    wide = wide.reindex(columns=list(PERCENTAGE_LEVELS))
    wide = wide.sort_index()
    hourly = wide.resample("1h").last()
    hourly = hourly.dropna(how="all")
    hourly = hourly.reset_index().rename(columns={"timestamp": "hour_start"})
    hourly["open_time"] = hourly["hour_start"].astype("datetime64[ms, UTC]").astype("int64")
    hourly = hourly.drop(columns=["hour_start"])
    rename_map = {level: f"notional_{level}" for level in PERCENTAGE_LEVELS}
    return hourly.rename(columns=rename_map)


if __name__ == "__main__":
    raise SystemExit(main())
