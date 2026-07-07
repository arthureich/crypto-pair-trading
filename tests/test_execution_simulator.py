from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import execution_simulator  # noqa: E402
from src.backtest.execution_simulator import (  # noqa: E402
    ExecutionSimulatorError,
    ExecutionStyle,
    TradeStatus,
    _simulate_leg_fill,
    simulate_round_trip_trade,
)
from src.backtest.fill_model import FillModelConfig, TopOfBookQuote  # noqa: E402
from src.execution.slippage_estimator import SlippageSide  # noqa: E402

HOUR_MS = 60 * 60 * 1000


def _quote(
    t: int, bid: float, ask: float, bid_qty: float = 10.0, ask_qty: float = 10.0
) -> TopOfBookQuote:
    return TopOfBookQuote(
        event_time=t, best_bid=bid, best_ask=ask, best_bid_qty=bid_qty, best_ask_qty=ask_qty
    )


def _intent(
    *,
    side_a: str = "SELL",
    side_b: str = "BUY",
    beta: float = 1.0,
    target_notional: float = 1_000.0,
    created_at: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        signal_id="S9-TEST-0-SHORT_SPREAD",
        pair="ARBUSDT/OPUSDT",
        symbol_a="ARBUSDT",
        symbol_b="OPUSDT",
        side_a=side_a,
        side_b=side_b,
        target_notional=target_notional,
        zscore=2.5,
        beta=beta,
        half_life_hours=12.0,
        expected_edge_bps=5.0,
        created_at=created_at,
        expires_at=created_at + HOUR_MS,
        barrier_policy_id="TEST_BARRIER",
    )


def test_round_trip_executes_with_full_fills_both_legs() -> None:
    intent = _intent()
    quotes_a = [
        _quote(0, 10.0, 10.01, bid_qty=1_000.0, ask_qty=1_000.0),
        _quote(HOUR_MS, 9.9, 9.91, bid_qty=1_000.0, ask_qty=1_000.0),
    ]
    quotes_b = [
        _quote(0, 5.0, 5.005, bid_qty=1_000.0, ask_qty=1_000.0),
        _quote(HOUR_MS, 5.05, 5.06, bid_qty=1_000.0, ask_qty=1_000.0),
    ]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    result = simulate_round_trip_trade(intent, quotes_a=quotes_a, quotes_b=quotes_b, config=config)

    assert result.status is TradeStatus.EXECUTED
    assert result.entry_fill_a.filled_quantity > 0.0
    assert result.entry_fill_b.filled_quantity > 0.0
    assert result.exit_fill_a is not None
    assert result.exit_fill_b is not None
    assert result.leg_fill_mismatch is False
    assert result.exit_delayed_by_ack_unknown_ms == 0


