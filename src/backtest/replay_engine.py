"""Causal replay driver for the Sprint 9 executable backtest.

Reuses the exact same causal signal generation already reviewed in Sprint 8
(``generate_pair_signal_intents``) and the same walk-forward test-window
filter, then feeds each signal through the Sprint 9 execution simulator
against real, checksum-verified tick-level bookTicker quotes that were
already downloaded for the Sprint 7/8 cost-gate work. No new data is
downloaded here.

Memory safety: a Sprint 8 attempt to load a full month of bookTicker data at
once caused an out-of-memory kill. This module never holds more than a small,
bounded number of decompressed daily files in memory at once (see
``_BoundedDayCache``).
"""

from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.research.execution_cost_evidence import normalize_book_ticker_frame
from src.research.historical_dataset import read_zip_csv, verify_checksum_file
from src.research.sprint8 import (
    Sprint8UniverseContract,
    WalkForwardFold,
    generate_pair_signal_intents,
    pair_symbols,
)

from .execution_simulator import (
    DEFAULT_EXECUTION_STYLE,
    ExecutionStyle,
    RoundTripTradeResult,
    simulate_round_trip_trade,
)
from .fill_model import FillModelConfig, TopOfBookQuote

DEFAULT_HOLDING_PERIOD_MS = 60 * 60 * 1000
DEFAULT_DAY_CACHE_SIZE = 8
_DAY_MS = 24 * 60 * 60 * 1000


class ReplayEngineError(ValueError):
    """Raised when replay inputs are missing or invalid."""


@dataclass(frozen=True, slots=True)
class ReplayConfig:
    """Configuration for one Sprint 9 replay run."""

    raw_root: Path
    holding_period_ms: int = DEFAULT_HOLDING_PERIOD_MS
    fill_config: FillModelConfig = field(default_factory=FillModelConfig)
    day_cache_size: int = DEFAULT_DAY_CACHE_SIZE
    execution_style: ExecutionStyle = DEFAULT_EXECUTION_STYLE

    def __post_init__(self) -> None:
        if self.holding_period_ms <= 0:
            raise ReplayEngineError("holding_period_ms must be positive")
        if self.day_cache_size <= 0:
            raise ReplayEngineError("day_cache_size must be positive")


class _BoundedDayCache:
    """FIFO-evicting cache bounding how many decompressed days stay resident.

    A single day of real bookTicker data can hold millions of tick rows.
    Holding more than a handful of days across multiple symbols at once
    risks the same class of out-of-memory failure Sprint 8 hit with a
    whole-month load. This cache trades a bit of re-reading for a hard,
    predictable memory ceiling.
    """

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ReplayEngineError("cache maxsize must be positive")
        self._maxsize = maxsize
        self._entries: OrderedDict[tuple[str, str], tuple[TopOfBookQuote, ...]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._entries)

    def get_or_load(
        self,
        key: tuple[str, str],
        loader: Callable[[], tuple[TopOfBookQuote, ...]],
    ) -> tuple[TopOfBookQuote, ...]:
        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key]
        value = loader()
        self._entries[key] = value
        self._entries.move_to_end(key)
        while len(self._entries) > self._maxsize:
            self._entries.popitem(last=False)
        return value


def load_symbol_day_quotes(
    symbol: str,
    day: str,
    raw_root: Path,
) -> tuple[TopOfBookQuote, ...]:
    """Load one symbol-day of checksum-verified real bookTicker quotes.

    Fails closed if the expected archive or its checksum sidecar is missing,
    or if the archive's SHA256 no longer matches the checksum recorded at
    download time -- a stale sidecar or on-disk corruption between the
    Sprint 8 download and this replay must never be silently trusted.
    """

    relative = f"data/futures/um/daily/bookTicker/{symbol}/{symbol}-bookTicker-{day}.zip"
    archive_path = raw_root / relative
    checksum_path = raw_root / f"{relative}.CHECKSUM"
    if not archive_path.exists():
        raise ReplayEngineError(f"missing raw bookTicker archive: {archive_path}")
    if not checksum_path.exists():
        raise ReplayEngineError(f"missing checksum sidecar: {checksum_path}")
    verification = verify_checksum_file(archive_path, checksum_path)

    raw = read_zip_csv(archive_path)
    normalized = normalize_book_ticker_frame(
        raw,
        symbol,
        source_path=str(archive_path),
        source_checksum=verification.actual_sha256,
        dataset_version="sprint9_replay",
    )
    quotes = [
        TopOfBookQuote(
            event_time=int(row.event_time),
            best_bid=float(row.best_bid),
            best_ask=float(row.best_ask),
            best_bid_qty=_finite_or_zero(row.bid_qty),
            best_ask_qty=_finite_or_zero(row.ask_qty),
        )
        for row in normalized.itertuples(index=False)
    ]
    quotes.sort(key=lambda quote: quote.event_time)
    return tuple(quotes)


def replay_pair(
    pair: str,
    bars: pd.DataFrame,
    contract: Sprint8UniverseContract,
    folds: tuple[WalkForwardFold, ...],
    config: ReplayConfig,
) -> tuple[RoundTripTradeResult, ...]:
    """Replay one pair's walk-forward signals with realistic fill simulation."""

    intents = generate_pair_signal_intents(bars, pair, contract=contract)
    walk_forward_intents = [
        intent for intent in intents if _is_in_test_window(intent.created_at, folds)
    ]
    if not walk_forward_intents:
        return ()

    symbol_a, symbol_b = pair_symbols(pair)
    cache = _BoundedDayCache(config.day_cache_size)
    results = []
    for intent in walk_forward_intents:
        window_end = (
            intent.created_at
            + config.holding_period_ms
            + config.fill_config.reconciliation_latency_ms
        )
        days = _days_spanning(intent.created_at, window_end)
        quotes_a = _load_days(cache, symbol_a, days, config.raw_root)
        quotes_b = _load_days(cache, symbol_b, days, config.raw_root)
        results.append(
            simulate_round_trip_trade(
                intent,
                quotes_a=quotes_a,
                quotes_b=quotes_b,
                holding_period_ms=config.holding_period_ms,
                config=config.fill_config,
                execution_style=config.execution_style,
            )
        )
    return tuple(results)


def _load_days(
    cache: _BoundedDayCache,
    symbol: str,
    days: tuple[str, ...],
    raw_root: Path,
) -> tuple[TopOfBookQuote, ...]:
    combined: list[TopOfBookQuote] = []
    for day in days:
        combined.extend(
            cache.get_or_load(
                (symbol, day),
                lambda symbol=symbol, day=day: load_symbol_day_quotes(symbol, day, raw_root),
            )
        )
    combined.sort(key=lambda quote: quote.event_time)
    return tuple(combined)


def _days_spanning(start_ms: int, end_ms: int) -> tuple[str, ...]:
    start_day = date(1970, 1, 1) + timedelta(milliseconds=start_ms)
    end_day = date(1970, 1, 1) + timedelta(milliseconds=end_ms)
    days = []
    current = start_day
    while current <= end_day:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return tuple(days)


def _is_in_test_window(created_at: int, folds: tuple[WalkForwardFold, ...]) -> bool:
    return any(fold.test_start_time <= created_at <= fold.test_end_time for fold in folds)


def _finite_or_zero(value: float) -> float:
    numeric = float(value)
    return numeric if math.isfinite(numeric) else 0.0


__all__ = [
    "ReplayConfig",
    "ReplayEngineError",
    "load_symbol_day_quotes",
    "replay_pair",
]
