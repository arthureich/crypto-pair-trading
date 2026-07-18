"""Tests for the immutable append-only forward ledger (TASK-DEPLOY-001, Phase 2).

Covers: deterministic decision ids, idempotent replay, append-only immutability
(overwrite with different content raises), the correction flow (new event, original
untouched), read round-trip, and the three-stream P&L accounting.
"""

from __future__ import annotations

import math

import pytest

from src.research.forward_ledger import (
    DecisionEvent,
    ForwardLedger,
    LedgerImmutabilityError,
    make_decision_id,
    three_stream_pnl,
)


def _event(**over) -> DecisionEvent:
    base = {
        "decision_id": "",
        "strategy_config_hash": "ba5037fc",
        "software_commit": "416c6a0",
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "signal_timestamp_ms": 1_700_000_000_000,
        "side": "long",
        "target_weight": 0.1,
        "gross_pnl": 0.02,
        "net_pnl_theoretical": 0.019,
        "net_pnl_executable": 0.017,
        "net_pnl_conservative": 0.008,
    }
    base.update(over)
    if not base["decision_id"]:
        base["decision_id"] = make_decision_id(
            base["strategy_config_hash"],
            base["exchange"],
            base["symbol"],
            base["signal_timestamp_ms"],
        )
    return DecisionEvent(**base)


def test_decision_id_deterministic_and_sensitive():
    a = make_decision_id("h", "binance", "BTCUSDT", 1000)
    b = make_decision_id("h", "binance", "BTCUSDT", 1000)
    c = make_decision_id("h", "binance", "ETHUSDT", 1000)
    assert a == b
    assert a != c


def test_three_stream_ordering_and_formula():
    s = three_stream_pnl(
        0.02,
        declared_cost=0.001,
        execution_frictions=0.003,
        conservative_risk_fraction=0.5,
        conservative_extra_drag=0.0005,
    )
    assert math.isclose(s.theoretical, 0.019)
    assert math.isclose(s.executable, 0.017)
    assert math.isclose(s.conservative, 0.5 * 0.017 - 0.0005)
    # executable is worse than theoretical when frictions exceed the declared cost
    assert s.executable < s.theoretical


def test_three_stream_rejects_bad_risk_fraction():
    with pytest.raises(ValueError, match="risk_fraction"):
        three_stream_pnl(
            0.01, declared_cost=0.0, execution_frictions=0.0, conservative_risk_fraction=0.0
        )


def test_append_and_read_roundtrip(tmp_path):
    led = ForwardLedger(tmp_path / "ledger.jsonl")
    assert led.append(_event()) is True
    rows = led.read_all()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["event_type"] == "decision"


def test_idempotent_replay_is_noop(tmp_path):
    led = ForwardLedger(tmp_path / "ledger.jsonl")
    ev = _event()
    assert led.append(ev) is True
    assert led.append(ev) is False  # identical replay -> no-op
    assert len(led.read_all()) == 1


def test_overwrite_with_different_content_raises(tmp_path):
    led = ForwardLedger(tmp_path / "ledger.jsonl")
    ev = _event()
    led.append(ev)
    mutated = _event(gross_pnl=0.99)  # same id (same key), different content
    assert mutated.decision_id == ev.decision_id
    with pytest.raises(LedgerImmutabilityError, match="append-only"):
        led.append(mutated)
    assert len(led.read_all()) == 1  # original untouched


def test_correction_is_new_event_original_preserved(tmp_path):
    led = ForwardLedger(tmp_path / "ledger.jsonl")
    ev = _event()
    led.append(ev)
    corrected = _event(
        corrects_decision_id=ev.decision_id, gross_pnl=0.03, net_pnl_executable=0.028
    )
    corr_id = led.append_correction(corrected, reason="funding restated by exchange")
    rows = led.read_all()
    assert len(rows) == 2
    original = next(r for r in rows if r["decision_id"] == ev.decision_id)
    correction = next(r for r in rows if r["decision_id"] == corr_id)
    assert original["gross_pnl"] == 0.02  # original NOT modified
    assert original["event_type"] == "decision"
    assert correction["event_type"] == "correction"
    assert correction["corrects_decision_id"] == ev.decision_id
    assert correction["correction_reason"] == "funding restated by exchange"


def test_correction_requires_existing_original(tmp_path):
    led = ForwardLedger(tmp_path / "ledger.jsonl")
    orphan = _event(corrects_decision_id="does-not-exist")
    with pytest.raises(LedgerImmutabilityError, match="existing original"):
        led.append_correction(orphan, reason="x")


def test_append_rejects_correction_type(tmp_path):
    led = ForwardLedger(tmp_path / "ledger.jsonl")
    ev = _event(event_type="correction")
    with pytest.raises(LedgerImmutabilityError, match="append_correction"):
        led.append(ev)


def test_flags_persist_as_lists(tmp_path):
    led = ForwardLedger(tmp_path / "ledger.jsonl")
    led.append(_event(data_quality_flags=("stale_funding",), execution_flags=("partial_fill",)))
    row = led.read_all()[0]
    assert row["data_quality_flags"] == ["stale_funding"]
    assert row["execution_flags"] == ["partial_fill"]
