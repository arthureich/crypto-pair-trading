from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (  # noqa: E402
    ExecutionCostGateConfig,
    ExecutionCostQuality,
    aggregate_book_ticker_hourly,
    evaluate_execution_cost_gate,
    join_cost_to_bars_no_lookahead,
    normalize_book_ticker_frame,
)
from src.research.execution_cost_evidence import HOUR_MS  # noqa: E402


def test_book_ticker_normalization_and_hourly_schema() -> None:
    raw = pd.DataFrame(
        [
            [
                "update_id",
                "best_bid_price",
                "best_bid_qty",
                "best_ask_price",
                "best_ask_qty",
                "transaction_time",
                "event_time",
            ],
            [1, "99.9", "4.0", "100.1", "2.0", 1000, 1000],
            [2, "99.9", "4.0", "100.1", "2.0", 2000, 2000],
            [3, "0", "4.0", "100.2", "2.0", 3000, 3000],
            [4, "100.3", "4.0", "100.2", "2.0", 4000, 4000],
        ]
    )

    samples = normalize_book_ticker_frame(
        raw,
        "btcusdt",
        source_path="data/futures/um/monthly/bookTicker/BTCUSDT/BTCUSDT-bookTicker-2023-06.zip",
        source_checksum="a" * 64,
        dataset_version="unit-cost",
        normalized_at="2026-07-01T00:00:00+00:00",
    )
    hourly = aggregate_book_ticker_hourly(
        samples,
        stale_gap_threshold_ms=10_000,
        normalized_at="2026-07-01T00:00:00+00:00",
    )

    assert list(samples["event_time"]) == [1000, 2000]
    assert samples["execution_cost_quality"].unique().tolist() == [
        ExecutionCostQuality.VERIFIED.value
    ]
    assert len(hourly) == 1
    assert hourly.loc[0, "symbol"] == "BTCUSDT"
    assert hourly.loc[0, "spread_sample_count_1h"] == 2
    assert hourly.loc[0, "median_spread_bps_1h"] == pytest.approx(20.0)
    assert hourly.loc[0, "p95_spread_bps_1h"] == pytest.approx(20.0)
    assert hourly.loc[0, "p99_spread_bps_1h"] == pytest.approx(20.0)
    assert hourly.loc[0, "cost_available_time"] == HOUR_MS


def test_cost_gate_fails_closed_when_cost_is_absent() -> None:
    bars = pd.DataFrame(_bars("BTCUSDT") + _bars("ETHUSDT"))

    gate = evaluate_execution_cost_gate(
        bars,
        ("BTCUSDT/ETHUSDT",),
        hourly_cost=None,
        config=ExecutionCostGateConfig(expected_bars=3, max_stale_hours=10),
    )

    assert gate["cost_gated_pass"] is False
    assert gate["pairs_passed"] == 0
    assert gate["pairs_failed"] == 1
    assert gate["pair_cost_results"][0]["reasons"] == [
        "LEG_COST_EVIDENCE_INCOMPLETE",
        "PAIR_WIDE_MEDIAN_SPREAD",
        "PAIR_WIDE_TAIL_SPREAD",
    ]
    assert all(
        stat["reasons"] == ["HISTORICAL_COST_EVIDENCE_UNAVAILABLE"]
        for stat in gate["symbol_cost_stats"]
    )


def test_cost_gate_fails_closed_when_cost_coverage_is_incomplete() -> None:
    bars = pd.DataFrame(_bars("BTCUSDT", count=4) + _bars("ETHUSDT", count=4))
    hourly = pd.DataFrame(
        [
            _hour("BTCUSDT", 0),
            _hour("BTCUSDT", HOUR_MS),
            _hour("ETHUSDT", 0),
            _hour("ETHUSDT", HOUR_MS),
        ]
    )

    gate = evaluate_execution_cost_gate(
        bars,
        ("BTCUSDT/ETHUSDT",),
        hourly,
        config=ExecutionCostGateConfig(
            expected_bars=4,
            min_hourly_coverage=1.0,
            max_longest_gap_hours=1.0,
            max_stale_hours=10,
        ),
    )

    assert gate["cost_gated_pass"] is False
    assert gate["pair_cost_results"][0]["reasons"] == ["LEG_COST_EVIDENCE_INCOMPLETE"]
    assert all(
        "HISTORICAL_COST_COVERAGE_INCOMPLETE" in stat["reasons"]
        for stat in gate["symbol_cost_stats"]
    )


def test_cost_join_uses_only_cost_available_before_bar_decision_time() -> None:
    bars = pd.DataFrame(_bars("BTCUSDT", count=3))
    hourly = pd.DataFrame([_hour("BTCUSDT", 0), _hour("BTCUSDT", HOUR_MS, median=2.0)])

    joined = join_cost_to_bars_no_lookahead(bars, hourly)

    assert math.isnan(joined.loc[0, "cost_open_time"])
    assert joined.loc[0, "cost_execution_cost_quality"] == ExecutionCostQuality.UNAVAILABLE.value
    assert joined.loc[1, "cost_open_time"] == 0
    assert joined.loc[1, "cost_median_spread_bps_1h"] == 1.0
    assert joined.loc[2, "cost_open_time"] == HOUR_MS
    assert joined.loc[2, "cost_median_spread_bps_1h"] == 2.0


def _bars(symbol: str, *, count: int = 3) -> list[dict[str, object]]:
    return [
        {
            "symbol": symbol,
            "open_time": index * HOUR_MS,
            "is_complete_bar": True,
            "log_price": 1.0 + index / 100.0,
        }
        for index in range(count)
    ]


def _hour(symbol: str, open_time: int, *, median: float = 1.0) -> dict[str, object]:
    return {
        "venue": "BINANCE",
        "market_type": "USD_M_FUTURES",
        "contract_type": "PERPETUAL",
        "symbol": symbol,
        "interval": "1h",
        "open_time": open_time,
        "close_time": open_time + HOUR_MS - 1,
        "cost_available_time": open_time + HOUR_MS,
        "spread_sample_count_1h": 10,
        "median_spread_bps_1h": median,
        "p95_spread_bps_1h": median + 1.0,
        "p99_spread_bps_1h": median + 2.0,
        "min_spread_bps_1h": median,
        "max_spread_bps_1h": median + 2.0,
        "first_event_time": open_time,
        "last_event_time": open_time + 1000,
        "max_sample_gap_ms": 1000,
        "stale_gap_count_1h": 0,
        "source_path": "source.zip",
        "source_checksum": "a" * 64,
        "dataset_version": "unit-cost",
        "execution_cost_quality": ExecutionCostQuality.VERIFIED.value,
        "normalized_at": "2026-07-01T00:00:00+00:00",
    }
