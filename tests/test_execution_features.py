from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features import (
    BookLevel,
    ExecutionFeatureReason,
    build_book_execution_features,
    depth_within_bps,
    mid_price,
    order_book_imbalance,
    spread_bps,
    update_volatility,
)
from src.market_data import (
    BookHealthDecision,
    BookHealthReason,
    BookHealthStatus,
    FeatureCache,
    FeatureCacheReason,
    SnapshotEvidence,
    decide_snapshot_resync,
)


def _healthy_book(age_ms: int | None = 42) -> BookHealthDecision:
    return BookHealthDecision(
        status=BookHealthStatus.HEALTHY,
        reason=BookHealthReason.IN_SEQUENCE,
        venue="BINANCE",
        symbol="BTCUSDT",
        last_sequence=10,
        entry_eligible=True,
        age_ms=age_ms,
    )


def _bids() -> tuple[BookLevel, ...]:
    return (
        BookLevel("99.96", "2"),
        BookLevel("99.94", "3"),
        BookLevel("99.00", "10"),
    )


def _asks() -> tuple[BookLevel, ...]:
    return (
        BookLevel("100.04", "1"),
        BookLevel("100.06", "4"),
        BookLevel("101.00", "10"),
    )


def test_mid_price_and_spread_bps_are_correct() -> None:
    assert mid_price(best_bid="99", best_ask="101") == Decimal("100")
    assert spread_bps(best_bid="99", best_ask="101") == Decimal("200")


def test_depth_within_5bps_and_10bps_is_computed_on_both_sides() -> None:
    depth_5 = depth_within_bps(_bids(), _asks(), mid_price="100", bps="5")
    depth_10 = depth_within_bps(_bids(), _asks(), mid_price="100", bps="10")

    assert depth_5.bid_quantity == Decimal("2")
    assert depth_5.ask_quantity == Decimal("1")
    assert depth_5.bid_notional == Decimal("199.92")
    assert depth_5.ask_notional == Decimal("100.04")
    assert depth_10.bid_quantity == Decimal("5")
    assert depth_10.ask_quantity == Decimal("5")


def test_order_book_imbalance_is_deterministic() -> None:
    first = order_book_imbalance(_bids(), _asks())
    second = order_book_imbalance(reversed(_bids()), reversed(_asks()))

    assert first == second
    assert first == Decimal("0")


def test_book_execution_features_model_is_usable_for_healthy_book() -> None:
    features = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=_bids(),
        asks=_asks(),
        generated_at_ms=1_000,
        book_health=_healthy_book(),
    )

    assert features.mid_price == Decimal("100.00")
    assert features.spread_bps == Decimal("8.00")
    assert features.depth_5_bps.bid_quantity == Decimal("2")
    assert features.depth_10_bps.ask_quantity == Decimal("5")
    assert features.book_age_ms == 42
    assert features.in_sync is True
    assert features.usable_for_trading is True
    assert features.reason is ExecutionFeatureReason.USABLE


def test_invalid_stale_or_resync_required_evidence_is_unusable_for_trading() -> None:
    invalid = BookHealthDecision(
        status=BookHealthStatus.INVALID,
        reason=BookHealthReason.SEQUENCE_GAP,
        venue="BINANCE",
        symbol="BTCUSDT",
        last_sequence=10,
        entry_eligible=False,
        age_ms=10,
    )
    stale = BookHealthDecision(
        status=BookHealthStatus.INVALID,
        reason=BookHealthReason.STALE_BOOK,
        venue="BINANCE",
        symbol="BTCUSDT",
        last_sequence=10,
        entry_eligible=False,
        age_ms=251,
    )
    stale_features = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=_bids(),
        asks=_asks(),
        generated_at_ms=1_000,
        book_health=stale,
    )
    invalid_features = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=_bids(),
        asks=_asks(),
        generated_at_ms=1_000,
        book_health=invalid,
    )
    resync = decide_snapshot_resync(
        SnapshotEvidence(
            venue="BINANCE",
            symbol="BTCUSDT",
            snapshot_complete=True,
            local_last_sequence=10,
            snapshot_last_sequence=9,
        )
    )
    resync_features = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=_bids(),
        asks=_asks(),
        generated_at_ms=1_000,
        book_health=_healthy_book(),
        snapshot_resync=resync,
    )

    assert invalid_features.usable_for_trading is False
    assert invalid_features.in_sync is False
    assert invalid_features.book_age_ms == 10
    assert invalid_features.reason is ExecutionFeatureReason.INVALID_BOOK
    assert stale_features.usable_for_trading is False
    assert stale_features.in_sync is False
    assert stale_features.book_age_ms == 251
    assert stale_features.reason is ExecutionFeatureReason.STALE_BOOK
    assert resync_features.usable_for_trading is False
    assert resync_features.in_sync is False
    assert resync_features.book_age_ms == 42
    assert resync_features.reason is ExecutionFeatureReason.RESYNC_REQUIRED


