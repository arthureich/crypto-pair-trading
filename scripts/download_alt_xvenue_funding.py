#!/usr/bin/env python3
"""TASK-ALT-010: pull cross-venue perpetual funding from the Coinalyze free tier.

Pre-registered in `docs/pre_registers/TASK-ALT-010.md` (ADR-0030). For each of
our 20 base assets, collects daily funding across the major USDT-perp venues
{Binance, Bybit, OKX, Huobi, BitMEX} and writes a tidy [asset, day, venue,
funding] panel. The diagnostic (`diagnostic_alt_xvenue_funding.py`) derives the
cross-venue dispersion / range / mean from it.

The API key comes from `COINALYZE_API_KEY` (in the gitignored `.env`); it is
never logged or committed. The pure parse/normalize functions (`tidy_funding`,
`select_markets`) are unit-tested against fixtures; only `_get_json` touches the
network (no network mock, same accepted precedent as the other downloaders).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

API_ROOT = "https://api.coinalyze.net/v1"
START = "2023-06-01"
END = "2026-05-31"
OUTPUT = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint_alt_xvenue_funding_202306_202605.csv.gz"
)
# Coinalyze exchange code -> venue name (the frozen major-venue set).
VENUES: dict[str, str] = {"A": "Binance", "6": "Bybit", "3": "OKX", "4": "Huobi", "0": "BitMEX"}
BASE_ASSETS = (
    "ADA", "APT", "ARB", "ATOM", "AVAX", "BCH", "BNB", "BTC", "DOGE", "DOT",
    "ETC", "ETH", "LINK", "LTC", "OP", "SOL", "SUI", "TRX", "UNI", "XRP",
)  # fmt: skip
_SYMBOLS_PER_CALL = 20
_MAX_RETRIES = 6
_TIMEOUT_S = 30
_RATE_SLEEP_S = 2.0  # free-tier courtesy pause between calls
_HTTP_TOO_MANY = 429
_RATE_LIMIT_BACKOFF_S = 15  # base wait when the free tier returns 429


def main() -> int:
    key = _load_key()
    markets = select_markets(_get_json("/future-markets", key), set(VENUES), set(BASE_ASSETS))
    if not markets:
        print("No matching markets returned; aborting.", file=sys.stderr)
        return 1
    print(f"{len(markets)} (asset,venue) perp markets across {len(VENUES)} venues", file=sys.stderr)

    symbol_meta = {m["symbol"]: m for m in markets}
    frm = int(pd.Timestamp(START, tz="UTC").timestamp())
    to = int(pd.Timestamp(END, tz="UTC").timestamp())

    frames: list[pd.DataFrame] = []
    symbols = list(symbol_meta)
    for i in range(0, len(symbols), _SYMBOLS_PER_CALL):
        batch = symbols[i : i + _SYMBOLS_PER_CALL]
        path = f"/funding-rate-history?symbols={','.join(batch)}&interval=daily&from={frm}&to={to}"
        rows = _get_json(path, key)
        frames.append(tidy_funding(rows, symbol_meta, VENUES))
        time.sleep(_RATE_SLEEP_S)

    panel = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    panel = panel.sort_values(["asset", "day", "venue"], kind="mergesort").reset_index(drop=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUTPUT, index=False, compression="gzip")
    print(
        f"Wrote {OUTPUT}: {len(panel)} (asset,day,venue) rows, "
        f"{panel['asset'].nunique()} assets",
        file=sys.stderr,
    )
    return 0


def _load_key() -> str:
    key = os.environ.get("COINALYZE_API_KEY")
    if not key:
        env = PROJECT_ROOT / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("COINALYZE_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        raise RuntimeError("COINALYZE_API_KEY not set (env or .env)")
    return key


def select_markets(markets: list[dict], venue_codes: set[str], assets: set[str]) -> list[dict]:
    """Filter future-markets to USDT perpetuals on the frozen venues/assets (pure)."""

    out = []
    for m in markets:
        if (
            m.get("is_perpetual")
            and m.get("quote_asset") == "USDT"
            and m.get("base_asset") in assets
            and m.get("exchange") in venue_codes
        ):
            out.append(m)
    return out


def tidy_funding(
    rows: list[dict], symbol_meta: dict[str, dict], venues: dict[str, str]
) -> pd.DataFrame:
    """Coinalyze funding-rate-history -> tidy [asset, day, venue, funding] (pure)."""

    records: list[dict] = []
    for entry in rows:
        meta = symbol_meta.get(entry.get("symbol"))
        if meta is None:
            continue
        asset = meta["base_asset"].lower()
        venue = venues[meta["exchange"]]
        for point in entry.get("history", []):
            records.append(
                {
                    "asset": asset,
                    "day": pd.to_datetime(point["t"], unit="s", utc=True).floor("D"),
                    "venue": venue,
                    "funding": point.get("c"),
                }
            )
    frame = pd.DataFrame.from_records(records, columns=["asset", "day", "venue", "funding"])
    frame["funding"] = pd.to_numeric(frame["funding"], errors="coerce")
    return frame.dropna(subset=["funding"]).reset_index(drop=True)


def _get_json(path: str, key: str) -> list | dict:
    sep = "&" if "?" in path else "?"
    url = f"{API_ROOT}{path}{sep}api_key={key}"
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as response:
                return json.load(response)
        except urllib.error.HTTPError as err:
            if err.code == _HTTP_TOO_MANY:  # transient rate limit -> back off and retry
                retry_after = err.headers.get("Retry-After")
                wait = (
                    int(retry_after)
                    if retry_after and retry_after.isdigit()
                    else (_RATE_LIMIT_BACKOFF_S * (attempt + 1))
                )
                last_err = err
                time.sleep(wait)
                continue
            raise  # other 4xx/5xx are real; do not silently swallow (ALT-007 lesson)
        except (urllib.error.URLError, TimeoutError) as err:
            last_err = err
            time.sleep(2**attempt)
    raise RuntimeError(f"failed to fetch after {_MAX_RETRIES} retries: {last_err}")


if __name__ == "__main__":
    raise SystemExit(main())
