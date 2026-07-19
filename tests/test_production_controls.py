"""Failure-mode + control tests for production risk controls (TASK-DEPLOY-001, Phase 5)."""

from __future__ import annotations

from src.research.production_controls import (
    SAFE_ACTION,
    RiskPolicy,
    data_quality_flags,
    evaluate_order,
    is_duplicate,
)

_POLICY = RiskPolicy()


def _clean_order(**over):
    base = {
        "symbol_exposure_after": 0.1,
        "gross_after": 0.9,
        "net_after": 0.1,
        "leverage_after": 1.0,
        "participation": 0.02,
        "symbol_dollar_volume": 50_000_000.0,
        "daily_turnover_after": 0.5,
        "margin_buffer": 0.5,
        "config_hash_ok": True,
        "exposure_matches_exchange": True,
        "data_flags": (),
        "policy": _POLICY,
    }
    base.update(over)
    return base


def test_clean_order_approved():
    r = evaluate_order(**_clean_order())
    assert r.approved is True
    assert r.violations == ()
    assert r.kill_switches == ()
    assert r.safe_action is None


def test_each_limit_rejects_when_breached():
    cases = {
        "max_exposure_per_symbol": {"symbol_exposure_after": 0.5},
        "max_participation": {"participation": 0.5},
        "min_liquidity": {"symbol_dollar_volume": 100.0},
        "max_gross_exposure": {"gross_after": 1.5},
        "max_net_exposure": {"net_after": 0.9},
        "max_leverage": {"leverage_after": 5.0},
        "max_daily_turnover": {"daily_turnover_after": 9.0},
    }
    for expected, over in cases.items():
        r = evaluate_order(**_clean_order(**over))
        assert expected in r.violations, expected
        assert r.approved is False


def test_kill_switch_config_hash_mismatch_halts_no_liquidation():
    r = evaluate_order(**_clean_order(config_hash_ok=False))
    assert "config_hash_mismatch" in r.kill_switches
    assert r.safe_action == SAFE_ACTION  # halt, NOT auto-liquidate
    assert r.approved is False


def test_kill_switch_margin_and_state_divergence():
    r = evaluate_order(**_clean_order(margin_buffer=0.1, exposure_matches_exchange=False))
    assert "margin_below_buffer" in r.kill_switches
    assert "local_state_divergence" in r.kill_switches


def test_critical_data_flag_trips_kill_switch():
    r = evaluate_order(**_clean_order(data_flags=("non_positive_price",)))
    assert "data_invalid:non_positive_price" in r.kill_switches
    assert r.safe_action == SAFE_ACTION


def test_noncritical_data_flag_does_not_kill():
    # incomplete_bar / missing_funding are flagged but not auto-kill by themselves
    r = evaluate_order(**_clean_order(data_flags=("incomplete_bar", "missing_funding")))
    assert r.kill_switches == ()


def test_data_quality_flags_detects_failure_modes():
    flags = data_quality_flags(
        bar_age_seconds=10_000,  # stale
        price=-1.0,  # non-positive
        reference_price=100.0,
        is_complete_bar=False,  # incomplete
        funding_present=False,  # missing funding
        spread_bps=250.0,  # abnormal
        policy=_POLICY,
    )
    for f in (
        "stale_data",
        "non_positive_price",
        "incomplete_bar",
        "missing_funding",
        "abnormal_spread",
    ):
        assert f in flags


def test_price_deviation_flag():
    flags = data_quality_flags(
        bar_age_seconds=0,
        price=140.0,
        reference_price=100.0,
        is_complete_bar=True,
        funding_present=True,
        spread_bps=5.0,
        policy=_POLICY,
    )
    assert "price_deviation" in flags  # 40% deviation > 20% cap


def test_clean_data_has_no_flags():
    flags = data_quality_flags(
        bar_age_seconds=60,
        price=100.0,
        reference_price=100.5,
        is_complete_bar=True,
        funding_present=True,
        spread_bps=3.0,
        policy=_POLICY,
    )
    assert flags == ()


def test_idempotency_dedup():
    emitted = {"abc", "def"}
    assert is_duplicate("abc", emitted) is True
    assert is_duplicate("xyz", emitted) is False
