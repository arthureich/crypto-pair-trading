from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reconciliation import CumulativeFillStatus, reconcile_cumulative_fill
from src.recovery import (
    PartialFillRouteDecisionType,
    PartialFillRouteInput,
    PartialFillRouteReason,
    decide_partial_fill_route,
)


def _route_input(**overrides: object) -> PartialFillRouteInput:
    fields = {
        "trade_id": "trade-1",
        "venue": "BINANCE",
        "account_id": "paper-main",
        "filled_leg": "A",
        "symbol": "BTCUSDT",
        "known_position_qty": Decimal("0.50"),
        "target_position_qty": Decimal("1.00"),
        "residual_order_uncertain": False,
        "paired_leg_reconciled": False,
        "hedge_reduces_exposure": True,
        "risk_reducing_proof": True,
    }
    fields.update(overrides)
    return PartialFillRouteInput(**fields)


def test_unpaired_partial_fill_with_risk_reducing_proof_routes_to_hedge_required() -> None:
    decision = decide_partial_fill_route(_route_input())

    assert decision.decision is PartialFillRouteDecisionType.HEDGING_REQUIRED
    assert decision.hedge_required is True
    assert decision.reason is PartialFillRouteReason.HEDGE_PROVEN_RISK_REDUCING
    assert decision.imbalance_qty == Decimal("0.50")
    assert decision.normal_entry_continuation_allowed is False


def test_residual_order_uncertainty_routes_to_exit_lockdown_even_with_hedge_proof() -> None:
    decision = decide_partial_fill_route(_route_input(residual_order_uncertain=True))

    assert decision.decision is PartialFillRouteDecisionType.EXIT_LOCKDOWN
    assert decision.exit_lockdown is True
    assert decision.reason is PartialFillRouteReason.RESIDUAL_ORDER_UNCERTAIN
    assert decision.normal_entry_continuation_allowed is False


def test_missing_risk_reducing_proof_routes_to_exit_lockdown() -> None:
    decision = decide_partial_fill_route(_route_input(risk_reducing_proof=False))

    assert decision.decision is PartialFillRouteDecisionType.EXIT_LOCKDOWN
    assert decision.reason is PartialFillRouteReason.HEDGE_PROOF_MISSING


def test_non_risk_reducing_hedge_routes_to_exit_lockdown() -> None:
    decision = decide_partial_fill_route(_route_input(hedge_reduces_exposure=False))

    assert decision.decision is PartialFillRouteDecisionType.EXIT_LOCKDOWN
    assert decision.reason is PartialFillRouteReason.HEDGE_NOT_RISK_REDUCING


def test_absent_unpaired_exposure_proof_routes_to_exit_lockdown_not_continue_entry() -> None:
    balanced = decide_partial_fill_route(
        _route_input(known_position_qty="1.00", target_position_qty="1.00")
    )
    paired_reconciled = decide_partial_fill_route(_route_input(paired_leg_reconciled=True))

    assert balanced.decision is PartialFillRouteDecisionType.EXIT_LOCKDOWN
    assert balanced.reason is PartialFillRouteReason.NO_UNPAIRED_EXPOSURE_PROOF
    assert balanced.normal_entry_continuation_allowed is False
    assert paired_reconciled.decision is PartialFillRouteDecisionType.EXIT_LOCKDOWN
    assert paired_reconciled.reason is PartialFillRouteReason.NO_UNPAIRED_EXPOSURE_PROOF


def test_decimal_precision_is_preserved_for_imbalance_quantity() -> None:
    decision = decide_partial_fill_route(
        _route_input(
            known_position_qty=Decimal("0.3000000000000000000000000001"),
            target_position_qty=Decimal("0.1"),
        )
    )

    assert decision.imbalance_qty == Decimal("0.2000000000000000000000000001")


@pytest.mark.parametrize(
    "route_input,match",
    (
        (_route_input(trade_id=""), "trade_id is required"),
        (_route_input(known_position_qty=-1), "non-negative"),
        (_route_input(known_position_qty=0.3), "must not be float"),
    ),
)
def test_invalid_inputs_fail_closed(route_input: PartialFillRouteInput, match: str) -> None:
    with pytest.raises((TypeError, ValueError), match=match):
        decide_partial_fill_route(route_input)


def test_sprint4_reconciled_partial_fill_delta_routes_to_hedge_or_lockdown() -> None:
    fill_result = reconcile_cumulative_fill(exchange_cum_qty="0.50", ledger_cum_qty="0")

    assert fill_result.status is CumulativeFillStatus.NEW_FILL
    assert fill_result.delta_fill == Decimal("0.50")

    hedge = decide_partial_fill_route(
        _route_input(
            known_position_qty=fill_result.ledger_cum_qty_after,
            target_position_qty="1.00",
            risk_reducing_proof=True,
            hedge_reduces_exposure=True,
        )
    )
    lockdown = decide_partial_fill_route(
        _route_input(
            known_position_qty=fill_result.ledger_cum_qty_after,
            target_position_qty="1.00",
            risk_reducing_proof=False,
            hedge_reduces_exposure=True,
        )
    )

    assert hedge.decision is PartialFillRouteDecisionType.HEDGING_REQUIRED
    assert hedge.normal_entry_continuation_allowed is False
    assert lockdown.decision is PartialFillRouteDecisionType.EXIT_LOCKDOWN
    assert lockdown.reason is PartialFillRouteReason.HEDGE_PROOF_MISSING