def test_zero_quantity_levels_do_not_become_best_bid_or_ask() -> None:
    features = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=(BookLevel("101", "0"), BookLevel("99", "2")),
        asks=(BookLevel("99.5", "0"), BookLevel("101", "3")),
        generated_at_ms=1_000,
        book_health=_healthy_book(),
    )

    assert features.usable_for_trading is True
    assert features.in_sync is True
    assert features.best_bid == Decimal("99")
    assert features.best_ask == Decimal("101")
    assert features.mid_price == Decimal("100")


def test_all_zero_quantity_book_is_unusable_for_trading() -> None:
    features = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=(BookLevel("99", "0"),),
        asks=(BookLevel("101", "0"),),
        generated_at_ms=1_000,
        book_health=_healthy_book(),
    )

    assert features.usable_for_trading is False
    assert features.in_sync is False
    assert features.book_age_ms == 42
    assert features.reason is ExecutionFeatureReason.CROSSED_OR_EMPTY_BOOK
    assert features.best_bid is None
    assert features.best_ask is None


def test_malformed_book_levels_fail_closed_without_exception() -> None:
    features = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=(BookLevel("-99", "1"),),
        asks=(BookLevel("101", "1"),),
        generated_at_ms=1_000,
        book_health=_healthy_book(),
    )

    assert features.usable_for_trading is False
    assert features.in_sync is False
    assert features.book_age_ms == 42
    assert features.reason is ExecutionFeatureReason.INVALID_BOOK
    assert features.mid_price is None


def test_volatility_updates_without_future_data_and_prunes_to_5s_window() -> None:
    first = update_volatility(None, mid_price="100", observed_at_ms=1_000)
    second = update_volatility(first.state, mid_price="101", observed_at_ms=1_500)
    third = update_volatility(second.state, mid_price="99", observed_at_ms=6_500)

    assert first.volatility_1s == Decimal("0")
    assert second.volatility_1s == Decimal("0.01")
    assert third.volatility_5s > 0
    assert tuple(obs.observed_at_ms for obs in third.state.observations) == (1_500, 6_500)
    with pytest.raises(ValueError, match="must not move backward"):
        update_volatility(third.state, mid_price="100", observed_at_ms=6_000)


def test_feature_cache_returns_latest_and_marks_stale_fail_closed() -> None:
    feature = build_book_execution_features(
        venue="BINANCE",
        symbol="BTCUSDT",
        bids=_bids(),
        asks=_asks(),
        generated_at_ms=1_000,
        book_health=_healthy_book(),
    )
    cache = FeatureCache(max_age_ms=500)

    assert cache.latest("BTCUSDT", now_ms=1_000).reason is FeatureCacheReason.MISS
    cache.store(feature)

    fresh = cache.latest("BTCUSDT", now_ms=1_500)
    stale = cache.latest("BTCUSDT", now_ms=1_501)

    assert fresh.reason is FeatureCacheReason.HIT
    assert fresh.usable_for_trading is True
    assert fresh.feature is not None
    assert fresh.feature.in_sync is True
    assert stale.reason is FeatureCacheReason.STALE
    assert stale.feature is not None
    assert stale.feature.usable_for_trading is False
    assert stale.feature.in_sync is False
    assert stale.feature.book_age_ms == 42
    assert stale.feature.reason is ExecutionFeatureReason.STALE_BOOK
