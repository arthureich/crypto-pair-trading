"""Initial research pair selection from normalized in-memory bars."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

HOUR_MS = 60 * 60 * 1000
DEFAULT_EXPECTED_1H_BARS = 26_304
MIN_TIMES_FOR_GAP_CHECK = 2


class ExecutionCostQuality(StrEnum):
    """Execution-cost evidence quality for conditional spread filters."""

    VERIFIED = "VERIFIED"
    UNAVAILABLE = "UNAVAILABLE"
    INCOMPLETE = "INCOMPLETE"


class CorrelationMode(StrEnum):
    """Correlation mode and look-ahead contract."""

    ROLLING_NO_LOOKAHEAD = "ROLLING_NO_LOOKAHEAD"
    FULL_SAMPLE_EXPLORATORY = "FULL_SAMPLE_EXPLORATORY"


class SymbolRejectReason(StrEnum):
    """Stable symbol-level rejection reasons."""

    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    HISTORY_GAPS = "HISTORY_GAPS"
    LONG_HISTORY_GAP = "LONG_HISTORY_GAP"
    FUNDING_GAPS = "FUNDING_GAPS"
    REFERENCE_PRICE_GAPS = "REFERENCE_PRICE_GAPS"
    LOW_MEDIAN_VOLUME = "LOW_MEDIAN_VOLUME"
    LOW_TAIL_VOLUME = "LOW_TAIL_VOLUME"
    VOLUME_GAPS = "VOLUME_GAPS"
    LOW_TRADE_COUNT = "LOW_TRADE_COUNT"
    HIGH_MEDIAN_FUNDING = "HIGH_MEDIAN_FUNDING"
    HIGH_TAIL_FUNDING = "HIGH_TAIL_FUNDING"
    WIDE_MEDIAN_SPREAD = "WIDE_MEDIAN_SPREAD"
    WIDE_P95_SPREAD = "WIDE_P95_SPREAD"
    WIDE_P99_SPREAD = "WIDE_P99_SPREAD"


class PairRejectReason(StrEnum):
    """Stable pair-level rejection reasons."""

    PAIR_HISTORY_GAPS = "PAIR_HISTORY_GAPS"
    PAIR_WIDE_MEDIAN_SPREAD = "PAIR_WIDE_MEDIAN_SPREAD"
    PAIR_WIDE_TAIL_SPREAD = "PAIR_WIDE_TAIL_SPREAD"
    PAIR_HIGH_FUNDING_CARRY = "PAIR_HIGH_FUNDING_CARRY"
    LOW_CORRELATION = "LOW_CORRELATION"
    INSUFFICIENT_PAIR_OBSERVATIONS = "INSUFFICIENT_PAIR_OBSERVATIONS"


@dataclass(frozen=True, slots=True)
class PairSelectionConfig:
    """Thresholds and column names for pure in-memory pair selection."""

    expected_bars: int = DEFAULT_EXPECTED_1H_BARS
    bar_interval_ms: int = HOUR_MS
    min_history_bars: int = 26_000
    min_history_coverage: float = 0.99
    max_longest_gap_hours: float = 6.0
    min_funding_coverage: float = 0.99
    min_reference_price_coverage: float = 0.99
    require_reference_price_columns: bool = False
    min_median_quote_volume: float = 1_000_000.0
    min_p10_quote_volume: float = 100_000.0
    min_nonzero_quote_volume_coverage: float = 0.99
    min_median_trades: float = 100.0
    max_median_abs_funding_bps: float = 3.0
    max_p95_abs_funding_bps: float = 15.0
    funding_events_per_day: float = 3.0
    max_median_spread_bps: float = 3.0
    max_p95_spread_bps: float = 8.0
    max_p99_spread_bps: float = 15.0
    min_pair_joint_coverage: float = 0.99
    max_pair_median_spread_bps: float = 6.0
    max_pair_p95_spread_bps: float = 10.0
    max_pair_funding_carry_bps_per_day: float = 10.0
    min_correlation: float = 0.75
    correlation_window: int = 168
    min_correlation_observations: int = 168
    correlation_mode: CorrelationMode | str = CorrelationMode.ROLLING_NO_LOOKAHEAD
    symbol_column: str = "symbol"
    time_column: str = "open_time"
    complete_bar_column: str = "is_complete_bar"
    price_column: str = "price_for_research"
    log_price_column: str = "log_price"
    quote_volume_column: str = "quote_volume"
    trade_count_column: str = "number_of_trades"
    funding_rate_column: str = "funding_rate_asof"
    execution_cost_quality_column: str = "execution_cost_quality"
    median_spread_column: str = "median_spread_bps_1h"
    p95_spread_column: str = "p95_spread_bps_1h"
    p99_spread_column: str = "p99_spread_bps_1h"
    reference_price_columns: tuple[str, ...] = ("mark_close", "index_close", "premium_close")

    def __post_init__(self) -> None:
        _positive_int("expected_bars", self.expected_bars)
        _positive_int("bar_interval_ms", self.bar_interval_ms)
        _positive_int("min_history_bars", self.min_history_bars)
        _positive_int("correlation_window", self.correlation_window)
        _positive_int("min_correlation_observations", self.min_correlation_observations)
        _non_negative_float("max_longest_gap_hours", self.max_longest_gap_hours)
        _positive_float("funding_events_per_day", self.funding_events_per_day)
        CorrelationMode(self.correlation_mode)


@dataclass(frozen=True, slots=True)
class SymbolMetrics:
    """Measured symbol-level filter inputs."""

    valid_bars: int
    history_coverage: float
    longest_missing_gap_hours: float
    funding_coverage: float
    reference_price_coverage: float
    median_quote_volume: float
    p10_quote_volume: float
    nonzero_quote_volume_coverage: float
    median_trades: float
    median_abs_funding_bps: float
    p95_abs_funding_bps: float
    funding_bps_per_day: float
    execution_cost_quality: str
    cost_filters_applied: bool
    median_spread_bps: float
    p95_spread_bps: float
    p99_spread_bps: float


@dataclass(frozen=True, slots=True)
class SymbolSelection:
    """Accepted or rejected symbol with preserved reasons."""

    symbol: str
    accepted: bool
    reasons: tuple[SymbolRejectReason, ...]
    metrics: SymbolMetrics


@dataclass(frozen=True, slots=True)
class PairMetrics:
    """Measured pair-level filter and ranking inputs."""

    joint_valid_bars: int
    joint_coverage: float
    funding_carry_bps_per_day: float
    combined_median_spread_bps: float | None
    combined_p95_spread_bps: float | None
    cost_filters_applied: bool
    correlation: float
    correlation_observations: int
    correlation_mode: str
    exploratory: bool
    score: float


@dataclass(frozen=True, slots=True)
class CandidatePair:
    """Accepted pair candidate ranked by deterministic score."""

    symbol_a: str
    symbol_b: str
    score: float
    metrics: PairMetrics

    @property
    def pair_id(self) -> str:
        return f"{self.symbol_a}/{self.symbol_b}"


@dataclass(frozen=True, slots=True)
class RejectedPair:
    """Rejected pair with all accumulated pair-level reasons."""

    symbol_a: str
    symbol_b: str
    reasons: tuple[PairRejectReason, ...]
    metrics: PairMetrics

    @property
    def pair_id(self) -> str:
        return f"{self.symbol_a}/{self.symbol_b}"


@dataclass(frozen=True, slots=True)
class PairSelectionResult:
    """Complete pair selection report for one in-memory universe."""

    accepted_symbols: tuple[SymbolSelection, ...]
    rejected_symbols: tuple[SymbolSelection, ...]
    candidate_pairs: tuple[CandidatePair, ...]
    rejected_pairs: tuple[RejectedPair, ...]

    @property
    def accepted_symbol_names(self) -> tuple[str, ...]:
        return tuple(symbol.symbol for symbol in self.accepted_symbols)

    @property
    def rejected_symbol_names(self) -> tuple[str, ...]:
        return tuple(symbol.symbol for symbol in self.rejected_symbols)


def select_pairs(
    normalized_bars: pd.DataFrame | Iterable[Mapping[str, Any]],
    config: PairSelectionConfig | None = None,
) -> PairSelectionResult:
    """Select and rank candidate pairs from already-normalized in-memory bars."""

    cfg = config or PairSelectionConfig()
    prepared = _prepare_bars(normalized_bars, cfg)
    symbol_selections = tuple(
        _evaluate_symbol(symbol, group, cfg)
        for symbol, group in prepared.groupby("__symbol", sort=True)
    )
    accepted_symbols = tuple(selection for selection in symbol_selections if selection.accepted)
    rejected_symbols = tuple(selection for selection in symbol_selections if not selection.accepted)
    symbol_by_name = {selection.symbol: selection for selection in accepted_symbols}

    candidates: list[CandidatePair] = []
    rejected_pairs: list[RejectedPair] = []
    for symbol_a, symbol_b in combinations(sorted(symbol_by_name), 2):
        pair_result = _evaluate_pair(symbol_a, symbol_b, prepared, symbol_by_name, cfg)
        if isinstance(pair_result, CandidatePair):
            candidates.append(pair_result)
        else:
            rejected_pairs.append(pair_result)

    ranked_candidates = tuple(
        sorted(candidates, key=lambda pair: (-pair.score, pair.symbol_a, pair.symbol_b))
    )
    ranked_rejections = tuple(
        sorted(rejected_pairs, key=lambda pair: (pair.symbol_a, pair.symbol_b))
    )
    return PairSelectionResult(
        accepted_symbols=accepted_symbols,
        rejected_symbols=rejected_symbols,
        candidate_pairs=ranked_candidates,
        rejected_pairs=ranked_rejections,
    )


def select_candidate_pairs(
    normalized_bars: pd.DataFrame | Iterable[Mapping[str, Any]],
    config: PairSelectionConfig | None = None,
) -> PairSelectionResult:
    """Alias kept explicit for notebook/report call sites."""

    return select_pairs(normalized_bars, config)


def rolling_correlation_no_lookahead(
    left_returns: pd.Series | Iterable[float],
    right_returns: pd.Series | Iterable[float],
    *,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    """Return rolling correlation shifted one bar so row ``t`` excludes row ``t``."""

    lookback = _positive_int("window", window)
    required_periods = (
        lookback if min_periods is None else _positive_int("min_periods", min_periods)
    )
    left = pd.Series(left_returns, dtype="float64")
    right = pd.Series(right_returns, dtype="float64")
    return left.rolling(window=lookback, min_periods=required_periods).corr(right).shift(1)


def _evaluate_symbol(
    symbol: str,
    group: pd.DataFrame,
    config: PairSelectionConfig,
) -> SymbolSelection:
    valid = group.loc[group["__valid_bar"]].copy()
    valid_bars = int(len(valid))
    quote_volume = _numeric_series(valid, config.quote_volume_column)
    trades = _numeric_series(valid, config.trade_count_column)
    funding = _numeric_series(valid, config.funding_rate_column)
    abs_funding_bps = funding.abs() * 10_000.0
    median_abs_funding_bps = _finite_median(abs_funding_bps)
    funding_bps_per_day = _funding_bps_per_day(median_abs_funding_bps, config)
    cost_quality = _symbol_cost_quality(valid, config)
    median_spread, p95_spread, p99_spread = _symbol_spread_metrics(valid, config)

    metrics = SymbolMetrics(
        valid_bars=valid_bars,
        history_coverage=_ratio(valid_bars, config.expected_bars),
        longest_missing_gap_hours=_longest_missing_gap_hours(valid["__open_time"], config),
        funding_coverage=_finite_coverage(funding, valid_bars),
        reference_price_coverage=_reference_price_coverage(valid, config),
        median_quote_volume=_finite_median(quote_volume),
        p10_quote_volume=_finite_quantile(quote_volume, 0.10),
        nonzero_quote_volume_coverage=_nonzero_coverage(quote_volume, valid_bars),
        median_trades=_finite_median(trades),
        median_abs_funding_bps=median_abs_funding_bps,
        p95_abs_funding_bps=_finite_quantile(abs_funding_bps, 0.95),
        funding_bps_per_day=funding_bps_per_day,
        execution_cost_quality=cost_quality,
        cost_filters_applied=cost_quality == ExecutionCostQuality.VERIFIED.value,
        median_spread_bps=median_spread,
        p95_spread_bps=p95_spread,
        p99_spread_bps=p99_spread,
    )
    reasons = _symbol_reject_reasons(metrics, config)
    return SymbolSelection(
        symbol=symbol,
        accepted=not reasons,
        reasons=tuple(reasons),
        metrics=metrics,
    )


def _symbol_reject_reasons(
    metrics: SymbolMetrics,
    config: PairSelectionConfig,
) -> list[SymbolRejectReason]:
    reasons: list[SymbolRejectReason] = []
    _append_if(
        metrics.valid_bars < config.min_history_bars,
        reasons,
        SymbolRejectReason.INSUFFICIENT_HISTORY,
    )
    _append_if(
        metrics.history_coverage < config.min_history_coverage,
        reasons,
        SymbolRejectReason.HISTORY_GAPS,
    )
    _append_if(
        metrics.longest_missing_gap_hours > config.max_longest_gap_hours,
        reasons,
        SymbolRejectReason.LONG_HISTORY_GAP,
    )
    _append_if(
        metrics.funding_coverage < config.min_funding_coverage,
        reasons,
        SymbolRejectReason.FUNDING_GAPS,
    )
    _append_if(
        metrics.reference_price_coverage < config.min_reference_price_coverage,
        reasons,
        SymbolRejectReason.REFERENCE_PRICE_GAPS,
    )
    _append_if(
        _below(metrics.median_quote_volume, config.min_median_quote_volume),
        reasons,
        SymbolRejectReason.LOW_MEDIAN_VOLUME,
    )
    _append_if(
        _below(metrics.p10_quote_volume, config.min_p10_quote_volume),
        reasons,
        SymbolRejectReason.LOW_TAIL_VOLUME,
    )
    _append_if(
        metrics.nonzero_quote_volume_coverage < config.min_nonzero_quote_volume_coverage,
        reasons,
        SymbolRejectReason.VOLUME_GAPS,
    )
    _append_if(
        _below(metrics.median_trades, config.min_median_trades),
        reasons,
        SymbolRejectReason.LOW_TRADE_COUNT,
    )
    _append_if(
        _above(metrics.median_abs_funding_bps, config.max_median_abs_funding_bps),
        reasons,
        SymbolRejectReason.HIGH_MEDIAN_FUNDING,
    )
    _append_if(
        _above(metrics.p95_abs_funding_bps, config.max_p95_abs_funding_bps),
        reasons,
        SymbolRejectReason.HIGH_TAIL_FUNDING,
    )
    if metrics.cost_filters_applied:
        _append_if(
            _above_or_missing(metrics.median_spread_bps, config.max_median_spread_bps),
            reasons,
            SymbolRejectReason.WIDE_MEDIAN_SPREAD,
        )
        _append_if(
            _above_or_missing(metrics.p95_spread_bps, config.max_p95_spread_bps),
            reasons,
            SymbolRejectReason.WIDE_P95_SPREAD,
        )
        _append_if(
            _above_or_missing(metrics.p99_spread_bps, config.max_p99_spread_bps),
            reasons,
            SymbolRejectReason.WIDE_P99_SPREAD,
        )
    return reasons


def _evaluate_pair(
    symbol_a: str,
    symbol_b: str,
    prepared: pd.DataFrame,
    accepted_symbols: dict[str, SymbolSelection],
    config: PairSelectionConfig,
) -> CandidatePair | RejectedPair:
    metrics_a = accepted_symbols[symbol_a].metrics
    metrics_b = accepted_symbols[symbol_b].metrics
    joint_bars = _joint_valid_bars(symbol_a, symbol_b, prepared)
    pair_cost_verified = metrics_a.cost_filters_applied and metrics_b.cost_filters_applied
    combined_median_spread = _combined_spread(
        metrics_a.median_spread_bps, metrics_b.median_spread_bps
    )
    combined_p95_spread = _combined_spread(metrics_a.p95_spread_bps, metrics_b.p95_spread_bps)
    funding_carry = metrics_a.funding_bps_per_day + metrics_b.funding_bps_per_day
    correlation, observations, correlation_reason = _pair_correlation(
        symbol_a,
        symbol_b,
        prepared,
        config,
    )
    score = _pair_score(correlation)
    metrics = PairMetrics(
        joint_valid_bars=joint_bars,
        joint_coverage=_ratio(joint_bars, config.expected_bars),
        funding_carry_bps_per_day=funding_carry,
        combined_median_spread_bps=combined_median_spread if pair_cost_verified else None,
        combined_p95_spread_bps=combined_p95_spread if pair_cost_verified else None,
        cost_filters_applied=pair_cost_verified,
        correlation=correlation,
        correlation_observations=observations,
        correlation_mode=CorrelationMode(config.correlation_mode).value,
        exploratory=CorrelationMode(config.correlation_mode)
        is CorrelationMode.FULL_SAMPLE_EXPLORATORY,
        score=score,
    )
    reasons = _pair_reject_reasons(
        metrics,
        correlation_reason=correlation_reason,
        config=config,
    )
    if reasons:
        return RejectedPair(symbol_a, symbol_b, tuple(reasons), metrics)
    return CandidatePair(symbol_a, symbol_b, score, metrics)


def _pair_reject_reasons(
    metrics: PairMetrics,
    *,
    correlation_reason: PairRejectReason | None,
    config: PairSelectionConfig,
) -> list[PairRejectReason]:
    reasons: list[PairRejectReason] = []
    _append_if(
        metrics.joint_coverage < config.min_pair_joint_coverage,
        reasons,
        PairRejectReason.PAIR_HISTORY_GAPS,
    )
    if metrics.cost_filters_applied:
        _append_if(
            _above_or_missing(
                metrics.combined_median_spread_bps, config.max_pair_median_spread_bps
            ),
            reasons,
            PairRejectReason.PAIR_WIDE_MEDIAN_SPREAD,
        )
        _append_if(
            _above_or_missing(metrics.combined_p95_spread_bps, config.max_pair_p95_spread_bps),
            reasons,
            PairRejectReason.PAIR_WIDE_TAIL_SPREAD,
        )
    _append_if(
        metrics.funding_carry_bps_per_day > config.max_pair_funding_carry_bps_per_day,
        reasons,
        PairRejectReason.PAIR_HIGH_FUNDING_CARRY,
    )
    if correlation_reason is not None:
        reasons.append(correlation_reason)
    else:
        _append_if(
            _below(metrics.correlation, config.min_correlation),
            reasons,
            PairRejectReason.LOW_CORRELATION,
        )
    return reasons


def _pair_correlation(
    symbol_a: str,
    symbol_b: str,
    prepared: pd.DataFrame,
    config: PairSelectionConfig,
) -> tuple[float, int, PairRejectReason | None]:
    returns = _joint_returns(symbol_a, symbol_b, prepared)
    if CorrelationMode(config.correlation_mode) is CorrelationMode.FULL_SAMPLE_EXPLORATORY:
        if len(returns) < config.min_correlation_observations:
            return math.nan, int(len(returns)), PairRejectReason.INSUFFICIENT_PAIR_OBSERVATIONS
        correlation = float(returns["return_a"].corr(returns["return_b"]))
        if not math.isfinite(correlation):
            return math.nan, int(len(returns)), PairRejectReason.INSUFFICIENT_PAIR_OBSERVATIONS
        return correlation, int(len(returns)), None

    rolling = rolling_correlation_no_lookahead(
        returns["return_a"],
        returns["return_b"],
        window=config.correlation_window,
        min_periods=config.min_correlation_observations,
    )
    valid = _finite_values(rolling)
    if len(valid) == 0:
        return math.nan, 0, PairRejectReason.INSUFFICIENT_PAIR_OBSERVATIONS
    return float(valid.mean()), int(len(valid)), None


def _prepare_bars(
    normalized_bars: pd.DataFrame | Iterable[Mapping[str, Any]],
    config: PairSelectionConfig,
) -> pd.DataFrame:
    data = (
        normalized_bars.copy(deep=True)
        if isinstance(normalized_bars, pd.DataFrame)
        else pd.DataFrame(normalized_bars)
    )
    _require_column(data, config.symbol_column)
    _require_column(data, config.time_column)
    log_price = _log_price_series(data, config)
    prepared = pd.DataFrame(
        {
            "__symbol": data[config.symbol_column].astype("string").str.strip(),
            "__open_time": pd.to_numeric(data[config.time_column], errors="coerce"),
            "__complete": _complete_bar_series(data, config),
            "__log_price": log_price,
        },
        index=data.index,
    )
    prepared = pd.concat([prepared, data], axis=1)
    prepared = prepared.dropna(subset=["__symbol", "__open_time"])
    prepared = prepared.loc[prepared["__symbol"] != ""].copy()
    prepared["__open_time"] = prepared["__open_time"].astype("int64")
    prepared["__valid_bar"] = prepared["__complete"] & np.isfinite(prepared["__log_price"])
    prepared = prepared.sort_values(["__symbol", "__open_time"], kind="mergesort").reset_index(
        drop=True
    )
    prepared["__return_1h"] = prepared.groupby("__symbol", sort=False)["__log_price"].diff()
    time_diff = prepared.groupby("__symbol", sort=False)["__open_time"].diff()
    previous_valid = prepared.groupby("__symbol", sort=False)["__valid_bar"].shift(1).fillna(False)
    consecutive = time_diff == config.bar_interval_ms
    return_is_valid = prepared["__valid_bar"] & previous_valid.astype(bool) & consecutive
    prepared.loc[~return_is_valid, "__return_1h"] = np.nan
    return prepared


def _log_price_series(data: pd.DataFrame, config: PairSelectionConfig) -> pd.Series:
    if config.price_column in data.columns:
        price = pd.to_numeric(data[config.price_column], errors="coerce")
        return _log_from_positive_price(price)
    if config.log_price_column in data.columns:
        return pd.to_numeric(data[config.log_price_column], errors="coerce")
    if "mark_close" in data.columns:
        return _log_from_positive_price(pd.to_numeric(data["mark_close"], errors="coerce"))
    if "close" in data.columns:
        return _log_from_positive_price(pd.to_numeric(data["close"], errors="coerce"))
    raise ValueError(
        "normalized bars must include price_for_research, log_price, mark_close, or close"
    )


def _complete_bar_series(data: pd.DataFrame, config: PairSelectionConfig) -> pd.Series:
    if config.complete_bar_column not in data.columns:
        return pd.Series(True, index=data.index, dtype="bool")
    return data[config.complete_bar_column].fillna(False).astype("bool")


def _log_from_positive_price(price: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=price.index, dtype="float64")
    finite_positive = np.isfinite(price) & (price > 0)
    result.loc[finite_positive] = np.log(price.loc[finite_positive])
    return result


def _joint_valid_bars(symbol_a: str, symbol_b: str, prepared: pd.DataFrame) -> int:
    left = _symbol_valid_rows(symbol_a, prepared)[["__open_time"]]
    right = _symbol_valid_rows(symbol_b, prepared)[["__open_time"]]
    return int(len(left.merge(right, on="__open_time", how="inner", sort=True)))


def _joint_returns(symbol_a: str, symbol_b: str, prepared: pd.DataFrame) -> pd.DataFrame:
    left = _symbol_valid_rows(symbol_a, prepared)[["__open_time", "__return_1h"]].rename(
        columns={"__return_1h": "return_a"}
    )
    right = _symbol_valid_rows(symbol_b, prepared)[["__open_time", "__return_1h"]].rename(
        columns={"__return_1h": "return_b"}
    )
    joint = left.merge(right, on="__open_time", how="inner", sort=True)
    return joint.dropna(subset=["return_a", "return_b"]).reset_index(drop=True)


def _symbol_valid_rows(symbol: str, prepared: pd.DataFrame) -> pd.DataFrame:
    return prepared.loc[(prepared["__symbol"] == symbol) & prepared["__valid_bar"]].copy()


def _symbol_cost_quality(valid: pd.DataFrame, config: PairSelectionConfig) -> str:
    if config.execution_cost_quality_column not in valid.columns or valid.empty:
        return ExecutionCostQuality.UNAVAILABLE.value
    raw_values = valid[config.execution_cost_quality_column]
    if raw_values.isna().any():
        return ExecutionCostQuality.INCOMPLETE.value
    values = {_normalize_execution_cost_quality(value) for value in raw_values}
    if not values:
        return ExecutionCostQuality.UNAVAILABLE.value
    if values == {ExecutionCostQuality.VERIFIED.value}:
        return ExecutionCostQuality.VERIFIED.value
    if values == {ExecutionCostQuality.UNAVAILABLE.value}:
        return ExecutionCostQuality.UNAVAILABLE.value
    return ExecutionCostQuality.INCOMPLETE.value


def _normalize_execution_cost_quality(value: Any) -> str:
    text = str(getattr(value, "value", value)).strip().upper()
    if text in {quality.value for quality in ExecutionCostQuality}:
        return text
    return ExecutionCostQuality.INCOMPLETE.value


def _symbol_spread_metrics(
    valid: pd.DataFrame,
    config: PairSelectionConfig,
) -> tuple[float, float, float]:
    median_column = _first_existing_column(valid, (config.median_spread_column, "spread_bps"))
    p95_column = _first_existing_column(valid, (config.p95_spread_column, "spread_bps"))
    p99_column = _first_existing_column(valid, (config.p99_spread_column, "spread_bps"))
    median = _finite_median(_numeric_series(valid, median_column))
    p95 = _finite_quantile(_numeric_series(valid, p95_column), 0.95)
    p99 = _finite_quantile(_numeric_series(valid, p99_column), 0.99)
    return median, p95, p99


def _first_existing_column(valid: pd.DataFrame, candidates: tuple[str | None, ...]) -> str:
    for column in candidates:
        if column is not None and column in valid.columns:
            return column
    return "__missing_column"


def _reference_price_coverage(valid: pd.DataFrame, config: PairSelectionConfig) -> float:
    if valid.empty:
        return 0.0
    if config.require_reference_price_columns:
        columns = config.reference_price_columns
    else:
        columns = tuple(
            column for column in config.reference_price_columns if column in valid.columns
        )
    if not columns:
        return 1.0
    coverages = []
    for column in columns:
        if column not in valid.columns:
            coverages.append(0.0)
            continue
        values = _numeric_series(valid, column)
        coverages.append(float(_valid_reference_values(values, column).sum()) / float(len(valid)))
    return min(coverages)


def _longest_missing_gap_hours(times: pd.Series, config: PairSelectionConfig) -> float:
    unique_times = np.sort(pd.to_numeric(times, errors="coerce").dropna().unique())
    if len(unique_times) < MIN_TIMES_FOR_GAP_CHECK:
        return 0.0
    diffs = np.diff(unique_times)
    missing_steps = np.maximum(np.rint(diffs / config.bar_interval_ms).astype(int) - 1, 0)
    if len(missing_steps) == 0:
        return 0.0
    return float(missing_steps.max())


def _valid_reference_values(values: pd.Series, column: str) -> pd.Series:
    finite = np.isfinite(values)
    if column.startswith("premium_"):
        return finite
    return finite & (values > 0)


def _funding_bps_per_day(median_abs_funding_bps: float, config: PairSelectionConfig) -> float:
    if not math.isfinite(median_abs_funding_bps):
        return math.nan
    return median_abs_funding_bps * config.funding_events_per_day


def _combined_spread(left: float, right: float) -> float:
    if not math.isfinite(left) or not math.isfinite(right):
        return math.nan
    return left + right


def _pair_score(correlation: float) -> float:
    if not math.isfinite(correlation):
        return math.nan
    return round(float(correlation), 12)


def _numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(np.nan, index=data.index, dtype="float64")
    return pd.to_numeric(data[column], errors="coerce")


def _finite_values(values: pd.Series) -> pd.Series:
    finite = pd.to_numeric(values, errors="coerce")
    return finite.loc[np.isfinite(finite)]


def _finite_median(values: pd.Series) -> float:
    finite = _finite_values(values)
    if finite.empty:
        return math.nan
    return float(finite.median())


def _finite_quantile(values: pd.Series, quantile: float) -> float:
    finite = _finite_values(values)
    if finite.empty:
        return math.nan
    return float(finite.quantile(quantile))


def _finite_coverage(values: pd.Series, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    finite = _finite_values(values)
    return float(len(finite)) / float(denominator)


def _nonzero_coverage(values: pd.Series, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    finite = _finite_values(values)
    return float((finite > 0).sum()) / float(denominator)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _append_if(condition: bool, reasons: list[Any], reason: Any) -> None:
    if condition:
        reasons.append(reason)


def _below(value: float, threshold: float) -> bool:
    return not math.isfinite(value) or value < threshold


def _above(value: float, threshold: float) -> bool:
    return math.isfinite(value) and value > threshold


def _above_or_missing(value: float | None, threshold: float) -> bool:
    return value is None or not math.isfinite(value) or value > threshold


def _require_column(data: pd.DataFrame, column: str) -> None:
    if column not in data.columns:
        raise ValueError(f"normalized bars must include {column!r}")


def _positive_int(field_name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _positive_float(field_name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field_name} must be numeric")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return float(value)


def _non_negative_float(field_name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field_name} must be numeric")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return float(value)


__all__ = [
    "CandidatePair",
    "CorrelationMode",
    "ExecutionCostQuality",
    "PairMetrics",
    "PairRejectReason",
    "PairSelectionConfig",
    "PairSelectionResult",
    "RejectedPair",
    "SymbolMetrics",
    "SymbolRejectReason",
    "SymbolSelection",
    "rolling_correlation_no_lookahead",
    "select_candidate_pairs",
    "select_pairs",
]
