"""Binance public-data loader and normalizer for Sprint 7 research datasets."""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

BINANCE_PUBLIC_DATA_BASE_URL = "https://data.binance.vision"
HOUR_MS = 60 * 60 * 1000
SHA256_HEX_LENGTH = 64
DECEMBER = 12
EXTREME_RETURN_THRESHOLD = 0.25
KLINE_COLUMNS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
)
FUNDING_COLUMNS = ("calc_time", "funding_interval_hours", "last_funding_rate")


class HistoricalDatasetError(ValueError):
    """Raised when historical data cannot be trusted or normalized."""


class BinanceDataFamily(StrEnum):
    """Supported Binance USD-M public-data families for Sprint 7."""

    KLINES = "klines"
    MARK_PRICE_KLINES = "markPriceKlines"
    INDEX_PRICE_KLINES = "indexPriceKlines"
    PREMIUM_INDEX_KLINES = "premiumIndexKlines"
    FUNDING_RATE = "fundingRate"
    BOOK_TICKER = "bookTicker"


@dataclass(frozen=True, slots=True)
class BinanceArchiveSpec:
    """One monthly public-data archive and its checksum URL."""

    family: BinanceDataFamily
    symbol: str
    year_month: str
    interval: str = "1h"
    base_url: str = BINANCE_PUBLIC_DATA_BASE_URL

    @property
    def filename(self) -> str:
        if self.family in (BinanceDataFamily.FUNDING_RATE, BinanceDataFamily.BOOK_TICKER):
            return f"{self.symbol}-{self.family.value}-{self.year_month}.zip"
        return f"{self.symbol}-{self.interval}-{self.year_month}.zip"

    @property
    def relative_path(self) -> str:
        if self.family in (BinanceDataFamily.FUNDING_RATE, BinanceDataFamily.BOOK_TICKER):
            return f"data/futures/um/monthly/{self.family.value}/{self.symbol}/{self.filename}"
        return (
            f"data/futures/um/monthly/{self.family.value}/{self.symbol}/"
            f"{self.interval}/{self.filename}"
        )

    @property
    def url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.relative_path}"

    @property
    def checksum_url(self) -> str:
        return f"{self.url}.CHECKSUM"

    def archive_path(self, root: Path) -> Path:
        return root / self.relative_path

    def checksum_path(self, root: Path) -> Path:
        return root / f"{self.relative_path}.CHECKSUM"


@dataclass(frozen=True, slots=True)
class ChecksumVerification:
    """Result of SHA256 checksum verification."""

    expected_sha256: str
    actual_sha256: str
    filename: str

    @property
    def passed(self) -> bool:
        return self.expected_sha256 == self.actual_sha256


@dataclass(frozen=True, slots=True)
class DownloadedArchive:
    """Downloaded archive paths plus checksum verification."""

    spec: BinanceArchiveSpec
    archive_path: Path
    checksum_path: Path
    checksum: ChecksumVerification


def month_range(start_month: str, end_month_exclusive: str) -> tuple[str, ...]:
    """Return UTC calendar months in ``YYYY-MM`` format for a half-open window."""

    start = _parse_year_month(start_month)
    end = _parse_year_month(end_month_exclusive)
    if start >= end:
        raise ValueError("start_month must be earlier than end_month_exclusive")

    months: list[str] = []
    current = start
    while current < end:
        months.append(f"{current.year:04d}-{current.month:02d}")
        current = _add_one_month(current)
    return tuple(months)


