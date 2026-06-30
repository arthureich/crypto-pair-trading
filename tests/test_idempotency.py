from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ledger.idempotency import (
    ObservationClassification,
    classify_exchange_observation,
    fill_reconciled_key,
    ledger_event_key,
    order_ack_unknown_key,
    order_acked_key,
    order_intent_created_key,
    order_sent_key,
    partial_fill_reconciled_key,
    reconciliation_observation_key,
)


def test_contract_event_keys_are_deterministic_and_match_expected_shapes() -> None:
    assert (
        order_intent_created_key(
            venue="binance",
            account_id="paper-main",
            strategy_id="pairs-v1",
            trade_id="trade-1",
            leg="A",
            phase="ENTRY",
            symbol="BTCUSDT",
            attempt=1,
        )
        == "ORDER_INTENT_CREATED:binance:paper-main:pairs-v1:trade-1:A:ENTRY:BTCUSDT:attempt-1"
    )
    assert (
        order_sent_key(
            client_order_id="coid.v1:binance:paper-main:pairs-v1:trade-1:A:ENTRY:BTCUSDT:1",
            send_attempt=1,
            side_effect_type="PLACE",
        )
        == "ORDER_SENT:coid.v1:binance:paper-main:pairs-v1:trade-1:A:ENTRY:BTCUSDT:1:1:PLACE"
    )
    assert (
        order_acked_key(
            venue="binance",
            account_id="paper-main",
            client_order_id="client-1",
            exchange_order_id="ex-1",
            ack_status="NEW",
        )
        == "ORDER_ACKED:binance:paper-main:client-1:ex-1:NEW"
    )
    assert (
        order_ack_unknown_key(
            venue="binance",
            account_id="paper-main",
            client_order_id="client-1",
            unknown_reason="REST_TIMEOUT",
        )
        == "ORDER_ACK_UNKNOWN:binance:paper-main:client-1:REST_TIMEOUT"
    )


def test_fill_keys_canonicalize_decimal_quantities_for_duplicate_observations() -> None:
    first = partial_fill_reconciled_key(
        venue="binance",
        account_id="paper-main",
        client_order_id="client-1",
        exchange_order_id="ex-1",
        exchange_cum_qty=Decimal("0.0500"),
    )
    second = partial_fill_reconciled_key(
        venue="binance",
        account_id="paper-main",
        client_order_id="client-1",
        exchange_order_id="ex-1",
        exchange_cum_qty="0.05",
    )

    assert first == second
    assert first == "PARTIAL_FILL_RECONCILED:binance:paper-main:client-1:ex-1:0.05"
    assert (
        fill_reconciled_key(
            venue="binance",
            account_id="paper-main",
            client_order_id="client-1",
            exchange_order_id="ex-1",
            exchange_cum_qty="1.000",
            terminal_order_status="FILLED",
        )
        == "FILL_RECONCILED:binance:paper-main:client-1:ex-1:1:FILLED"
    )


def test_generic_ledger_event_key_is_stable_across_mapping_field_order() -> None:
    left = ledger_event_key(
        "CUSTOM_EVENT",
        {
            "venue": "binance",
            "account_id": "paper-main",
            "trade_id": "trade-1",
        },
    )
    right = ledger_event_key(
        "CUSTOM_EVENT",
        {
            "trade_id": "trade-1",
            "venue": "binance",
            "account_id": "paper-main",
        },
    )

    assert left == right
    assert left == "CUSTOM_EVENT:account_id=paper-main:trade_id=trade-1:venue=binance"


def test_different_business_inputs_produce_different_keys() -> None:
    base = order_acked_key(
        venue="binance",
        account_id="paper-main",
        client_order_id="client-1",
        exchange_order_id="ex-1",
        ack_status="NEW",
    )
    different_status = order_acked_key(
        venue="binance",
        account_id="paper-main",
        client_order_id="client-1",
        exchange_order_id="ex-1",
        ack_status="REPLACED",
    )
    first_quantity = partial_fill_reconciled_key(
        venue="binance",
        account_id="paper-main",
        client_order_id="client-1",
        exchange_order_id="ex-1",
        exchange_cum_qty="0.05",
    )
    different_quantity = partial_fill_reconciled_key(
        venue="binance",
        account_id="paper-main",
        client_order_id="client-1",
        exchange_order_id="ex-1",
        exchange_cum_qty="0.06",
    )

    assert base != different_status
    assert first_quantity != different_quantity


