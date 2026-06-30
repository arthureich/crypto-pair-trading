"""Small in-memory cache for latest execution feature snapshots."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING

from src.features.execution_features import ExecutionFeatureReason

if TYPE_CHECKING:
    from src.features.execution_features import BookExecutionFeatures


class FeatureCacheReason(StrEnum):
    """Stable cache lookup reason codes."""

    HIT = "HIT"
    MISS = "MISS"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class FeatureCacheResult:
    """Feature cache lookup result."""

    symbol: str
    feature: BookExecutionFeatures | None
    reason: FeatureCacheReason

    @property
    def found(self) -> bool:
        return self.feature is not None

    @property
    def usable_for_trading(self) -> bool:
        return self.feature is not None and self.feature.usable_for_trading


class FeatureCache:
    """Latest-feature cache keyed by symbol, failing stale entries closed."""

    def __init__(self, *, max_age_ms: int) -> None:
        self._max_age_ms = _positive_int("max_age_ms", max_age_ms)
        self._features_by_symbol: dict[str, BookExecutionFeatures] = {}

    def store(self, feature: BookExecutionFeatures) -> None:
        symbol = _required_text("symbol", feature.symbol)
        self._features_by_symbol[symbol] = feature

    def latest(self, symbol: str, *, now_ms: int) -> FeatureCacheResult:
        normalized_symbol = _required_text("symbol", symbol)
        now = _non_negative_int("now_ms", now_ms)
        feature = self._features_by_symbol.get(normalized_symbol)
        if feature is None:
            return FeatureCacheResult(
                symbol=normalized_symbol,
                feature=None,
                reason=FeatureCacheReason.MISS,
            )
        if now < feature.generated_at_ms:
            raise ValueError("now_ms must be greater than or equal to feature.generated_at_ms")
        if now - feature.generated_at_ms > self._max_age_ms:
            return FeatureCacheResult(
                symbol=normalized_symbol,
                feature=replace(
                    feature,
                    usable_for_trading=False,
                    reason=ExecutionFeatureReason.STALE_BOOK,
                ),
                reason=FeatureCacheReason.STALE,
            )
        return FeatureCacheResult(
            symbol=normalized_symbol,
            feature=feature,
            reason=FeatureCacheReason.HIT,
        )


def _required_text(field_name: str, value: object) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _non_negative_int(field_name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _positive_int(field_name: str, value: int) -> int:
    integer = _non_negative_int(field_name, value)
    if integer <= 0:
        raise ValueError(f"{field_name} must be positive")
    return integer


__all__ = [
    "FeatureCache",
    "FeatureCacheReason",
    "FeatureCacheResult",
]