def expected_hourly_bars(start_month: str, end_month_exclusive: str) -> int:
    """Return expected hourly bars in a half-open complete-month UTC window."""

    start = _month_start_datetime(start_month)
    end = _month_start_datetime(end_month_exclusive)
    if start >= end:
        raise ValueError("start_month must be earlier than end_month_exclusive")
    return int((end - start).total_seconds() // 3600)


def build_archive_plan(
    symbols: Iterable[str],
    *,
    start_month: str,
    end_month_exclusive: str,
    interval: str = "1h",
    families: Sequence[BinanceDataFamily | str] | None = None,
) -> tuple[BinanceArchiveSpec, ...]:
    """Build deterministic monthly public-data archive specs."""

    selected_families = tuple(
        BinanceDataFamily(family)
        for family in (
            families
            if families is not None
            else (
                BinanceDataFamily.KLINES,
                BinanceDataFamily.MARK_PRICE_KLINES,
                BinanceDataFamily.INDEX_PRICE_KLINES,
                BinanceDataFamily.PREMIUM_INDEX_KLINES,
                BinanceDataFamily.FUNDING_RATE,
            )
        )
    )
    months = month_range(start_month, end_month_exclusive)
    specs = [
        BinanceArchiveSpec(
            family=family,
            symbol=_normalize_symbol(symbol),
            year_month=month,
            interval=interval,
        )
        for symbol in symbols
        for month in months
        for family in selected_families
    ]
    return tuple(specs)


def download_archives(
    specs: Iterable[BinanceArchiveSpec],
    root: Path,
    *,
    overwrite: bool = False,
    timeout_seconds: float = 30.0,
    max_workers: int = 1,
) -> tuple[DownloadedArchive, ...]:
    """Download archives and checksum files, then verify SHA256."""

    ordered_specs = tuple(specs)
    if max_workers <= 1:
        return tuple(
            _download_archive(
                spec,
                root,
                overwrite=overwrite,
                timeout_seconds=timeout_seconds,
            )
            for spec in ordered_specs
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return tuple(
            executor.map(
                lambda spec: _download_archive(
                    spec,
                    root,
                    overwrite=overwrite,
                    timeout_seconds=timeout_seconds,
                ),
                ordered_specs,
            )
        )


def verify_checksum_file(archive_path: Path, checksum_path: Path) -> ChecksumVerification:
    """Verify Binance ``.CHECKSUM`` contents against a local archive."""

    expected_sha256, filename = parse_checksum_text(checksum_path.read_text(encoding="utf-8"))
    actual_sha256 = sha256_file(archive_path)
    verification = ChecksumVerification(
        expected_sha256=expected_sha256,
        actual_sha256=actual_sha256,
        filename=filename,
    )
    if not verification.passed:
        raise HistoricalDatasetError(
            f"checksum mismatch for {archive_path}: expected {expected_sha256}, got {actual_sha256}"
        )
    if filename and filename != archive_path.name:
        raise HistoricalDatasetError(
            f"checksum filename mismatch for {archive_path}: checksum names {filename}"
        )
    return verification


def parse_checksum_text(text: str) -> tuple[str, str]:
    """Parse Binance checksum text in ``<sha256> <filename>`` form."""

    parts = text.strip().split()
    if not parts:
        raise HistoricalDatasetError("empty checksum file")
    checksum = parts[0].strip().lower()
    if len(checksum) != SHA256_HEX_LENGTH or any(
        char not in "0123456789abcdef" for char in checksum
    ):
        raise HistoricalDatasetError(f"invalid SHA256 checksum: {checksum!r}")
    filename = parts[1].strip().lstrip("*") if len(parts) > 1 else ""
    return checksum, filename


def sha256_file(path: Path) -> str:
    """Return the SHA256 hex digest for a local file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_archive_plan(
    specs: Iterable[BinanceArchiveSpec],
    root: Path,
    *,
    dataset_version: str,
    verify_checksums: bool = True,
) -> pd.DataFrame:
    """Normalize downloaded archives from a spec plan into research bars."""

    grouped: dict[str, dict[BinanceDataFamily, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for spec in specs:
        archive_path = spec.archive_path(root)
        if not archive_path.exists():
            raise FileNotFoundError(archive_path)
        if verify_checksums:
            verify_checksum_file(archive_path, spec.checksum_path(root))
        grouped[spec.symbol][spec.family].append(archive_path)

    frames = [
        normalize_symbol_archive_files(symbol, archives, dataset_version=dataset_version)
        for symbol, archives in sorted(grouped.items())
    ]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values(["symbol", "open_time"]).reset_index(
        drop=True
    )


def normalize_symbol_archive_files(
    symbol: str,
    archives_by_family: Mapping[BinanceDataFamily | str, Sequence[Path]],
    *,
    dataset_version: str,
) -> pd.DataFrame:
    """Normalize all monthly archives for one symbol."""

    normalized_symbol = _normalize_symbol(symbol)
    kline_frames: list[pd.DataFrame] = []
    sidecar_frames: dict[BinanceDataFamily, list[pd.DataFrame]] = {
        BinanceDataFamily.MARK_PRICE_KLINES: [],
        BinanceDataFamily.INDEX_PRICE_KLINES: [],
        BinanceDataFamily.PREMIUM_INDEX_KLINES: [],
    }
    funding_frames: list[pd.DataFrame] = []

    for family_value, archive_paths in archives_by_family.items():
        family = BinanceDataFamily(family_value)
        for archive_path in archive_paths:
            raw = read_zip_csv(archive_path)
            source_checksum = sha256_file(archive_path)
            if family is BinanceDataFamily.FUNDING_RATE:
                funding_frames.append(
                    normalize_funding_frame(
                        raw,
                        normalized_symbol,
                        source_path=str(archive_path),
                        source_checksum=source_checksum,
                        dataset_version=dataset_version,
                    )
                )
            elif family is BinanceDataFamily.KLINES:
                kline_frames.append(
                    normalize_kline_frame(
                        raw,
                        normalized_symbol,
                        family,
                        source_path=str(archive_path),
                        source_checksum=source_checksum,
                        dataset_version=dataset_version,
                    )
                )
            else:
                sidecar_frames[family].append(
                    normalize_kline_frame(
                        raw,
                        normalized_symbol,
                        family,
                        source_path=str(archive_path),
                        source_checksum=source_checksum,
                        dataset_version=dataset_version,
                    )
                )

    if not kline_frames:
        raise HistoricalDatasetError(f"{normalized_symbol} requires at least one kline archive")

    klines = _concat_frames(kline_frames)
    mark = _concat_frames(sidecar_frames[BinanceDataFamily.MARK_PRICE_KLINES])
    index = _concat_frames(sidecar_frames[BinanceDataFamily.INDEX_PRICE_KLINES])
    premium = _concat_frames(sidecar_frames[BinanceDataFamily.PREMIUM_INDEX_KLINES])
    funding = _concat_frames(funding_frames)
    return merge_symbol_data(
        klines=klines,
        mark=mark,
        index=index,
        premium=premium,
        funding=funding,
    )


def read_zip_csv(path: Path) -> pd.DataFrame:
    """Read the single CSV inside a Binance public-data ZIP archive."""

    with zipfile.ZipFile(path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise HistoricalDatasetError(f"{path} must contain exactly one CSV; got {csv_names}")
        content = archive.read(csv_names[0])
    return pd.read_csv(io.BytesIO(content), header=None, dtype="string")


def normalize_kline_frame(
    raw: pd.DataFrame,
    symbol: str,
    family: BinanceDataFamily | str,
    *,
    source_path: str,
    source_checksum: str,
    dataset_version: str,
) -> pd.DataFrame:
    """Normalize one kline-like CSV family."""

    family = BinanceDataFamily(family)
    data = _coerce_expected_columns(raw, KLINE_COLUMNS)
    data = _drop_exact_duplicates_or_fail(data, subset=("open_time",), label=f"{symbol} {family}")
    numeric = _numeric_columns(data, KLINE_COLUMNS[:-1])
    price_values_valid = _kline_price_values_valid(numeric, family)
    open_time = _finite_int_series(numeric["open_time"])
    close_time = _finite_int_series(numeric["close_time"])
    open_price = numeric["open"]
    high = numeric["high"]
    low = numeric["low"]
    close = numeric["close"]
    valid = (
        open_time.notna()
        & close_time.notna()
        & (close_time > open_time)
        & price_values_valid
        & (high >= np.maximum(open_price, close))
        & (low <= np.minimum(open_price, close))
        & (high >= low)
        & _non_negative(numeric["volume"])
        & _non_negative(numeric["quote_volume"])
        & _non_negative(numeric["count"])
        & _non_negative(numeric["taker_buy_volume"])
        & _non_negative(numeric["taker_buy_quote_volume"])
    )
    cleaned = numeric.loc[valid].copy()
    cleaned["open_time"] = open_time.loc[valid].astype("int64")
    cleaned["close_time"] = close_time.loc[valid].astype("int64")
    cleaned = cleaned.sort_values("open_time", kind="mergesort").reset_index(drop=True)

    if family is BinanceDataFamily.KLINES:
        result = pd.DataFrame(
            {
                "venue": "BINANCE",
                "market_type": "USD_M_FUTURES",
                "contract_type": "PERPETUAL",
                "symbol": _normalize_symbol(symbol),
                "quote_asset": "USDT",
                "interval": "1h",
                "open_time": cleaned["open_time"],
                "close_time": cleaned["close_time"],
                "open": cleaned["open"],
                "high": cleaned["high"],
                "low": cleaned["low"],
                "close": cleaned["close"],
                "volume_base": cleaned["volume"],
                "quote_volume": cleaned["quote_volume"],
                "number_of_trades": cleaned["count"],
                "taker_buy_base_volume": cleaned["taker_buy_volume"],
                "taker_buy_quote_volume": cleaned["taker_buy_quote_volume"],
                "source_path": source_path,
                "source_checksum": source_checksum,
                "dataset_version": dataset_version,
            }
        )
        result["base_asset"] = result["symbol"].str.removesuffix("USDT")
        return result

    prefix = _sidecar_prefix(family)
    return pd.DataFrame(
        {
            "symbol": _normalize_symbol(symbol),
            "open_time": cleaned["open_time"],
            f"{prefix}_open": cleaned["open"],
            f"{prefix}_high": cleaned["high"],
            f"{prefix}_low": cleaned["low"],
            f"{prefix}_close": cleaned["close"],
        }
    )


def normalize_funding_frame(
    raw: pd.DataFrame,
    symbol: str,
    *,
    source_path: str,
    source_checksum: str,
    dataset_version: str,
) -> pd.DataFrame:
    """Normalize one Binance funding-rate CSV family."""

    data = _coerce_funding_columns(raw)
    funding_time_column = _first_existing(data, ("calc_time", "funding_time", "fundingTime"))
    funding_rate_column = _first_existing(
        data,
        ("last_funding_rate", "funding_rate", "fundingRate"),
    )
    interval_column = _first_existing(data, ("funding_interval_hours", "fundingIntervalHours"))
    if funding_time_column is None or funding_rate_column is None:
        raise HistoricalDatasetError("funding data requires funding time and funding rate columns")

    funding_time = _finite_int_series(pd.to_numeric(data[funding_time_column], errors="coerce"))
    funding_rate = pd.to_numeric(data[funding_rate_column], errors="coerce")
    interval = (
        pd.to_numeric(data[interval_column], errors="coerce")
        if interval_column is not None
        else pd.Series(np.nan, index=data.index)
    )
    valid = funding_time.notna() & np.isfinite(funding_rate)
    result = pd.DataFrame(
        {
            "symbol": _normalize_symbol(symbol),
            "funding_time": funding_time.loc[valid].astype("int64"),
            "funding_rate": funding_rate.loc[valid].astype(float),
            "funding_interval_hours": interval.loc[valid].astype(float),
            "funding_source_path": source_path,
            "funding_source_checksum": source_checksum,
            "dataset_version": dataset_version,
        }
    )
    result = _drop_exact_duplicates_or_fail(
        result,
        subset=("funding_time",),
        label=f"{symbol} funding",
    )
    return result.sort_values("funding_time", kind="mergesort").reset_index(drop=True)


def merge_symbol_data(
    *,
    klines: pd.DataFrame,
    mark: pd.DataFrame | None = None,
    index: pd.DataFrame | None = None,
    premium: pd.DataFrame | None = None,
    funding: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Merge base klines, price sidecars, and funding as-of data for one symbol."""

    bars = klines.copy().sort_values("open_time", kind="mergesort").reset_index(drop=True)
    for sidecar in (mark, index, premium):
        if sidecar is not None and not sidecar.empty:
            bars = bars.merge(sidecar, on=["symbol", "open_time"], how="left", sort=False)

    bars = _merge_funding_asof(bars, funding)
    mark_valid = "mark_close" in bars.columns and _positive(bars["mark_close"])
    bars["price_for_research"] = bars["close"]
    if isinstance(mark_valid, pd.Series):
        bars.loc[mark_valid, "price_for_research"] = bars.loc[mark_valid, "mark_close"]
    bars["log_price"] = np.log(bars["price_for_research"])
    bars["is_complete_bar"] = _positive(bars["price_for_research"]) & (
        bars["close_time"] > bars["open_time"]
    )
    bars["quality_flags"] = ""
    if isinstance(mark_valid, pd.Series):
        bars.loc[~mark_valid, "quality_flags"] = _append_flag(
            bars.loc[~mark_valid, "quality_flags"],
            "PRICE_FALLBACK_CLOSE",
        )
    bars["return_1h"] = _no_forward_fill_return(bars)
    extreme = bars["return_1h"].abs() > EXTREME_RETURN_THRESHOLD
    bars.loc[extreme, "quality_flags"] = _append_flag(
        bars.loc[extreme, "quality_flags"],
        "EXTREME_RETURN",
    )
    bars["execution_cost_quality"] = "UNAVAILABLE"
    bars["normalized_at"] = datetime.now(UTC).isoformat()
    return bars.sort_values("open_time", kind="mergesort").reset_index(drop=True)


def _download_url(
    url: str,
    path: Path,
    *,
    overwrite: bool,
    timeout_seconds: float,
) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=timeout_seconds) as response:
        path.write_bytes(response.read())


def _download_archive(
    spec: BinanceArchiveSpec,
    root: Path,
    *,
    overwrite: bool,
    timeout_seconds: float,
) -> DownloadedArchive:
    archive_path = spec.archive_path(root)
    checksum_path = spec.checksum_path(root)
    _download_url(spec.url, archive_path, overwrite=overwrite, timeout_seconds=timeout_seconds)
    _download_url(
        spec.checksum_url,
        checksum_path,
        overwrite=overwrite,
        timeout_seconds=timeout_seconds,
    )
    checksum = verify_checksum_file(archive_path, checksum_path)
    return DownloadedArchive(
        spec=spec,
        archive_path=archive_path,
        checksum_path=checksum_path,
        checksum=checksum,
    )


def _merge_funding_asof(bars: pd.DataFrame, funding: pd.DataFrame | None) -> pd.DataFrame:
    if funding is None or funding.empty:
        bars["funding_time"] = np.nan
        bars["funding_rate_asof"] = np.nan
        bars["funding_interval_hours"] = np.nan
        return bars

    left = bars.sort_values("close_time", kind="mergesort")
    right = funding.sort_values("funding_time", kind="mergesort")
    merged = pd.merge_asof(
        left,
        right[["funding_time", "funding_rate", "funding_interval_hours"]],
        left_on="close_time",
        right_on="funding_time",
        direction="backward",
    )
    merged = merged.rename(columns={"funding_rate": "funding_rate_asof"})
    return merged.sort_values("open_time", kind="mergesort").reset_index(drop=True)


def _no_forward_fill_return(bars: pd.DataFrame) -> pd.Series:
    log_price = pd.to_numeric(bars["log_price"], errors="coerce")
    consecutive = pd.to_numeric(bars["open_time"], errors="coerce").diff() == HOUR_MS
    returns = log_price.diff()
    returns.loc[~consecutive] = np.nan
    return returns


def _append_flag(values: pd.Series, flag: str) -> pd.Series:
    return values.apply(lambda value: flag if not value else f"{value};{flag}")


def _concat_frames(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _coerce_expected_columns(raw: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    if columns[0] in raw.columns:
        return raw.copy()
    if len(raw.columns) != len(columns):
        raise HistoricalDatasetError(f"expected {len(columns)} columns, got {len(raw.columns)}")
    result = raw.copy()
    result.columns = list(columns)
    return result


def _coerce_funding_columns(raw: pd.DataFrame) -> pd.DataFrame:
    if {"calc_time", "last_funding_rate"}.issubset(raw.columns):
        return raw.copy()
    if len(raw.columns) == len(FUNDING_COLUMNS):
        result = raw.copy()
        result.columns = list(FUNDING_COLUMNS)
        return result
    return raw.copy()


def _drop_exact_duplicates_or_fail(
    data: pd.DataFrame,
    *,
    subset: Sequence[str],
    label: str,
) -> pd.DataFrame:
    deduped = data.drop_duplicates().copy()
    duplicated = deduped.duplicated(subset=list(subset), keep=False)
    if duplicated.any():
        keys = deduped.loc[duplicated, list(subset)].drop_duplicates().to_dict("records")
        raise HistoricalDatasetError(f"{label} has disagreeing duplicate keys: {keys[:3]}")
    return deduped


def _numeric_columns(data: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            column: pd.to_numeric(data[column], errors="coerce").astype("float64")
            for column in columns
        }
    )


def _finite_int_series(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype("float64")
    result = pd.Series(np.nan, index=values.index, dtype="float64")
    finite = np.isfinite(numeric)
    result.loc[finite] = numeric.loc[finite]
    return result


def _positive(values: pd.Series) -> pd.Series:
    return np.isfinite(values) & (values > 0)


def _kline_price_values_valid(
    numeric: pd.DataFrame,
    family: BinanceDataFamily,
) -> pd.Series:
    columns = ("open", "high", "low", "close")
    finite = np.logical_and.reduce([np.isfinite(numeric[column]) for column in columns])
    if family is BinanceDataFamily.PREMIUM_INDEX_KLINES:
        return pd.Series(finite, index=numeric.index)
    positive = np.logical_and.reduce([numeric[column] > 0 for column in columns])
    return pd.Series(finite & positive, index=numeric.index)


def _non_negative(values: pd.Series) -> pd.Series:
    return np.isfinite(values) & (values >= 0)


def _first_existing(data: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    for candidate in candidates:
        if candidate in data.columns:
            return candidate
    return None


def _sidecar_prefix(family: BinanceDataFamily) -> str:
    if family is BinanceDataFamily.MARK_PRICE_KLINES:
        return "mark"
    if family is BinanceDataFamily.INDEX_PRICE_KLINES:
        return "index"
    if family is BinanceDataFamily.PREMIUM_INDEX_KLINES:
        return "premium"
    raise ValueError(f"{family} is not a kline sidecar family")


def _parse_year_month(value: str) -> date:
    try:
        parsed = datetime.strptime(value, "%Y-%m").date()
    except ValueError as exc:
        raise ValueError(f"invalid YYYY-MM month: {value!r}") from exc
    return parsed.replace(day=1)


def _month_start_datetime(value: str) -> datetime:
    parsed = _parse_year_month(value)
    return datetime(parsed.year, parsed.month, 1, tzinfo=UTC)


def _add_one_month(value: date) -> date:
    if value.month == DECEMBER:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _normalize_symbol(symbol: str) -> str:
    normalized = str(symbol).strip().upper()
    if not normalized:
        raise ValueError("symbol must not be empty")
    return normalized


__all__ = [
    "BINANCE_PUBLIC_DATA_BASE_URL",
    "HOUR_MS",
    "BinanceArchiveSpec",
    "BinanceDataFamily",
    "ChecksumVerification",
    "DownloadedArchive",
    "HistoricalDatasetError",
    "build_archive_plan",
    "download_archives",
    "expected_hourly_bars",
    "merge_symbol_data",
    "month_range",
    "normalize_archive_plan",
    "normalize_funding_frame",
    "normalize_kline_frame",
    "normalize_symbol_archive_files",
    "parse_checksum_text",
    "read_zip_csv",
    "sha256_file",
    "verify_checksum_file",
]
