"""Historical execution-cost evidence helpers for Sprint 7 research gates."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from xml.etree import ElementTree

import numpy as np
import pandas as pd

from .historical_dataset import BINANCE_PUBLIC_DATA_BASE_URL, month_range
from .pair_selection import DEFAULT_EXPECTED_1H_BARS, ExecutionCostQuality

HOUR_MS = 60 * 60 * 1000
DECEMBER = 12
DEFAULT_STALE_GAP_MS = 60_000
BOOK_TICKER_COLUMNS = (
    "update_id",
    "best_bid_price",
    "best_bid_qty",
    "best_ask_price",
    "best_ask_qty",
    "transaction_time",
    "event_time",
)
RAW_COST_SAMPLE_COLUMNS = (
    "venue",
    "market_type",
    "contract_type",
    "symbol",
    "event_time",
    "transaction_time",
    "update_id",
    "best_bid",
    "best_ask",
    "bid_qty",
    "ask_qty",
    "mid_price",
    "spread_bps",
    "source_path",
    "source_checksum",
    "dataset_version",
    "execution_cost_quality",
    "normalized_at",
)
HOURLY_COST_COLUMNS = (
    "venue",
    "market_type",
    "contract_type",
    "symbol",
    "interval",
    "open_time",
    "close_time",
    "cost_available_time",
    "spread_sample_count_1h",
    "median_spread_bps_1h",
    "p95_spread_bps_1h",
    "p99_spread_bps_1h",
    "min_spread_bps_1h",
    "max_spread_bps_1h",
    "first_event_time",
    "last_event_time",
    "max_sample_gap_ms",
    "stale_gap_count_1h",
    "source_path",
    "source_checksum",
    "dataset_version",
    "execution_cost_quality",
    "normalized_at",
)
JOIN_COST_COLUMNS = (
    "cost_open_time",
    "cost_available_time",
    "cost_spread_sample_count_1h",
    "cost_median_spread_bps_1h",
    "cost_p95_spread_bps_1h",
    "cost_p99_spread_bps_1h",
    "cost_max_sample_gap_ms",
    "cost_stale_gap_count_1h",
    "cost_execution_cost_quality",
)
S3_LIST_ENDPOINT = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"


class ExecutionCostEvidenceError(ValueError):
    """Raised when historical execution-cost evidence cannot be trusted."""


@dataclass(frozen=True, slots=True)
class ExecutionCostGateConfig:
    """Thresholds for the Sprint 7 cost-gated pair approval."""

    expected_bars: int = DEFAULT_EXPECTED_1H_BARS
    min_hourly_coverage: float = 0.99
    max_longest_gap_hours: float = 6.0
    stale_gap_threshold_ms: int = DEFAULT_STALE_GAP_MS
    max_stale_hours: int = 0
    max_median_spread_bps: float = 3.0
    max_p95_spread_bps: float = 8.0
    max_p99_spread_bps: float = 15.0
    max_pair_median_spread_bps: float = 6.0
    max_pair_p95_spread_bps: float = 10.0

    def __post_init__(self) -> None:
        _positive_int("expected_bars", self.expected_bars)
        _positive_float("min_hourly_coverage", self.min_hourly_coverage)
        _non_negative_float("max_longest_gap_hours", self.max_longest_gap_hours)
        _positive_int("stale_gap_threshold_ms", self.stale_gap_threshold_ms)
        _non_negative_int("max_stale_hours", self.max_stale_hours)
        _positive_float("max_median_spread_bps", self.max_median_spread_bps)
        _positive_float("max_p95_spread_bps", self.max_p95_spread_bps)
        _positive_float("max_p99_spread_bps", self.max_p99_spread_bps)
        _positive_float("max_pair_median_spread_bps", self.max_pair_median_spread_bps)
        _positive_float("max_pair_p95_spread_bps", self.max_pair_p95_spread_bps)


@dataclass(frozen=True, slots=True)
class S3Object:
    """Small subset of S3 object-list metadata used as source provenance."""

    key: str
    size: int
    last_modified: str
    etag: str


def normalize_book_ticker_frame(
    raw: pd.DataFrame | Iterable[Mapping[str, Any]],
    symbol: str,
    *,
    source_path: str,
    source_checksum: str,
    dataset_version: str,
    normalized_at: str | None = None,
) -> pd.DataFrame:
    """Normalize one verified Binance USD-M historical bookTicker CSV."""

    data = _coerce_book_ticker_columns(raw)
    event_time_column = _first_existing(
        data,
        ("event_time", "eventTime", "time", "transaction_time", "transactionTime"),
    )
    bid_column = _first_existing(data, ("best_bid_price", "bidPrice", "bid_price"))
    ask_column = _first_existing(data, ("best_ask_price", "askPrice", "ask_price"))
    bid_qty_column = _first_existing(data, ("best_bid_qty", "bidQty", "bid_qty"))
    ask_qty_column = _first_existing(data, ("best_ask_qty", "askQty", "ask_qty"))
    transaction_time_column = _first_existing(data, ("transaction_time", "transactionTime"))
    if event_time_column is None or bid_column is None or ask_column is None:
        raise ExecutionCostEvidenceError("bookTicker data requires event time, bid, and ask")

    event_time = _numeric_series(data, event_time_column)
    transaction_time = (
        _numeric_series(data, transaction_time_column)
        if transaction_time_column is not None
        else pd.Series(np.nan, index=data.index)
    )
    best_bid = _numeric_series(data, bid_column)
    best_ask = _numeric_series(data, ask_column)
    bid_qty = (
        _numeric_series(data, bid_qty_column)
        if bid_qty_column is not None
        else pd.Series(np.nan, index=data.index)
    )
    ask_qty = (
        _numeric_series(data, ask_qty_column)
        if ask_qty_column is not None
        else pd.Series(np.nan, index=data.index)
    )
    update_id = (
        _numeric_series(data, "update_id")
        if "update_id" in data.columns
        else pd.Series(np.nan, index=data.index)
    )
    mid = (best_bid + best_ask) / 2.0
    valid = (
        np.isfinite(event_time)
        & np.isfinite(best_bid)
        & np.isfinite(best_ask)
        & (event_time >= 0)
        & (best_bid > 0)
        & (best_ask > 0)
        & (best_ask >= best_bid)
        & np.isfinite(mid)
        & (mid > 0)
    )
    spread_bps = (best_ask - best_bid) / mid * 10_000.0
    result = pd.DataFrame(
        {
            "venue": "BINANCE",
            "market_type": "USD_M_FUTURES",
            "contract_type": "PERPETUAL",
            "symbol": _normalize_symbol(symbol),
            "event_time": event_time.loc[valid].astype("int64"),
            "transaction_time": transaction_time.loc[valid],
            "update_id": update_id.loc[valid],
            "best_bid": best_bid.loc[valid],
            "best_ask": best_ask.loc[valid],
            "bid_qty": bid_qty.loc[valid],
            "ask_qty": ask_qty.loc[valid],
            "mid_price": mid.loc[valid],
            "spread_bps": spread_bps.loc[valid],
            "source_path": source_path,
            "source_checksum": source_checksum,
            "dataset_version": dataset_version,
            "execution_cost_quality": ExecutionCostQuality.VERIFIED.value,
            "normalized_at": normalized_at or datetime.now(UTC).isoformat(),
        }
    )
    if result.empty:
        return pd.DataFrame(columns=RAW_COST_SAMPLE_COLUMNS)
    return result.loc[:, RAW_COST_SAMPLE_COLUMNS].sort_values(
        ["symbol", "event_time", "update_id"],
        kind="mergesort",
    ).reset_index(drop=True)


def aggregate_book_ticker_hourly(
    samples: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    stale_gap_threshold_ms: int = DEFAULT_STALE_GAP_MS,
    normalized_at: str | None = None,
) -> pd.DataFrame:
    """Aggregate verified top-of-book samples into stable hourly spread fields."""

    _positive_int("stale_gap_threshold_ms", stale_gap_threshold_ms)
    data = _dataframe(samples)
    if data.empty:
        return pd.DataFrame(columns=HOURLY_COST_COLUMNS)
    _require_columns(data, ("symbol", "event_time", "spread_bps"))
    prepared = data.copy()
    prepared["symbol"] = prepared["symbol"].astype("string").str.strip().str.upper()
    prepared["event_time"] = _numeric_series(prepared, "event_time")
    prepared["spread_bps"] = _numeric_series(prepared, "spread_bps")
    valid = prepared.loc[
        np.isfinite(prepared["event_time"])
        & np.isfinite(prepared["spread_bps"])
        & (prepared["spread_bps"] >= 0)
    ].copy()
    if valid.empty:
        return pd.DataFrame(columns=HOURLY_COST_COLUMNS)
    valid["event_time"] = valid["event_time"].astype("int64")
    valid["open_time"] = (valid["event_time"] // HOUR_MS) * HOUR_MS
    rows = [
        _hourly_cost_row(
            symbol=symbol,
            open_time=int(open_time),
            group=group,
            stale_gap_threshold_ms=stale_gap_threshold_ms,
            normalized_at=normalized_at,
        )
        for (symbol, open_time), group in valid.groupby(["symbol", "open_time"], sort=True)
    ]
    return pd.DataFrame(rows, columns=HOURLY_COST_COLUMNS).sort_values(
        ["symbol", "open_time"],
        kind="mergesort",
    ).reset_index(drop=True)


def join_cost_to_bars_no_lookahead(
    bars: pd.DataFrame | Iterable[Mapping[str, Any]],
    hourly_cost: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    decision_time_column: str = "open_time",
) -> pd.DataFrame:
    """Join hourly cost aggregates as-of using only cost available by decision time."""

    bar_data = _dataframe(bars).copy()
    if bar_data.empty:
        return _ensure_join_columns(bar_data)
    _require_columns(bar_data, ("symbol", decision_time_column))
    cost_data = _dataframe(hourly_cost).copy()
    bar_data["__row_order"] = np.arange(len(bar_data))
    bar_data["__decision_time"] = _numeric_series(bar_data, decision_time_column)
    bar_data["symbol"] = bar_data["symbol"].astype("string").str.strip().str.upper()
    if cost_data.empty:
        return _ensure_join_columns(bar_data.drop(columns=["__row_order", "__decision_time"]))

    _require_columns(cost_data, ("symbol", "open_time", "cost_available_time"))
    cost_data["symbol"] = cost_data["symbol"].astype("string").str.strip().str.upper()
    cost_data["cost_available_time"] = _numeric_series(cost_data, "cost_available_time")
    right = cost_data.rename(
        columns={
            "open_time": "cost_open_time",
            "spread_sample_count_1h": "cost_spread_sample_count_1h",
            "median_spread_bps_1h": "cost_median_spread_bps_1h",
            "p95_spread_bps_1h": "cost_p95_spread_bps_1h",
            "p99_spread_bps_1h": "cost_p99_spread_bps_1h",
            "max_sample_gap_ms": "cost_max_sample_gap_ms",
            "stale_gap_count_1h": "cost_stale_gap_count_1h",
            "execution_cost_quality": "cost_execution_cost_quality",
        }
    )
    right_columns = ("symbol", *JOIN_COST_COLUMNS)
    right = right.loc[:, [column for column in right_columns if column in right.columns]]
    joined_frames = []
    for symbol, left_group in bar_data.groupby("symbol", sort=False):
        left_sorted = left_group.sort_values("__decision_time", kind="mergesort")
        right_group = right.loc[right["symbol"] == symbol].sort_values(
            "cost_available_time",
            kind="mergesort",
        )
        if right_group.empty:
            joined_frames.append(_ensure_join_columns(left_sorted))
            continue
        merged = pd.merge_asof(
            left_sorted,
            right_group.drop(columns=["symbol"]),
            left_on="__decision_time",
            right_on="cost_available_time",
            direction="backward",
            allow_exact_matches=True,
        )
        joined_frames.append(merged)
    joined = pd.concat(joined_frames, ignore_index=True)
    joined = joined.sort_values("__row_order", kind="mergesort").drop(
        columns=["__row_order", "__decision_time"]
    )
    return _ensure_join_columns(joined.reset_index(drop=True))


def evaluate_execution_cost_gate(
    bars: pd.DataFrame | Iterable[Mapping[str, Any]],
    candidate_pairs: Iterable[str | Mapping[str, Any]],
    hourly_cost: pd.DataFrame | Iterable[Mapping[str, Any]] | None = None,
    *,
    config: ExecutionCostGateConfig | None = None,
) -> dict[str, Any]:
    """Evaluate Sprint 7 cost-gated pass/fail decisions for candidate pairs."""

    cfg = config or ExecutionCostGateConfig()
    bar_data = _dataframe(bars)
    cost_data = (
        pd.DataFrame(columns=HOURLY_COST_COLUMNS)
        if hourly_cost is None
        else _dataframe(hourly_cost)
    )
    pairs = tuple(_pair_id(pair) for pair in candidate_pairs)
    symbols = tuple(sorted(_symbols_from_bars_and_pairs(bar_data, pairs)))
    joined = join_cost_to_bars_no_lookahead(bar_data, cost_data)
    symbol_stats = [
        _symbol_cost_stats(joined, symbol, cfg, source_absent=cost_data.empty)
        for symbol in symbols
    ]
    stats_by_symbol = {item["symbol"]: item for item in symbol_stats}
    pair_results = [_pair_cost_result(pair, stats_by_symbol, cfg) for pair in pairs]
    pairs_passed = [item for item in pair_results if item["cost_gated_pass"]]
    pairs_failed = [item for item in pair_results if not item["cost_gated_pass"]]
    return {
        "cost_gated_pass": bool(pairs_passed),
        "pairs_passed": len(pairs_passed),
        "pairs_failed": len(pairs_failed),
        "symbol_count": len(symbol_stats),
        "symbol_cost_stats": symbol_stats,
        "pair_cost_results": pair_results,
        "thresholds": _threshold_payload(cfg),
    }


def parse_s3_list_objects(xml_text: str) -> tuple[S3Object, ...]:
    """Parse an S3 ListBucketResult XML payload into object metadata."""

    root = ElementTree.fromstring(xml_text)
    namespace = "{http://s3.amazonaws.com/doc/2006-03-01/}"
    objects = []
    for item in root.findall(f"{namespace}Contents"):
        key = item.findtext(f"{namespace}Key") or ""
        size_text = item.findtext(f"{namespace}Size") or "0"
        objects.append(
            S3Object(
                key=key,
                size=int(size_text),
                last_modified=item.findtext(f"{namespace}LastModified") or "",
                etag=(item.findtext(f"{namespace}ETag") or "").strip('"'),
            )
        )
    return tuple(objects)


def summarize_book_ticker_source(
    symbols: Iterable[str],
    *,
    start_month: str,
    end_month_exclusive: str,
    monthly_objects_by_symbol: Mapping[str, Iterable[S3Object]],
    daily_objects_by_symbol: Mapping[str, Iterable[S3Object]] | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Summarize Binance public-data bookTicker coverage without downloading archives."""

    months = month_range(start_month, end_month_exclusive)
    daily_by_symbol = daily_objects_by_symbol or {}
    symbol_reviews = [
        _book_ticker_symbol_review(
            symbol=_normalize_symbol(symbol),
            months=months,
            monthly_objects=tuple(monthly_objects_by_symbol.get(_normalize_symbol(symbol), ())),
            daily_objects=tuple(daily_by_symbol.get(_normalize_symbol(symbol), ())),
        )
        for symbol in symbols
    ]
    complete = bool(symbol_reviews) and all(item["complete_for_window"] for item in symbol_reviews)
    return {
        "source": "Binance Public Data bookTicker",
        "base_url": BINANCE_PUBLIC_DATA_BASE_URL,
        "s3_list_endpoint": S3_LIST_ENDPOINT,
        "period": {
            "start_month": start_month,
            "end_month_exclusive": end_month_exclusive,
            "months_required": len(months),
        },
        "symbols_required": [_normalize_symbol(symbol) for symbol in symbols],
        "granularity_evaluated": ["monthly/bookTicker", "daily/bookTicker"],
        "fields": list(BOOK_TICKER_COLUMNS),
        "source_exists": any(item["covered_months"] > 0 for item in symbol_reviews),
        "complete_for_window": complete,
        "decision": "SOURCE_COMPLETE" if complete else "SOURCE_INCOMPLETE_FAIL_CLOSED",
        "limits": _threshold_payload(ExecutionCostGateConfig()),
        "symbol_reviews": symbol_reviews,
        "generated_at_utc": generated_at_utc or datetime.now(UTC).isoformat(),
    }


