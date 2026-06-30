from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution.client_order_id import (
    CLIENT_ORDER_ID_VERSION,
    SHORT_CLIENT_ORDER_ID_VERSION,
    ClientOrderIdInputs,
    build_client_order_id,
    canonical_client_order_id,
    generate_client_order_id,
)


def _base_inputs(**overrides: object) -> ClientOrderIdInputs:
    fields = {
        "venue": "BINANCE",
        "account_id": "acct-main",
        "strategy_id": "pairs-v1",
        "trade_id": "trade-000001",
        "leg": "A",
        "phase": "ENTRY",
        "symbol": "BTCUSDT",
        "attempt": 1,
    }
    fields.update(overrides)
    return ClientOrderIdInputs(**fields)


def test_canonical_id_is_deterministic_and_versioned() -> None:
    inputs = _base_inputs()

    first = build_client_order_id(inputs)
    second = build_client_order_id(inputs)

    assert first == second
    assert first.version == CLIENT_ORDER_ID_VERSION
    assert not first.is_shortened
    assert first.client_order_id == first.canonical_id
    assert first.client_order_id == (
        "coid.v1:BINANCE:acct-main:pairs-v1:trade-000001:A:ENTRY:BTCUSDT:attempt-1"
    )


def test_reconstructing_inputs_after_restart_regenerates_same_id() -> None:
    before_restart = build_client_order_id(_base_inputs())

    reconstructed_inputs = ClientOrderIdInputs(
        venue="BINANCE",
        account_id="acct-main",
        strategy_id="pairs-v1",
        trade_id="trade-000001",
        leg="A",
        phase="ENTRY",
        symbol="BTCUSDT",
        attempt=1,
    )
    after_restart = build_client_order_id(reconstructed_inputs)

    assert after_restart == before_restart


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("venue", "KRAKEN"),
        ("account_id", "acct-sub"),
        ("strategy_id", "meanrev-v2"),
        ("trade_id", "trade-000002"),
        ("leg", "B"),
        ("phase", "EXIT"),
        ("symbol", "ETHUSDT"),
        ("attempt", 2),
    ),
)
def test_ids_are_unique_by_required_dimensions(field: str, value: object) -> None:
    baseline = build_client_order_id(_base_inputs()).client_order_id
    changed = build_client_order_id(_base_inputs(**{field: value})).client_order_id

    assert changed != baseline


def test_slice_id_is_supported_and_distinct_from_attempt() -> None:
    attempt_id = build_client_order_id(_base_inputs(attempt="slice-001")).client_order_id
    slice_id = build_client_order_id(
        _base_inputs(attempt=None, slice_id="slice-001")
    ).client_order_id

    assert attempt_id.endswith(":attempt-slice-001")
    assert slice_id.endswith(":slice-slice-001")
    assert slice_id != attempt_id


def test_exactly_one_attempt_or_slice_id_is_required() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        canonical_client_order_id(_base_inputs(attempt=None))

    with pytest.raises(ValueError, match="exactly one"):
        canonical_client_order_id(_base_inputs(slice_id="slice-001"))


def test_no_timestamp_randomness_or_process_state_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("non-deterministic source was called")

    monkeypatch.setattr("time.time", fail_if_called)
    monkeypatch.setattr("time.monotonic", fail_if_called)
    monkeypatch.setattr("random.random", fail_if_called)

    ids = [build_client_order_id(_base_inputs()).client_order_id for _ in range(5)]

    assert ids == [ids[0]] * 5


def test_shortening_is_deterministic_versioned_bounded_and_preserves_canonical() -> None:
    inputs = _base_inputs(
        account_id="account-with-a-very-long-subaccount-name",
        strategy_id="statistical-arbitrage-pairs-sprint-three",
        trade_id="trade-with-long-durable-ledger-identifier-000001",
        symbol="ETHBTC-PERPETUAL-CONTRACT",
    )

    first = build_client_order_id(inputs, max_length=36)
    second = build_client_order_id(inputs, max_length=36)

    assert first == second
    assert first.is_shortened
    assert first.client_order_id.startswith(f"{SHORT_CLIENT_ORDER_ID_VERSION}:")
    assert len(first.client_order_id) <= 36
    assert first.canonical_id == canonical_client_order_id(inputs)
    assert first.canonical_id != first.client_order_id


def test_shortened_ids_change_when_any_uniqueness_dimension_changes() -> None:
    dimensions = {
        "venue": "KRAKEN",
        "account_id": "acct-secondary",
        "strategy_id": "pairs-v2",
        "trade_id": "trade-000099",
        "leg": "B",
        "phase": "HEDGE",
        "symbol": "ETHUSDT",
        "attempt": 7,
    }
    baseline = build_client_order_id(_base_inputs(), max_length=28).client_order_id
    changed_ids = {
        build_client_order_id(_base_inputs(**{field: value}), max_length=28).client_order_id
        for field, value in dimensions.items()
    }

    assert baseline not in changed_ids
    assert len(changed_ids) == len(dimensions)


def test_attempt_and_slice_domains_remain_unique_in_bulk() -> None:
    ids = set()
    for leg, phase, symbol, attempt in itertools.product(
        ("A", "B"),
        ("ENTRY", "EXIT"),
        ("BTCUSDT", "ETHUSDT"),
        (1, 2, 3),
    ):
        ids.add(
            generate_client_order_id(
                venue="BINANCE",
                account_id="acct-main",
                strategy_id="pairs-v1",
                trade_id="trade-000001",
                leg=leg,
                phase=phase,
                symbol=symbol,
                attempt=attempt,
            )
        )

    for leg, phase, symbol, slice_id in itertools.product(
        ("A", "B"),
        ("ENTRY", "EXIT"),
        ("BTCUSDT", "ETHUSDT"),
        ("slice-001", "slice-002", "slice-003"),
    ):
        ids.add(
            generate_client_order_id(
                venue="BINANCE",
                account_id="acct-main",
                strategy_id="pairs-v1",
                trade_id="trade-000001",
                leg=leg,
                phase=phase,
                symbol=symbol,
                slice_id=slice_id,
            )
        )

    assert len(ids) == 48


def test_invalid_components_are_rejected_before_building_ids() -> None:
    with pytest.raises(ValueError, match="unsupported characters"):
        build_client_order_id(_base_inputs(symbol="BTC/USDT"))

    with pytest.raises(ValueError, match="ASCII"):
        build_client_order_id(_base_inputs(account_id="conta-principal-\u00e1"))


def test_too_small_shortened_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_length"):
        build_client_order_id(_base_inputs(), max_length=12)
