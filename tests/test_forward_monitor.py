"""Tests for the forward monitor (TASK-DEPLOY-001, Phase 7)."""

from __future__ import annotations

import numpy as np

from src.research.forward_monitor import (
    AlertThresholds,
    evaluate_alerts,
    reading_horizon,
    stream_metrics,
)


def test_reading_horizon_gates_verdict():
    assert reading_horizon(5)["reading_level"] == "operational_diagnostic_only"
    assert reading_horizon(5)["verdict_horizon_reached"] is False
    assert reading_horizon(20)["reading_level"] == "preliminary"
    assert reading_horizon(40)["reading_level"] == "initial_evidence"
    assert reading_horizon(80)["verdict_horizon_reached"] is True  # ~13 months
    assert reading_horizon(150)["reading_level"] == "more_confident_assessment"


def test_stream_metrics_basic():
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.02, size=200)
    m = stream_metrics(r)
    assert m["n"] == 200
    assert m["sharpe"] is not None
    assert 0.0 <= m["hit_rate"] <= 1.0
    assert m["max_drawdown_compounded_pct"] is not None


def test_stream_metrics_too_few():
    m = stream_metrics([0.01])
    assert m["sharpe"] is None
    assert m["n"] == 1


def test_no_alerts_when_healthy():
    healthy = {"sharpe": 0.95, "max_drawdown_compounded_pct": 30.0, "hit_rate": 0.55}
    alerts = evaluate_alerts(
        theoretical={"sharpe": 0.97},
        executable=healthy,
        effective_cost_bps=7.0,
        max_single_rebalance_share=0.2,
        config_hash_ok=True,
        data_failure_count=0,
        exposure_matches_config=True,
    )
    assert alerts == ()


def test_execution_shortfall_alert():
    alerts = evaluate_alerts(
        theoretical={"sharpe": 1.0},
        executable={"sharpe": 0.5, "max_drawdown_compounded_pct": 30.0, "hit_rate": 0.55},
        effective_cost_bps=7.0,
        max_single_rebalance_share=0.2,
        config_hash_ok=True,
        data_failure_count=0,
        exposure_matches_config=True,
    )
    assert "execution_shortfall_exceeds_budget" in alerts


def test_drawdown_and_hitrate_and_concentration_alerts():
    alerts = evaluate_alerts(
        theoretical={"sharpe": 0.9},
        executable={"sharpe": 0.85, "max_drawdown_compounded_pct": 70.0, "hit_rate": 0.30},
        effective_cost_bps=200.0,
        max_single_rebalance_share=0.9,
        config_hash_ok=True,
        data_failure_count=0,
        exposure_matches_config=True,
    )
    assert "drawdown_beyond_historical" in alerts
    assert "hit_rate_persistent_drop" in alerts
    assert "pnl_concentration" in alerts
    assert "cost_above_breakeven" in alerts


def test_config_and_state_alerts():
    alerts = evaluate_alerts(
        theoretical={"sharpe": 0.9},
        executable={"sharpe": 0.9, "max_drawdown_compounded_pct": 30.0, "hit_rate": 0.55},
        effective_cost_bps=7.0,
        max_single_rebalance_share=0.2,
        config_hash_ok=False,
        data_failure_count=3,
        exposure_matches_config=False,
    )
    assert "config_hash_mismatch" in alerts
    assert "recurring_data_failures" in alerts
    assert "exposure_differs_from_frozen_config" in alerts


def test_custom_thresholds_respected():
    t = AlertThresholds()
    t.historical_max_drawdown_pct = 20.0  # stricter
    alerts = evaluate_alerts(
        theoretical={"sharpe": 0.9},
        executable={"sharpe": 0.9, "max_drawdown_compounded_pct": 30.0, "hit_rate": 0.55},
        effective_cost_bps=7.0,
        max_single_rebalance_share=0.2,
        config_hash_ok=True,
        data_failure_count=0,
        exposure_matches_config=True,
        thresholds=t,
    )
    assert "drawdown_beyond_historical" in alerts
