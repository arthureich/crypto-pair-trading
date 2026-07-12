"""Tests for the pure helpers in the cross-venue funding scripts (TASK-ALT-010).

Network is not mocked (only `_get_json` touches it, same accepted precedent as
the other downloaders). Covers `select_markets` / `tidy_funding` (downloader)
and `cross_venue_stats` (diagnostic) against small fixtures shaped like real
Coinalyze `future-markets` / `funding-rate-history` payloads.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dl = _load("download_alt_xvenue_funding", "download_alt_xvenue_funding.py")
diag = _load("diagnostic_alt_xvenue_funding", "diagnostic_alt_xvenue_funding.py")


def _markets() -> list[dict]:
    return [
        {"symbol": "BTCUSDT_PERP.A", "exchange": "A", "base_asset": "BTC",
         "quote_asset": "USDT", "is_perpetual": True},
        {"symbol": "BTCUSDT.6", "exchange": "6", "base_asset": "BTC",
         "quote_asset": "USDT", "is_perpetual": True},
        {"symbol": "BTCUSD_PERP.A", "exchange": "A", "base_asset": "BTC",
         "quote_asset": "USD", "is_perpetual": True},  # not USDT -> excluded
        {"symbol": "BTC-FUT.A", "exchange": "A", "base_asset": "BTC",
         "quote_asset": "USDT", "is_perpetual": False},  # not perpetual -> excluded
        {"symbol": "XRPUSDT.K", "exchange": "K", "base_asset": "XRP",
         "quote_asset": "USDT", "is_perpetual": True},  # Kraken not in venue set
    ]  # fmt: skip


def test_select_markets_keeps_only_usdt_perps_on_chosen_venues() -> None:
    kept = dl.select_markets(_markets(), venue_codes={"A", "6"}, assets={"BTC", "XRP"})
    syms = {m["symbol"] for m in kept}
    assert syms == {"BTCUSDT_PERP.A", "BTCUSDT.6"}  # USD, non-perp, Kraken all dropped


def test_tidy_funding_maps_venue_and_parses_points() -> None:
    symbol_meta = {
        "BTCUSDT_PERP.A": {"base_asset": "BTC", "exchange": "A"},
        "BTCUSDT.6": {"base_asset": "BTC", "exchange": "6"},
    }
    venues = {"A": "Binance", "6": "Bybit"}
    rows = [
        {"symbol": "BTCUSDT_PERP.A", "history": [
            {"t": 1685577600, "c": 0.01}, {"t": 1685664000, "c": 0.012}]},
        {"symbol": "BTCUSDT.6", "history": [{"t": 1685577600, "c": 0.03}]},
        {"symbol": "UNKNOWN.9", "history": [{"t": 1685577600, "c": 0.9}]},  # no meta -> skip
    ]  # fmt: skip
    tidy = dl.tidy_funding(rows, symbol_meta, venues)
    assert set(tidy["venue"]) == {"Binance", "Bybit"}
    assert len(tidy) == 3  # 2 Binance points + 1 Bybit; unknown symbol dropped
    assert tidy["day"].dt.tz is not None
    binance = tidy[(tidy["venue"] == "Binance")].sort_values("day")
    assert list(binance["funding"]) == [0.01, 0.012]


def test_cross_venue_stats_requires_min_venues_and_computes_range() -> None:
    day = pd.Timestamp("2024-01-01", tz="UTC")
    other = pd.Timestamp("2024-01-02", tz="UTC")
    funding = pd.DataFrame(
        {
            "asset": ["btc", "btc", "btc", "btc", "btc"],
            "day": [day, day, day, other, other],
            "venue": ["Binance", "Bybit", "OKX", "Binance", "Bybit"],
            "funding": [0.01, 0.02, 0.06, 0.05, 0.05],
        }
    )
    stats = diag.cross_venue_stats(funding, min_venues=3)
    # Only the first day has >= 3 venues; the second (2 venues) is dropped.
    assert len(stats) == 1
    row = stats.iloc[0]
    assert row["day"] == day
    assert row["range"] == 0.06 - 0.01  # max - min
    assert row["mean"] == (0.01 + 0.02 + 0.06) / 3


def test_cross_venue_stats_empty_when_never_enough_venues() -> None:
    funding = pd.DataFrame(
        {
            "asset": ["eth", "eth"],
            "day": [pd.Timestamp("2024-01-01", tz="UTC")] * 2,
            "venue": ["Binance", "Bybit"],
            "funding": [0.01, 0.02],
        }
    )
    assert diag.cross_venue_stats(funding, min_venues=3).empty
