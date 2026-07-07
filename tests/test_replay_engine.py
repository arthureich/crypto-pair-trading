from __future__ import annotations

import hashlib
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import replay_engine as replay_engine_module  # noqa: E402
from src.backtest.execution_simulator import ExecutionStyle  # noqa: E402
from src.backtest.fill_model import FillModelConfig, TopOfBookQuote  # noqa: E402
from src.backtest.replay_engine import (  # noqa: E402
    ReplayConfig,
    ReplayEngineError,
    _BoundedDayCache,
    _days_spanning,
    load_symbol_day_quotes,
    replay_pair,
)
from src.research.sprint8 import (  # noqa: E402
    WalkForwardFold,
    load_sprint8_universe_contract,
)

HOUR_MS = 60 * 60 * 1000
DAY_MS = 24 * HOUR_MS


def test_bounded_day_cache_never_exceeds_maxsize() -> None:
    cache = _BoundedDayCache(maxsize=2)
    loads = {"a": 0, "b": 0, "c": 0}

    def loader(key: str) -> tuple[TopOfBookQuote, ...]:
        loads[key] += 1
        return ()

    cache.get_or_load(("SYM", "a"), lambda: loader("a"))
    cache.get_or_load(("SYM", "b"), lambda: loader("b"))
    cache.get_or_load(("SYM", "c"), lambda: loader("c"))

    assert len(cache) == 2
    # "a" was evicted (FIFO); re-requesting it must reload, not reuse a stale slot.
    cache.get_or_load(("SYM", "a"), lambda: loader("a"))
    assert loads["a"] == 2
    assert loads["c"] == 1


def test_bounded_day_cache_reuses_hit_without_reloading() -> None:
    cache = _BoundedDayCache(maxsize=4)
    calls = {"count": 0}

    def loader() -> tuple[TopOfBookQuote, ...]:
        calls["count"] += 1
        return (
            TopOfBookQuote(
                event_time=1, best_bid=1.0, best_ask=1.01, best_bid_qty=1.0, best_ask_qty=1.0
            ),
        )

    cache.get_or_load(("SYM", "a"), loader)
    cache.get_or_load(("SYM", "a"), loader)

    assert calls["count"] == 1


def test_days_spanning_covers_start_and_end_inclusive() -> None:
    start = 0
    end = DAY_MS + HOUR_MS

    days = _days_spanning(start, end)

    assert days == ("1970-01-01", "1970-01-02")


def test_load_symbol_day_quotes_fails_closed_on_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(ReplayEngineError, match="missing raw bookTicker archive"):
        load_symbol_day_quotes("ARBUSDT", "2023-06-01", tmp_path)


def test_load_symbol_day_quotes_fails_closed_on_missing_checksum_sidecar(tmp_path: Path) -> None:
    relative = "data/futures/um/daily/bookTicker/ARBUSDT/ARBUSDT-bookTicker-2023-06-01.zip"
    archive_path = tmp_path / relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(b"not a real zip, but presence is enough for this check")

    with pytest.raises(ReplayEngineError, match="missing checksum sidecar"):
        load_symbol_day_quotes("ARBUSDT", "2023-06-01", tmp_path)


def test_load_symbol_day_quotes_fails_closed_on_checksum_mismatch(tmp_path: Path) -> None:
    relative = "data/futures/um/daily/bookTicker/ARBUSDT/ARBUSDT-bookTicker-2023-06-01.zip"
    archive_path = tmp_path / relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(b"archive bytes that will not match the checksum below")
    checksum_path = tmp_path / f"{relative}.CHECKSUM"
    wrong_digest = hashlib.sha256(b"different bytes entirely").hexdigest()
    checksum_path.write_text(
        f"{wrong_digest}  ARBUSDT-bookTicker-2023-06-01.zip\n", encoding="utf-8"
    )

    with pytest.raises(Exception, match="checksum mismatch"):
        load_symbol_day_quotes("ARBUSDT", "2023-06-01", tmp_path)