def test_round_trip_weights_leg_b_quantity_by_beta() -> None:
    intent = _intent(beta=2.0, target_notional=1_000.0)
    quotes_a = [_quote(0, 10.0, 10.0), _quote(HOUR_MS, 10.0, 10.0)]
    quotes_b = [_quote(0, 5.0, 5.0), _quote(HOUR_MS, 5.0, 5.0)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    result = simulate_round_trip_trade(intent, quotes_a=quotes_a, quotes_b=quotes_b, config=config)

    # leg A: 1000 / 10.0 = 100 units; leg B: beta(2.0) * 1000 / 5.0 = 400 units
    assert result.entry_fill_a.requested_quantity == pytest.approx(100.0)
    assert result.entry_fill_b.requested_quantity == pytest.approx(400.0)


def test_round_trip_flags_leg_fill_mismatch_on_partial_fill() -> None:
    intent = _intent()
    quotes_a = [_quote(0, 10.0, 10.01, ask_qty=1.0), _quote(HOUR_MS, 9.9, 9.91)]
    quotes_b = [_quote(0, 5.0, 5.005, bid_qty=1_000.0), _quote(HOUR_MS, 5.05, 5.06)]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    result = simulate_round_trip_trade(intent, quotes_a=quotes_a, quotes_b=quotes_b, config=config)

    assert result.leg_fill_mismatch is True


def test_round_trip_pnl_includes_partially_filled_leg_not_just_the_full_leg() -> None:
    """Regression: a partially-filled leg must still contribute real PnL.

    Before this was fixed, a partial fill's average_price came back as None
    (see tests/test_fill_model.py), which made execution_simulator's
    _leg_pnl_quote bail out to 0.0 for that leg -- silently dropping half a
    round trip's economics whenever either leg didn't fully fill.
    """

    intent = _intent(side_a="BUY", side_b="SELL")
    quotes_a = [
        _quote(0, 10.0, 10.01, ask_qty=1.0),
        _quote(HOUR_MS, 9.0, 9.01, bid_qty=1.0),
    ]
    quotes_b = [
        _quote(0, 5.0, 5.005, bid_qty=1_000.0, ask_qty=1_000.0),
        _quote(HOUR_MS, 5.0, 5.005, bid_qty=1_000.0, ask_qty=1_000.0),
    ]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    result = simulate_round_trip_trade(intent, quotes_a=quotes_a, quotes_b=quotes_b, config=config)

    assert result.entry_fill_a.status.value == "PARTIALLY_FILLED"
    assert result.entry_fill_a.average_price is not None
    assert result.exit_fill_a is not None
    assert result.exit_fill_a.average_price is not None
    # Leg A alone (BUY at ~10.01, SELL at ~9.0 on only 1.0 unit) is a large
    # realized loss; it must show up in net_pnl_quote, not be zeroed out.
    assert result.net_pnl_quote < -0.5


def test_round_trip_reports_no_entry_fill_without_reference_quote() -> None:
    intent = _intent(created_at=HOUR_MS)
    quotes_a = [_quote(2 * HOUR_MS, 10.0, 10.01)]
    quotes_b = [_quote(2 * HOUR_MS, 5.0, 5.005)]

    result = simulate_round_trip_trade(intent, quotes_a=quotes_a, quotes_b=quotes_b)

    assert result.status is TradeStatus.NO_ENTRY_FILL
    assert result.net_pnl_quote == 0.0


def test_ack_unknown_entry_delays_the_exit_decision_time() -> None:
    intent = _intent()
    reconciliation_latency_ms = HOUR_MS + 10 * 60_000
    quotes_a = [_quote(t, 10.0, 10.01) for t in range(0, 3 * HOUR_MS, HOUR_MS // 4)]
    quotes_b = [_quote(t, 5.0, 5.005) for t in range(0, 3 * HOUR_MS, HOUR_MS // 4)]
    config = FillModelConfig(
        latency_ms=0,
        ack_unknown_rate=1.0,
        reconciliation_latency_ms=reconciliation_latency_ms,
    )

    result = simulate_round_trip_trade(intent, quotes_a=quotes_a, quotes_b=quotes_b, config=config)

    assert result.exit_delayed_by_ack_unknown_ms >= 10 * 60_000
    assert result.exit_fill_a is not None
    assert result.exit_fill_a.decision_time >= intent.created_at + reconciliation_latency_ms


def test_invalid_target_notional_fails_closed() -> None:
    intent = _intent(target_notional=-5.0)
    with pytest.raises(ExecutionSimulatorError):
        simulate_round_trip_trade(
            intent,
            quotes_a=[_quote(0, 10.0, 10.01)],
            quotes_b=[_quote(0, 5.0, 5.005)],
        )


def test_execution_simulator_does_not_import_live_planes() -> None:
    source = inspect.getsource(execution_simulator)

    forbidden_imports = ("src.ledger", "src.live", "src.recovery", "src.risk.execution_risk_gate")
    assert all(forbidden not in source for forbidden in forbidden_imports)


def test_default_execution_style_is_market_ioc_unchanged_from_sprint_9() -> None:
    intent = _intent()
    quotes_a = [
        _quote(0, 10.0, 10.01, bid_qty=1_000.0, ask_qty=1_000.0),
        _quote(HOUR_MS, 9.9, 9.91, bid_qty=1_000.0, ask_qty=1_000.0),
    ]
    quotes_b = [
        _quote(0, 5.0, 5.005, bid_qty=1_000.0, ask_qty=1_000.0),
        _quote(HOUR_MS, 5.05, 5.06, bid_qty=1_000.0, ask_qty=1_000.0),
    ]
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    default_result = simulate_round_trip_trade(
        intent, quotes_a=quotes_a, quotes_b=quotes_b, config=config
    )
    explicit_result = simulate_round_trip_trade(
        intent,
        quotes_a=quotes_a,
        quotes_b=quotes_b,
        config=config,
        execution_style=ExecutionStyle.MARKET_IOC,
    )

    assert default_result.net_pnl_quote == pytest.approx(explicit_result.net_pnl_quote)
    assert default_result.entry_fill_a.order_type.value == "MARKET_IOC"


def test_limit_maker_ttl_entry_never_crosses_at_placement_only_fills_when_market_crosses() -> None:
    """Passive orders must earn the spread, not pay it, when they do fill."""

    intent = _intent(side_a="BUY", side_b="SELL")
    quotes_a = [
        _quote(0, 10.0, 10.02, bid_qty=1_000.0, ask_qty=1_000.0),
        _quote(500, 9.98, 9.99, bid_qty=1_000.0, ask_qty=1_000.0),
    ]
    quotes_b = [
        _quote(0, 5.0, 5.02, bid_qty=1_000.0, ask_qty=1_000.0),
        _quote(500, 5.03, 5.05, bid_qty=1_000.0, ask_qty=1_000.0),
    ]
    config = FillModelConfig(latency_ms=0, limit_ttl_ms=5_000, ack_unknown_rate=0.0)

    result = simulate_round_trip_trade(
        intent,
        quotes_a=quotes_a,
        quotes_b=quotes_b,
        config=config,
        execution_style=ExecutionStyle.LIMIT_MAKER_TTL,
    )

    assert result.entry_fill_a.order_type.value == "LIMIT"
    assert result.entry_fill_a.status.value == "FILLED"
    assert result.entry_fill_a.average_price == pytest.approx(10.0)
    assert result.entry_fill_b.order_type.value == "LIMIT"
    assert result.entry_fill_b.status.value == "FILLED"
    assert result.entry_fill_b.average_price == pytest.approx(5.02)


def test_limit_maker_ttl_expires_when_market_never_crosses_within_ttl() -> None:
    intent = _intent(side_a="BUY", side_b="SELL")
    quotes_a = [_quote(0, 10.0, 10.02, bid_qty=1_000.0, ask_qty=1_000.0)]
    quotes_b = [_quote(0, 5.0, 5.02, bid_qty=1_000.0, ask_qty=1_000.0)]
    config = FillModelConfig(latency_ms=0, limit_ttl_ms=1_000, ack_unknown_rate=0.0)

    result = simulate_round_trip_trade(
        intent,
        quotes_a=quotes_a,
        quotes_b=quotes_b,
        config=config,
        execution_style=ExecutionStyle.LIMIT_MAKER_TTL,
    )

    assert result.status is TradeStatus.NO_ENTRY_FILL
    assert result.entry_fill_a.status.value == "EXPIRED"
    assert result.entry_fill_b.status.value == "EXPIRED"
    assert result.net_pnl_quote == 0.0


def test_simulate_leg_fill_limit_maker_ttl_fails_closed_without_a_quote() -> None:
    config = FillModelConfig(latency_ms=0, ack_unknown_rate=0.0)

    outcome = _simulate_leg_fill(
        order_id="leg-no-quote",
        side=SlippageSide.BUY,
        quantity=1.0,
        quotes=[],
        decision_time=1_000,
        config=config,
        execution_style=ExecutionStyle.LIMIT_MAKER_TTL,
        market_reference_price=None,
    )

    assert outcome.status.value == "NO_QUOTE"
    assert outcome.filled_quantity == 0.0