def test_order_intent_attempt_and_slice_domains_do_not_collide() -> None:
    attempt_key = order_intent_created_key(
        venue="binance",
        account_id="paper-main",
        strategy_id="pairs-v1",
        trade_id="trade-1",
        leg="A",
        phase="ENTRY",
        symbol="BTCUSDT",
        attempt="slice-1",
    )
    slice_key = order_intent_created_key(
        venue="binance",
        account_id="paper-main",
        strategy_id="pairs-v1",
        trade_id="trade-1",
        leg="A",
        phase="ENTRY",
        symbol="BTCUSDT",
        slice_id="slice-1",
    )

    assert attempt_key.endswith(":attempt-slice-1")
    assert slice_key.endswith(":slice-slice-1")
    assert attempt_key != slice_key


def test_reconciliation_observation_key_is_router_free_and_order_stable() -> None:
    first = reconciliation_observation_key(
        venue="binance",
        account_id="paper-main",
        symbol="BTCUSDT",
        client_order_id="client-1",
        exchange_order_id="ex-1",
        exchange_cum_qty="0.0500",
        observation_status="PARTIALLY_FILLED",
    )
    second = reconciliation_observation_key(
        account_id="paper-main",
        venue="binance",
        symbol="BTCUSDT",
        exchange_order_id="ex-1",
        client_order_id="client-1",
        exchange_cum_qty=Decimal("0.05"),
        observation_status="PARTIALLY_FILLED",
    )

    assert first == second
    assert "observed_at" not in first
    assert "process" not in first


def test_classify_exchange_observation_duplicate_new_fill_and_regression() -> None:
    duplicate = classify_exchange_observation(
        venue="binance",
        account_id="paper-main",
        symbol="BTCUSDT",
        client_order_id="client-1",
        exchange_cum_qty="0.05",
        ledger_cum_qty=Decimal("0.0500"),
    )
    new_fill = classify_exchange_observation(
        venue="binance",
        account_id="paper-main",
        symbol="BTCUSDT",
        client_order_id="client-1",
        exchange_cum_qty="0.08",
        ledger_cum_qty="0.05",
    )
    regression = classify_exchange_observation(
        venue="binance",
        account_id="paper-main",
        symbol="BTCUSDT",
        client_order_id="client-1",
        exchange_cum_qty="0.04",
        ledger_cum_qty="0.05",
    )

    assert duplicate.classification is ObservationClassification.DUPLICATE
    assert duplicate.delta_fill == Decimal("0")
    assert new_fill.classification is ObservationClassification.NEW_FILL
    assert new_fill.delta_fill == Decimal("0.03")
    assert regression.classification is ObservationClassification.REGRESSION
    assert regression.delta_fill == Decimal("0")


@pytest.mark.parametrize(
    "call,match",
    [
        (
            lambda: order_acked_key(
                venue="binance",
                account_id="paper-main",
                client_order_id="",
                exchange_order_id="ex-1",
                ack_status="NEW",
            ),
            "field is required",
        ),
        (
            lambda: order_intent_created_key(
                venue="binance",
                account_id="paper-main",
                strategy_id="pairs-v1",
                trade_id="trade-1",
                leg="A",
                phase="ENTRY",
                symbol="BTCUSDT",
            ),
            "attempt or slice_id is required",
        ),
        (
            lambda: order_intent_created_key(
                venue="binance",
                account_id="paper-main",
                strategy_id="pairs-v1",
                trade_id="trade-1",
                leg="A",
                phase="ENTRY",
                symbol="BTCUSDT",
                attempt=1,
                slice_id="slice-1",
            ),
            "mutually exclusive",
        ),
        (
            lambda: reconciliation_observation_key(
                venue="binance",
                account_id="paper-main",
                symbol="BTCUSDT",
                exchange_cum_qty="0.05",
            ),
            "client_order_id or exchange_order_id is required",
        ),
        (
            lambda: partial_fill_reconciled_key(
                venue="binance",
                account_id="paper-main",
                client_order_id="client-1",
                exchange_order_id="ex-1",
                exchange_cum_qty="-1",
            ),
            "non-negative",
        ),
    ],
)
def test_invalid_or_missing_required_fields_raise_value_error(call, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        call()
