#!/usr/bin/env python3
"""TASK-ALT-011: pull Deribit DVOL (30d IV index) for BTC & ETH -- free, keyless.

Deribit's public `get_volatility_index_data` returns daily DVOL OHLC (no auth).
Pre-registered in `docs/pre_registers/TASK-ALT-011.md` (ADR-0032). Writes a tidy
daily [asset, day, dvol_close] panel; the diagnostic derives the VRP features
from it plus realized vol from the existing bars.

Pure parse (`tidy_dvol`) is unit-tested against a fixture; only `_get_json`
touches the network (no network mock, same precedent as the other downloaders).
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

API = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
CURRENCIES = ("BTC", "ETH")
START = "2023-06-01"
END = "2026-05-31"
RESOLUTION = 86400  # 1 day, seconds
_MS_PER_DAY = 86_400_000
_CHUNK_DAYS = 300  # stay well under any per-call row cap
_MAX_RETRIES = 4
_TIMEOUT_S = 30
OUTPUT = (
    PROJECT_ROOT / "data/research/binance_public/normalized/sprint_alt_dvol_202306_202605.csv.gz"
)


def main() -> int:
    start_ms = int(pd.Timestamp(START, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(END, tz="UTC").timestamp() * 1000)
    frames = []
    for ccy in CURRENCIES:
        rows = _fetch_currency(ccy, start_ms, end_ms)
        tidy = tidy_dvol(rows, ccy)
        print(f"{ccy}: {len(tidy)} daily DVOL rows", file=sys.stderr)
        frames.append(tidy)
    panel = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["asset", "day"])
        .sort_values(["asset", "day"], kind="mergesort")
        .reset_index(drop=True)
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUTPUT, index=False, compression="gzip")
    print(f"Wrote {OUTPUT}: {len(panel)} (asset,day) rows", file=sys.stderr)
    return 0


def _fetch_currency(ccy: str, start_ms: int, end_ms: int) -> list[list]:
    collected: list[list] = []
    cursor = start_ms
    chunk = _CHUNK_DAYS * _MS_PER_DAY
    while cursor <= end_ms:
        hi = min(cursor + chunk, end_ms)
        url = (
            f"{API}?currency={ccy}&start_timestamp={cursor}"
            f"&end_timestamp={hi}&resolution={RESOLUTION}"
        )
        payload = _get_json(url)
        collected.extend(payload.get("result", {}).get("data", []))
        cursor = hi + _MS_PER_DAY
        time.sleep(0.3)
    return collected


def _get_json(url: str) -> dict:
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as response:
                return json.load(response)
        except urllib.error.HTTPError:
            raise  # real 4xx/5xx are not transient (ALT-007 lesson)
        except (urllib.error.URLError, TimeoutError) as err:
            last_err = err
            time.sleep(2**attempt)
    raise RuntimeError(f"failed to fetch after {_MAX_RETRIES} retries: {last_err}")


def tidy_dvol(rows: list[list], asset: str) -> pd.DataFrame:
    """Deribit DVOL OHLC rows ([ts_ms, o, h, l, c]) -> [asset, day, dvol_close]."""

    if not rows:
        return pd.DataFrame(columns=["asset", "day", "dvol_close"])
    frame = pd.DataFrame(rows, columns=["ts_ms", "open", "high", "low", "close"])
    frame["day"] = pd.to_datetime(frame["ts_ms"], unit="ms", utc=True).dt.floor("D")
    frame["asset"] = asset.lower()  # base_asset convention (btc, eth)
    frame["dvol_close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["dvol_close"])
    return frame[["asset", "day", "dvol_close"]].reset_index(drop=True)


if __name__ == "__main__":
    raise SystemExit(main())
