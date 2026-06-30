from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (
    CorrelationMode,
    ExecutionCostQuality,
    PairRejectReason,
    PairSelectionConfig,
    SymbolRejectReason,
    pair_selection,
    rolling_correlation_no_lookahead,
    select_pairs,
)

BASE_RETURNS = (
    0.011,
    -0.004,
    0.008,
    0.006,
    -0.007,
    0.005,
    0.003,
    -0.006,
    0.007,
    0.004,
    -0.003,
)


def _config(**overrides: object) -> PairSelectionConfig:
    values = {
        "expected_bars": 12,
        "min_history_bars": 12,
        "min_history_coverage": 1.0,
        "max_longest_gap_hours": 0.0,
        "min_funding_coverage": 1.0,
        "min_reference_price_coverage": 1.0,
        "min_median_quote_volume": 100.0,
        "min_p10_quote_volume": 100.0,
        "min_nonzero_quote_volume_coverage": 1.0,
        "min_median_trades": 1.0,
        "max_median_abs_funding_bps": 3.0,
        "max_p95_abs_funding_bps": 15.0,
        "funding_events_per_day": 3.0,
        "max_median_spread_bps": 3.0,
        "max_p95_spread_bps": 8.0,
        "max_p99_spread_bps": 15.0,
        "min_pair_joint_coverage": 1.0,
        "max_pair_median_spread_bps": 6.0,
        "max_pair_p95_spread_bps": 10.0,
        "max_pair_funding_carry_bps_per_day": 10.0,
        "min_correlation": 0.75,
        "correlation_window": 4,
        "min_correlation_observations": 4,
    }
    values.update(overrides)
    return PairSelectionConfig(**values)


def _rows(
    symbol: str,
    log_returns: tuple[float, ...] = BASE_RETURNS,
    *,
    quote_volume: float = 1_000.0,
    trades: int = 10,
    funding_rate: float = 0.0001,
    execution_cost_quality: str = ExecutionCostQuality.UNAVAILABLE.value,
    median_spread_bps: float = 1.0,
    p95_spread_bps: float = 2.0,
    p99_spread_bps: float = 3.0,
    drop_indexes: set[int] | None = None,
) -> list[dict[str, object]]:
    prices = [100.0]
    for log_return in log_returns:
        prices.append(prices[-1] * math.exp(log_return))
    dropped = drop_indexes or set()
    rows = []
    for index, price in enumerate(prices):
        if index in dropped:
            continue
        rows.append(
            {
                "symbol": symbol,
                "open_time": index * 3_600_000,
                "price_for_research": price,
                "is_complete_bar": True,
                "quote_volume": quote_volume,
                "number_of_trades": trades,
                "funding_rate_asof": funding_rate,
                "execution_cost_quality": execution_cost_quality,
                "median_spread_bps_1h": median_spread_bps,
                "p95_spread_bps_1h": p95_spread_bps,
                "p99_spread_bps_1h": p99_spread_bps,
            }
        )
    return rows


def test_asset_without_enough_data_is_rejected_and_excluded_from_pairs() -> None:
    data = pd.DataFrame(
        _rows("BTCUSDT") + _rows("ETHUSDT") + _rows("THINUSDT", drop_indexes=set(range(5, 12)))
    )

    result = select_pairs(data, _config())

    rejected = {selection.symbol: selection for selection in result.rejected_symbols}
    assert "THINUSDT" in rejected
    assert SymbolRejectReason.INSUFFICIENT_HISTORY in rejected["THINUSDT"].reasons
    assert result.accepted_symbol_names == ("BTCUSDT", "ETHUSDT")
    assert all("THINUSDT" not in pair.pair_id for pair in result.candidate_pairs)


def test_pair_with_low_rolling_correlation_is_rejected() -> None:
    low_correlation = tuple(reversed(BASE_RETURNS))
    data = pd.DataFrame(_rows("BTCUSDT") + _rows("ETHUSDT", low_correlation))

    result = select_pairs(data, _config(min_correlation=0.90))

    assert result.candidate_pairs == ()
    assert len(result.rejected_pairs) == 1
    assert result.rejected_pairs[0].pair_id == "BTCUSDT/ETHUSDT"
    assert PairRejectReason.LOW_CORRELATION in result.rejected_pairs[0].reasons


def test_candidate_pairs_are_ranked_by_deterministic_score() -> None:
    noisy_returns = tuple(
        base + noise
        for base, noise in zip(
            BASE_RETURNS,
            (0.001, -0.002, 0.002, -0.001, 0.003, -0.003, 0.001, 0.002, -0.002, 0.001, -0.001),
            strict=True,
        )
    )
    data = pd.DataFrame(
        _rows("BTCUSDT") + _rows("ETHUSDT", BASE_RETURNS) + _rows("SOLUSDT", noisy_returns)
    )

    result = select_pairs(data, _config(min_correlation=0.20))

    ranked_ids = tuple(pair.pair_id for pair in result.candidate_pairs)
    assert ranked_ids[0] == "BTCUSDT/ETHUSDT"
    assert tuple(pair.score for pair in result.candidate_pairs) == tuple(
        sorted((pair.score for pair in result.candidate_pairs), reverse=True)
    )


