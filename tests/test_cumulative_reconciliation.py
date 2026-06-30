from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution.client_order_id import ClientOrderIdInputs, build_client_order_id
from src.ledger.idempotency import (
    ObservationClassification,
    classify_exchange_observation,
    fill_reconciled_key,
    order_intent_created_key,
    order_sent_key,
    partial_fill_reconciled_key,
)
from src.reconciliation import CumulativeFillStatus, reconcile_cumulative_fill


def test_partial_fill_returns_positive_delta_and_new_ledger_cumulative() -> None:
    result = reconcile_cumulative_fill(
        exchange_cum_qty=Decimal("0.05"),
        ledger_cum_qty=Decimal("0.03"),
    )

    assert result.status is CumulativeFillStatus.NEW_FILL
    assert result.delta_fill == Decimal("0.02")
    assert result.ledger_cum_qty_after == Decimal("0.05")
    assert result.increases_position is True


def test_duplicate_cumulative_observation_returns_zero_delta() -> None:
    result = reconcile_cumulative_fill(
        exchange_cum_qty=Decimal("1.25"),
        ledger_cum_qty=Decimal("1.25"),
    )

    assert result.status is CumulativeFillStatus.DUPLICATE
    assert result.delta_fill == Decimal("0")
    assert result.ledger_cum_qty_after == Decimal("1.25")
    assert result.is_duplicate_observation is True
    assert result.increases_position is False


def test_sprint3_duplicate_fill_observations_do_not_duplicate_position_delta() -> None:
    client_order = build_client_order_id(
        ClientOrderIdInputs(
            venue="BINANCE",
            account_id="paper-main",
            strategy_id="pairs-v1",
            trade_id="trade-1",
            leg="A",
            phase="ENTRY",
            symbol="BTCUSDT",
            attempt=1,
        )
    )
    intent_key = order_intent_created_key(
        venue="BINANCE",
        account_id="paper-main",
        strategy_id="pairs-v1",
        trade_id="trade-1",
        leg="A",
        phase="ENTRY",
        symbol="BTCUSDT",
        attempt=1,
    )
    sent_key = order_sent_key(
        client_order_id=client_order.client_order_id,
        send_attempt=1,
        side_effect_type="PLACE",
    )

    assert client_order.client_order_id in sent_key
    assert intent_key == (
        "ORDER_INTENT_CREATED:BINANCE:paper-main:pairs-v1:trade-1:A:ENTRY:BTCUSDT:attempt-1"
    )

    ledger_cum_qty = Decimal("0")
    position_delta = Decimal("0")
    observations = (
        ("0.50", "PARTIALLY_FILLED"),
        (Decimal("0.5000"), "PARTIALLY_FILLED"),
        ("1.00", "FILLED"),
        (Decimal("1.0000"), "FILLED"),
    )

    decisions = []
    results = []
    for exchange_cum_qty, observation_status in observations:
        result = reconcile_cumulative_fill(
            exchange_cum_qty=exchange_cum_qty,
            ledger_cum_qty=ledger_cum_qty,
        )
        decision = classify_exchange_observation(
            venue="BINANCE",
            account_id="paper-main",
            symbol="BTCUSDT",
            client_order_id=client_order.client_order_id,
            exchange_order_id="ex-1",
            exchange_cum_qty=exchange_cum_qty,
            ledger_cum_qty=ledger_cum_qty,
            observation_status=observation_status,
        )

        position_delta += result.delta_fill
        ledger_cum_qty = result.ledger_cum_qty_after
        results.append(result)
        decisions.append(decision)

    assert [result.status for result in results] == [
        CumulativeFillStatus.NEW_FILL,
        CumulativeFillStatus.DUPLICATE,
        CumulativeFillStatus.NEW_FILL,
        CumulativeFillStatus.DUPLICATE,
    ]
    assert [decision.classification for decision in decisions] == [
        ObservationClassification.NEW_FILL,
        ObservationClassification.DUPLICATE,
        ObservationClassification.NEW_FILL,
        ObservationClassification.DUPLICATE,
    ]
    assert [result.delta_fill for result in results] == [
        Decimal("0.50"),
        Decimal("0"),
        Decimal("0.50"),
        Decimal("0"),
    ]
    assert position_delta == Decimal("1.00")
    assert ledger_cum_qty == Decimal("1.00")
    assert decisions[0].idempotency_key == decisions[1].idempotency_key
    assert decisions[2].idempotency_key == decisions[3].idempotency_key
    assert partial_fill_reconciled_key(
        venue="BINANCE",
        account_id="paper-main",
        client_order_id=client_order.client_order_id,
        exchange_order_id="ex-1",
        exchange_cum_qty="0.50",
    ) == partial_fill_reconciled_key(
        venue="BINANCE",
        account_id="paper-main",
        client_order_id=client_order.client_order_id,
        exchange_order_id="ex-1",
        exchange_cum_qty=Decimal("0.5000"),
    )
    assert fill_reconciled_key(
        venue="BINANCE",
        account_id="paper-main",
        client_order_id=client_order.client_order_id,
        exchange_order_id="ex-1",
        exchange_cum_qty="1.00",
        terminal_order_status="FILLED",
    ) == fill_reconciled_key(
        venue="BINANCE",
        account_id="paper-main",
        client_order_id=client_order.client_order_id,
        exchange_order_id="ex-1",
        exchange_cum_qty=Decimal("1.0000"),
        terminal_order_status="FILLED",
    )


def test_lower_out_of_order_observation_is_flagged_without_negative_delta() -> None:
    result = reconcile_cumulative_fill(
        exchange_cum_qty=Decimal("0.40"),
        ledger_cum_qty=Decimal("0.75"),
    )

    assert result.status is CumulativeFillStatus.LOWER_THAN_LEDGER
    assert result.delta_fill == Decimal("0")
    assert result.ledger_cum_qty_after == Decimal("0.75")
    assert result.is_inconsistent_regression is True
    assert result.increases_position is False


def test_exact_zero_observation_is_idempotent_and_does_not_increase_position() -> None:
    result = reconcile_cumulative_fill(exchange_cum_qty="0", ledger_cum_qty="0")

    assert result.status is CumulativeFillStatus.EXACT_ZERO
    assert result.exchange_cum_qty == Decimal("0")
    assert result.ledger_cum_qty == Decimal("0")
    assert result.delta_fill == Decimal("0")
    assert result.ledger_cum_qty_after == Decimal("0")
    assert result.is_duplicate_observation is True
    assert result.increases_position is False


def test_decimal_precision_has_no_float_drift() -> None:
    result = reconcile_cumulative_fill(
        exchange_cum_qty=Decimal("0.3000000000000000000000000001"),
        ledger_cum_qty=Decimal("0.1"),
    )

    assert result.delta_fill == Decimal("0.2000000000000000000000000001")
    assert result.ledger_cum_qty_after == Decimal("0.3000000000000000000000000001")


def test_float_inputs_are_rejected_to_preserve_decimal_safety() -> None:
    with pytest.raises(TypeError, match="must not be float"):
        reconcile_cumulative_fill(exchange_cum_qty=0.3, ledger_cum_qty=Decimal("0.1"))  # type: ignore


def test_negative_quantities_are_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        reconcile_cumulative_fill(exchange_cum_qty=Decimal("-0.01"), ledger_cum_qty=0)