def build_unavailable_source_review(
    symbols: Iterable[str],
    *,
    start_month: str,
    end_month_exclusive: str,
    reason: str,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a fail-closed source review when a probe cannot provide evidence."""

    return {
        "source": "Binance Public Data bookTicker",
        "base_url": BINANCE_PUBLIC_DATA_BASE_URL,
        "period": {
            "start_month": start_month,
            "end_month_exclusive": end_month_exclusive,
        },
        "symbols_required": [_normalize_symbol(symbol) for symbol in symbols],
        "source_exists": False,
        "complete_for_window": False,
        "decision": "SOURCE_UNAVAILABLE_FAIL_CLOSED",
        "reason": reason,
        "limits": _threshold_payload(ExecutionCostGateConfig()),
        "generated_at_utc": generated_at_utc or datetime.now(UTC).isoformat(),
    }


def _coerce_book_ticker_columns(
    raw: pd.DataFrame | Iterable[Mapping[str, Any]],
) -> pd.DataFrame:
    data = _dataframe(raw).copy()
    if data.empty:
        return pd.DataFrame(columns=BOOK_TICKER_COLUMNS)
    renamed = {column: str(column).strip() for column in data.columns}
    data = data.rename(columns=renamed)
    lower_to_original = {str(column).strip(): column for column in data.columns}
    if {"best_bid_price", "best_ask_price"}.issubset(lower_to_original):
        return data
    first_row = tuple(str(value).strip() for value in data.iloc[0].tolist())
    if {"best_bid_price", "best_ask_price", "event_time"}.issubset(first_row):
        columns = [str(value).strip() for value in data.iloc[0].tolist()]
        result = data.iloc[1:].copy()
        result.columns = columns
        return result.reset_index(drop=True)
    if len(data.columns) < len(BOOK_TICKER_COLUMNS):
        raise ExecutionCostEvidenceError("bookTicker data has fewer columns than expected")
    result = data.iloc[:, : len(BOOK_TICKER_COLUMNS)].copy()
    result.columns = BOOK_TICKER_COLUMNS
    return result


def _hourly_cost_row(
    *,
    symbol: str,
    open_time: int,
    group: pd.DataFrame,
    stale_gap_threshold_ms: int,
    normalized_at: str | None,
) -> dict[str, Any]:
    spreads = _finite_values(group["spread_bps"])
    times = np.sort(pd.to_numeric(group["event_time"], errors="coerce").dropna().unique())
    diffs = np.diff(times) if len(times) > 1 else np.array([], dtype="float64")
    return {
        "venue": "BINANCE",
        "market_type": "USD_M_FUTURES",
        "contract_type": "PERPETUAL",
        "symbol": str(symbol),
        "interval": "1h",
        "open_time": open_time,
        "close_time": open_time + HOUR_MS - 1,
        "cost_available_time": open_time + HOUR_MS,
        "spread_sample_count_1h": int(len(spreads)),
        "median_spread_bps_1h": _finite_median(spreads),
        "p95_spread_bps_1h": _finite_quantile(spreads, 0.95),
        "p99_spread_bps_1h": _finite_quantile(spreads, 0.99),
        "min_spread_bps_1h": _finite_min(spreads),
        "max_spread_bps_1h": _finite_max(spreads),
        "first_event_time": int(times[0]) if len(times) else math.nan,
        "last_event_time": int(times[-1]) if len(times) else math.nan,
        "max_sample_gap_ms": float(diffs.max()) if len(diffs) else 0.0,
        "stale_gap_count_1h": int((diffs > stale_gap_threshold_ms).sum()),
        "source_path": _join_unique(group.get("source_path")),
        "source_checksum": _join_unique(group.get("source_checksum")),
        "dataset_version": _join_unique(group.get("dataset_version")),
        "execution_cost_quality": ExecutionCostQuality.VERIFIED.value,
        "normalized_at": normalized_at or datetime.now(UTC).isoformat(),
    }


def _symbol_cost_stats(
    joined: pd.DataFrame,
    symbol: str,
    config: ExecutionCostGateConfig,
    *,
    source_absent: bool,
) -> dict[str, Any]:
    rows = (
        joined.loc[joined["symbol"] == symbol].copy()
        if "symbol" in joined.columns
        else pd.DataFrame()
    )
    if rows.empty:
        return _empty_symbol_cost_stats(symbol, config, source_absent=source_absent)
    complete = (
        rows["is_complete_bar"].fillna(False).astype(bool)
        if "is_complete_bar" in rows.columns
        else pd.Series(True, index=rows.index)
    )
    rows = rows.loc[complete].copy()
    denominator = max(int(len(rows)), config.expected_bars)
    verified = rows["cost_execution_cost_quality"] == ExecutionCostQuality.VERIFIED.value
    spreads = _finite_values(rows.loc[verified, "cost_median_spread_bps_1h"])
    p95_values = _finite_values(rows.loc[verified, "cost_p95_spread_bps_1h"])
    p99_values = _finite_values(rows.loc[verified, "cost_p99_spread_bps_1h"])
    stale_hours = int((_numeric_series(rows.loc[verified], "cost_stale_gap_count_1h") > 0).sum())
    coverage = float(verified.sum()) / float(denominator) if denominator else 0.0
    longest_missing = _longest_missing_cost_gap_hours(rows, verified)
    median_spread = _finite_median(spreads)
    p95_spread = _finite_quantile(p95_values, 0.95)
    p99_spread = _finite_quantile(p99_values, 0.99)
    reasons = _symbol_cost_reasons(
        source_absent=source_absent,
        coverage=coverage,
        longest_missing_gap_hours=longest_missing,
        stale_hours=stale_hours,
        median_spread=median_spread,
        p95_spread=p95_spread,
        p99_spread=p99_spread,
        config=config,
    )
    return {
        "symbol": symbol,
        "cost_gated_symbol_pass": not reasons,
        "execution_cost_quality": (
            ExecutionCostQuality.VERIFIED.value
            if not reasons
            else ExecutionCostQuality.INCOMPLETE.value
        ),
        "valid_bars": int(len(rows)),
        "expected_bars": config.expected_bars,
        "cost_coverage": coverage,
        "longest_missing_cost_gap_hours": longest_missing,
        "stale_hours": stale_hours,
        "median_spread_bps": median_spread,
        "p95_spread_bps": p95_spread,
        "p99_spread_bps": p99_spread,
        "min_sample_count_1h": _finite_min(
            _numeric_series(rows.loc[verified], "cost_spread_sample_count_1h")
        ),
        "median_sample_count_1h": _finite_median(
            _numeric_series(rows.loc[verified], "cost_spread_sample_count_1h")
        ),
        "max_sample_gap_ms": _finite_max(
            _numeric_series(rows.loc[verified], "cost_max_sample_gap_ms")
        ),
        "reasons": reasons,
    }


def _empty_symbol_cost_stats(
    symbol: str,
    config: ExecutionCostGateConfig,
    *,
    source_absent: bool,
) -> dict[str, Any]:
    reason = (
        "HISTORICAL_COST_EVIDENCE_UNAVAILABLE"
        if source_absent
        else "HISTORICAL_COST_COVERAGE_INCOMPLETE"
    )
    return {
        "symbol": symbol,
        "cost_gated_symbol_pass": False,
        "execution_cost_quality": ExecutionCostQuality.UNAVAILABLE.value,
        "valid_bars": 0,
        "expected_bars": config.expected_bars,
        "cost_coverage": 0.0,
        "longest_missing_cost_gap_hours": float(config.expected_bars),
        "stale_hours": 0,
        "median_spread_bps": math.nan,
        "p95_spread_bps": math.nan,
        "p99_spread_bps": math.nan,
        "min_sample_count_1h": math.nan,
        "median_sample_count_1h": math.nan,
        "max_sample_gap_ms": math.nan,
        "reasons": [reason],
    }


def _symbol_cost_reasons(
    *,
    source_absent: bool,
    coverage: float,
    longest_missing_gap_hours: float,
    stale_hours: int,
    median_spread: float,
    p95_spread: float,
    p99_spread: float,
    config: ExecutionCostGateConfig,
) -> list[str]:
    reasons: list[str] = []
    if source_absent:
        reasons.append("HISTORICAL_COST_EVIDENCE_UNAVAILABLE")
        return reasons
    if coverage < config.min_hourly_coverage:
        reasons.append("HISTORICAL_COST_COVERAGE_INCOMPLETE")
    if longest_missing_gap_hours > config.max_longest_gap_hours:
        reasons.append("HISTORICAL_COST_LONG_GAP")
    if stale_hours > config.max_stale_hours:
        reasons.append("HISTORICAL_COST_STALE")
    if (
        not math.isfinite(median_spread)
        or not math.isfinite(p95_spread)
        or not math.isfinite(p99_spread)
    ):
        reasons.append("HISTORICAL_COST_SPREAD_STATS_MISSING")
    if math.isfinite(median_spread) and median_spread > config.max_median_spread_bps:
        reasons.append("WIDE_MEDIAN_SPREAD")
    if math.isfinite(p95_spread) and p95_spread > config.max_p95_spread_bps:
        reasons.append("WIDE_P95_SPREAD")
    if math.isfinite(p99_spread) and p99_spread > config.max_p99_spread_bps:
        reasons.append("WIDE_P99_SPREAD")
    return reasons


def _pair_cost_result(
    pair_id: str,
    stats_by_symbol: Mapping[str, Mapping[str, Any]],
    config: ExecutionCostGateConfig,
) -> dict[str, Any]:
    symbol_a, symbol_b = pair_id.split("/", maxsplit=1)
    stats_a = stats_by_symbol.get(symbol_a)
    stats_b = stats_by_symbol.get(symbol_b)
    reasons: list[str] = []
    if stats_a is None or stats_b is None:
        reasons.append("PAIR_COST_SYMBOL_STATS_MISSING")
        return _failed_pair_payload(pair_id, math.nan, math.nan, math.nan, reasons)
    if not stats_a["cost_gated_symbol_pass"] or not stats_b["cost_gated_symbol_pass"]:
        reasons.append("LEG_COST_EVIDENCE_INCOMPLETE")
    combined_median = _combined(stats_a["median_spread_bps"], stats_b["median_spread_bps"])
    combined_p95 = _combined(stats_a["p95_spread_bps"], stats_b["p95_spread_bps"])
    combined_p99 = _combined(stats_a["p99_spread_bps"], stats_b["p99_spread_bps"])
    if _above_or_missing(combined_median, config.max_pair_median_spread_bps):
        reasons.append("PAIR_WIDE_MEDIAN_SPREAD")
    if _above_or_missing(combined_p95, config.max_pair_p95_spread_bps):
        reasons.append("PAIR_WIDE_TAIL_SPREAD")
    return {
        "pair": pair_id,
        "cost_gated_pass": not reasons,
        "combined_median_spread_bps": combined_median,
        "combined_p95_spread_bps": combined_p95,
        "combined_p99_spread_bps": combined_p99,
        "reasons": reasons,
    }


def _failed_pair_payload(
    pair_id: str,
    combined_median: float,
    combined_p95: float,
    combined_p99: float,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "pair": pair_id,
        "cost_gated_pass": False,
        "combined_median_spread_bps": combined_median,
        "combined_p95_spread_bps": combined_p95,
        "combined_p99_spread_bps": combined_p99,
        "reasons": reasons,
    }


def _book_ticker_symbol_review(
    *,
    symbol: str,
    months: tuple[str, ...],
    monthly_objects: tuple[S3Object, ...],
    daily_objects: tuple[S3Object, ...],
) -> dict[str, Any]:
    monthly_by_key = {item.key: item for item in monthly_objects}
    daily_by_key = {item.key: item for item in daily_objects}
    month_reviews = [
        _book_ticker_month_review(symbol, month, monthly_by_key, daily_by_key)
        for month in months
    ]
    missing = [item["month"] for item in month_reviews if not item["covered"]]
    covered_months = len(month_reviews) - len(missing)
    return {
        "symbol": symbol,
        "complete_for_window": not missing,
        "covered_months": covered_months,
        "required_months": len(months),
        "coverage": float(covered_months) / float(len(months)) if months else 0.0,
        "missing_months": missing,
        "available_compressed_bytes": sum(
            int(item["archive_size_bytes"]) for item in month_reviews if item["covered"]
        ),
        "month_reviews": month_reviews,
    }


def _book_ticker_month_review(
    symbol: str,
    month: str,
    monthly_by_key: Mapping[str, S3Object],
    daily_by_key: Mapping[str, S3Object],
) -> dict[str, Any]:
    monthly_key = f"data/futures/um/monthly/bookTicker/{symbol}/{symbol}-bookTicker-{month}.zip"
    checksum_key = f"{monthly_key}.CHECKSUM"
    if monthly_key in monthly_by_key and checksum_key in monthly_by_key:
        archive = monthly_by_key[monthly_key]
        return {
            "month": month,
            "covered": True,
            "granularity": "monthly",
            "archive_key": monthly_key,
            "checksum_key": checksum_key,
            "archive_size_bytes": archive.size,
            "archive_last_modified": archive.last_modified,
            "archive_etag": archive.etag,
        }

    daily_keys = _daily_book_ticker_keys(symbol, month)
    missing_daily = [
        key
        for key in daily_keys
        if key not in daily_by_key or f"{key}.CHECKSUM" not in daily_by_key
    ]
    if not missing_daily:
        archive_size = sum(daily_by_key[key].size for key in daily_keys)
        return {
            "month": month,
            "covered": True,
            "granularity": "daily",
            "archive_key": "",
            "checksum_key": "",
            "archive_size_bytes": archive_size,
            "daily_archive_count": len(daily_keys),
            "daily_checksum_count": len(daily_keys),
        }
    return {
        "month": month,
        "covered": False,
        "granularity": "missing",
        "archive_key": monthly_key,
        "checksum_key": checksum_key,
        "archive_size_bytes": 0,
        "missing_daily_archives": len(missing_daily),
        "sample_missing_daily_key": missing_daily[0] if missing_daily else "",
    }


def _daily_book_ticker_keys(symbol: str, month: str) -> tuple[str, ...]:
    start = _month_start(month)
    end = _add_one_month(start)
    keys = []
    current = start
    while current < end:
        day = current.isoformat()
        keys.append(f"data/futures/um/daily/bookTicker/{symbol}/{symbol}-bookTicker-{day}.zip")
        current += timedelta(days=1)
    return tuple(keys)


def _month_start(month: str) -> date:
    year_text, month_text = month.split("-", maxsplit=1)
    return date(int(year_text), int(month_text), 1)


def _add_one_month(value: date) -> date:
    if value.month == DECEMBER:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _dataframe(data: pd.DataFrame | Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    return data.copy(deep=True) if isinstance(data, pd.DataFrame) else pd.DataFrame(data)


def _ensure_join_columns(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    for column in JOIN_COST_COLUMNS:
        if column not in result.columns:
            result[column] = np.nan
    result["cost_execution_cost_quality"] = result["cost_execution_cost_quality"].fillna(
        ExecutionCostQuality.UNAVAILABLE.value
    )
    return result


def _symbols_from_bars_and_pairs(data: pd.DataFrame, pairs: tuple[str, ...]) -> set[str]:
    symbols: set[str] = set()
    if "symbol" in data.columns:
        symbols.update(data["symbol"].astype("string").str.strip().str.upper().dropna())
    for pair in pairs:
        left, right = pair.split("/", maxsplit=1)
        symbols.add(left)
        symbols.add(right)
    return symbols


def _pair_id(pair: str | Mapping[str, Any]) -> str:
    if isinstance(pair, str):
        return pair.strip().upper()
    if "pair" not in pair:
        raise ExecutionCostEvidenceError("candidate pair mapping must include 'pair'")
    return str(pair["pair"]).strip().upper()


def _longest_missing_cost_gap_hours(rows: pd.DataFrame, verified: pd.Series) -> float:
    if rows.empty:
        return 0.0
    ordered = rows.assign(__cost_verified=verified).sort_values("open_time", kind="mergesort")
    longest = 0
    current = 0
    previous_time: int | None = None
    for open_time_value, is_verified in zip(
        ordered["open_time"],
        ordered["__cost_verified"],
        strict=True,
    ):
        open_time = int(open_time_value)
        if previous_time is not None and open_time - previous_time != HOUR_MS:
            current = 0
        if bool(is_verified):
            current = 0
        else:
            current += 1
            longest = max(longest, current)
        previous_time = open_time
    return float(longest)


def _threshold_payload(config: ExecutionCostGateConfig) -> dict[str, Any]:
    return {
        "min_hourly_coverage": config.min_hourly_coverage,
        "max_longest_gap_hours": config.max_longest_gap_hours,
        "stale_gap_threshold_ms": config.stale_gap_threshold_ms,
        "max_stale_hours": config.max_stale_hours,
        "max_median_spread_bps": config.max_median_spread_bps,
        "max_p95_spread_bps": config.max_p95_spread_bps,
        "max_p99_spread_bps": config.max_p99_spread_bps,
        "max_pair_median_spread_bps": config.max_pair_median_spread_bps,
        "max_pair_p95_spread_bps": config.max_pair_p95_spread_bps,
    }


def _require_columns(data: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = sorted(set(columns).difference(data.columns))
    if missing:
        raise ExecutionCostEvidenceError(f"execution-cost data missing columns: {missing}")


def _first_existing(data: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    lookup = {str(column).strip(): column for column in data.columns}
    lower_lookup = {str(column).strip().lower(): column for column in data.columns}
    for candidate in candidates:
        if candidate in lookup:
            return str(lookup[candidate])
        lowered = candidate.lower()
        if lowered in lower_lookup:
            return str(lower_lookup[lowered])
    return None


def _normalize_symbol(symbol: str) -> str:
    normalized = str(symbol).strip().upper()
    if not normalized:
        raise ExecutionCostEvidenceError("symbol is required")
    return normalized


def _numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(np.nan, index=data.index, dtype="float64")
    return pd.to_numeric(data[column], errors="coerce")


def _finite_values(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.loc[np.isfinite(numeric)]


def _finite_median(values: pd.Series) -> float:
    finite = _finite_values(values)
    return math.nan if finite.empty else float(finite.median())


def _finite_quantile(values: pd.Series, quantile: float) -> float:
    finite = _finite_values(values)
    return math.nan if finite.empty else float(finite.quantile(quantile))


def _finite_min(values: pd.Series) -> float:
    finite = _finite_values(values)
    return math.nan if finite.empty else float(finite.min())


def _finite_max(values: pd.Series) -> float:
    finite = _finite_values(values)
    return math.nan if finite.empty else float(finite.max())


def _join_unique(values: pd.Series | None) -> str:
    if values is None:
        return ""
    unique = sorted({str(value) for value in values.dropna().unique() if str(value)})
    return ";".join(unique)


def _combined(left: Any, right: Any) -> float:
    left_value = float(left)
    right_value = float(right)
    if not math.isfinite(left_value) or not math.isfinite(right_value):
        return math.nan
    return left_value + right_value


def _above_or_missing(value: float, threshold: float) -> bool:
    return not math.isfinite(value) or value > threshold


def _positive_int(field_name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _non_negative_int(field_name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
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
    "BOOK_TICKER_COLUMNS",
    "HOURLY_COST_COLUMNS",
    "JOIN_COST_COLUMNS",
    "RAW_COST_SAMPLE_COLUMNS",
    "S3Object",
    "ExecutionCostEvidenceError",
    "ExecutionCostGateConfig",
    "aggregate_book_ticker_hourly",
    "build_unavailable_source_review",
    "evaluate_execution_cost_gate",
    "join_cost_to_bars_no_lookahead",
    "normalize_book_ticker_frame",
    "parse_s3_list_objects",
    "summarize_book_ticker_source",
]