def test_symbol_rejection_preserves_multiple_liquidity_and_funding_reasons() -> None:
    data = pd.DataFrame(
        _rows("BTCUSDT")
        + _rows(
            "WEAKUSDT",
            quote_volume=0.0,
            trades=0,
            funding_rate=0.0004,
        )
    )

    result = select_pairs(data, _config())

    weak = next(
        selection for selection in result.rejected_symbols if selection.symbol == "WEAKUSDT"
    )
    assert SymbolRejectReason.LOW_MEDIAN_VOLUME in weak.reasons
    assert SymbolRejectReason.LOW_TAIL_VOLUME in weak.reasons
    assert SymbolRejectReason.VOLUME_GAPS in weak.reasons
    assert SymbolRejectReason.LOW_TRADE_COUNT in weak.reasons
    assert SymbolRejectReason.HIGH_MEDIAN_FUNDING in weak.reasons


def test_spread_filters_apply_only_when_execution_cost_quality_is_verified() -> None:
    data = pd.DataFrame(
        _rows(
            "VERIFIEDUSDT",
            execution_cost_quality=ExecutionCostQuality.VERIFIED.value,
            median_spread_bps=4.0,
        )
        + _rows(
            "UNAVAILABLEUSDT",
            execution_cost_quality=ExecutionCostQuality.UNAVAILABLE.value,
            median_spread_bps=100.0,
        )
    )

    result = select_pairs(data, _config())

    rejected = {selection.symbol: selection for selection in result.rejected_symbols}
    assert SymbolRejectReason.WIDE_MEDIAN_SPREAD in rejected["VERIFIEDUSDT"].reasons
    assert result.accepted_symbol_names == ("UNAVAILABLEUSDT",)


def test_incomplete_execution_cost_quality_does_not_apply_verified_spread_filters() -> None:
    rows = _rows(
        "PATCHYUSDT",
        execution_cost_quality=ExecutionCostQuality.VERIFIED.value,
        median_spread_bps=100.0,
    )
    rows[0]["execution_cost_quality"] = None

    result = select_pairs(pd.DataFrame(rows), _config())

    assert result.accepted_symbol_names == ("PATCHYUSDT",)
    metrics = result.accepted_symbols[0].metrics
    assert metrics.execution_cost_quality == ExecutionCostQuality.INCOMPLETE.value
    assert metrics.cost_filters_applied is False


def test_verified_execution_cost_requires_tail_spread_columns_or_raw_spread() -> None:
    rows = _rows(
        "TAILLESSUSDT",
        execution_cost_quality=ExecutionCostQuality.VERIFIED.value,
        median_spread_bps=1.0,
    )
    for row in rows:
        row.pop("p95_spread_bps_1h")
        row.pop("p99_spread_bps_1h")

    result = select_pairs(pd.DataFrame(rows), _config())

    rejected = result.rejected_symbols[0]
    assert rejected.symbol == "TAILLESSUSDT"
    assert SymbolRejectReason.WIDE_P95_SPREAD in rejected.reasons
    assert SymbolRejectReason.WIDE_P99_SPREAD in rejected.reasons


def test_pair_level_verified_spread_and_funding_filters_are_preserved() -> None:
    data = pd.DataFrame(
        _rows(
            "BTCUSDT",
            funding_rate=0.0002,
            execution_cost_quality=ExecutionCostQuality.VERIFIED.value,
            median_spread_bps=2.0,
            p95_spread_bps=6.0,
        )
        + _rows(
            "ETHUSDT",
            funding_rate=0.0002,
            execution_cost_quality=ExecutionCostQuality.VERIFIED.value,
            median_spread_bps=2.0,
            p95_spread_bps=6.0,
        )
    )

    result = select_pairs(
        data,
        _config(max_pair_median_spread_bps=3.0, max_pair_p95_spread_bps=10.0),
    )

    assert result.candidate_pairs == ()
    rejected = result.rejected_pairs[0]
    assert PairRejectReason.PAIR_WIDE_MEDIAN_SPREAD in rejected.reasons
    assert PairRejectReason.PAIR_WIDE_TAIL_SPREAD in rejected.reasons
    assert PairRejectReason.PAIR_HIGH_FUNDING_CARRY in rejected.reasons


def test_full_sample_mode_is_marked_exploratory() -> None:
    data = pd.DataFrame(_rows("BTCUSDT") + _rows("ETHUSDT"))

    result = select_pairs(
        data,
        _config(
            correlation_mode=CorrelationMode.FULL_SAMPLE_EXPLORATORY,
            min_correlation_observations=4,
        ),
    )

    assert len(result.candidate_pairs) == 1
    assert result.candidate_pairs[0].metrics.exploratory is True
    assert result.candidate_pairs[0].metrics.correlation_mode == "FULL_SAMPLE_EXPLORATORY"


def test_reference_price_coverage_allows_negative_premium_sidecar() -> None:
    data = pd.DataFrame(_rows("BTCUSDT") + _rows("ETHUSDT"))
    data["mark_close"] = data["price_for_research"]
    data["index_close"] = data["price_for_research"]
    data["premium_close"] = -0.0002

    result = select_pairs(data, _config(require_reference_price_columns=True))

    assert result.rejected_symbols == ()
    assert len(result.candidate_pairs) == 1


def test_rolling_correlation_helper_excludes_the_current_row() -> None:
    left = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])
    right = pd.Series([1.0, 2.0, 3.0, 4.0, -100.0])

    correlation = rolling_correlation_no_lookahead(left, right, window=3, min_periods=3)

    assert np.isnan(correlation.iloc[2])
    assert correlation.iloc[3] == pytest.approx(1.0)
    assert correlation.iloc[4] == pytest.approx(1.0)


def test_pair_selection_module_has_no_global_dataframe_state() -> None:
    global_dataframes = [
        name
        for name, value in pair_selection.__dict__.items()
        if not name.startswith("__") and isinstance(value, pd.DataFrame)
    ]

    assert global_dataframes == []