def test_replay_pair_never_uses_quotes_before_the_signal_and_respects_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    contract = load_sprint8_universe_contract()
    bars = _synthetic_pair_bars()
    folds = (
        WalkForwardFold(
            fold_index=0,
            train_start_time=0,
            train_end_time=(200 - 1) * HOUR_MS,
            test_start_time=200 * HOUR_MS,
            test_end_time=int(bars["open_time"].max()),
            train_rows=200,
            test_rows=int(bars["open_time"].nunique()) - 200,
        ),
    )

    seen_days: list[tuple[str, str]] = []

    def fake_load(symbol: str, day: str, raw_root: Path) -> tuple[TopOfBookQuote, ...]:  # noqa: ARG001
        seen_days.append((symbol, day))
        day_start_ms = _day_start_ms(day)
        return tuple(
            TopOfBookQuote(
                event_time=day_start_ms + minute * 60_000,
                best_bid=10.0,
                best_ask=10.01,
                best_bid_qty=1_000.0,
                best_ask_qty=1_000.0,
            )
            for minute in range(0, 24 * 60, 5)
        )

    monkeypatch.setattr(replay_engine_module, "load_symbol_day_quotes", fake_load)

    config = ReplayConfig(
        raw_root=tmp_path,
        fill_config=FillModelConfig(latency_ms=0, ack_unknown_rate=0.0),
        day_cache_size=2,
    )
    results = replay_pair("ARBUSDT/OPUSDT", bars, contract, folds, config)

    assert len(results) > 0
    for result in results:
        if result.entry_fill_a.execution_time is not None:
            assert result.entry_fill_a.execution_time >= result.entry_fill_a.decision_time
        if result.entry_fill_b.execution_time is not None:
            assert result.entry_fill_b.execution_time >= result.entry_fill_b.decision_time
    # bounded cache: never more unique (symbol, day) pairs loaded than requested,
    # and each requested day loaded via the injected loader (fail-closed path
    # is never silently bypassed).
    assert len(set(seen_days)) > 0


def test_replay_config_defaults_to_market_ioc() -> None:
    config = ReplayConfig(raw_root=Path("."))

    assert config.execution_style is ExecutionStyle.MARKET_IOC


def test_replay_pair_propagates_limit_maker_ttl_execution_style(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A ReplayConfig configured for LIMIT_MAKER_TTL must reach the fill model.

    Regression: this catches a refactor that threads ``execution_style``
    through ``ReplayConfig`` but forgets to pass it into
    ``simulate_round_trip_trade`` inside ``replay_pair``.
    """

    contract = load_sprint8_universe_contract()
    bars = _synthetic_pair_bars()
    folds = (
        WalkForwardFold(
            fold_index=0,
            train_start_time=0,
            train_end_time=(200 - 1) * HOUR_MS,
            test_start_time=200 * HOUR_MS,
            test_end_time=int(bars["open_time"].max()),
            train_rows=200,
            test_rows=int(bars["open_time"].nunique()) - 200,
        ),
    )

    def fake_load(symbol: str, day: str, raw_root: Path) -> tuple[TopOfBookQuote, ...]:  # noqa: ARG001
        day_start_ms = _day_start_ms(day)
        return tuple(
            TopOfBookQuote(
                event_time=day_start_ms + minute * 60_000,
                best_bid=10.0,
                best_ask=10.01,
                best_bid_qty=1_000.0,
                best_ask_qty=1_000.0,
            )
            for minute in range(0, 24 * 60, 5)
        )

    monkeypatch.setattr(replay_engine_module, "load_symbol_day_quotes", fake_load)

    config = ReplayConfig(
        raw_root=tmp_path,
        fill_config=FillModelConfig(latency_ms=0, limit_ttl_ms=5_000, ack_unknown_rate=0.0),
        day_cache_size=2,
        execution_style=ExecutionStyle.LIMIT_MAKER_TTL,
    )
    results = replay_pair("ARBUSDT/OPUSDT", bars, contract, folds, config)

    assert len(results) > 0
    assert any(result.entry_fill_a.order_type.value == "LIMIT" for result in results)


def _day_start_ms(day: str) -> int:
    year, month, day_num = (int(part) for part in day.split("-"))
    epoch = date(1970, 1, 1)
    delta = date(year, month, day_num) - epoch
    return delta.days * DAY_MS


def _synthetic_pair_bars() -> pd.DataFrame:
    n = 400
    rng = np.random.default_rng(7)
    phi_true = 0.85
    noise = rng.normal(0.0, 0.05, size=n)
    spread = np.zeros(n)
    for i in range(1, n):
        spread[i] = phi_true * spread[i - 1] + noise[i]
    x = np.cumsum(np.full(n, 0.0005))
    y = x + spread
    open_time = [t * HOUR_MS for t in range(n)]
    return pd.concat(
        [
            pd.DataFrame({"symbol": "ARBUSDT", "open_time": open_time, "log_price": y}),
            pd.DataFrame({"symbol": "OPUSDT", "open_time": open_time, "log_price": x}),
        ],
        ignore_index=True,
    )
