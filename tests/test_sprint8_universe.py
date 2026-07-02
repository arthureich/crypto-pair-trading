from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (
    Sprint8ContractError,
    assert_pair_cost_gated,
    load_sprint8_universe_contract,
    validate_sprint8_universe_contract,
)


def test_sprint8_universe_contract_loads_exact_cost_gated_scope() -> None:
    contract = load_sprint8_universe_contract()

    assert contract.evidence_scope == "2023-06"
    assert len(contract.approved_pairs) == 31
    assert len(contract.blocked_pairs) == 10
    assert contract.cost_gate["cost_gated_pass"] is True
    assert contract.artifacts["execution_cost_gate_json"].endswith(
        "all_candidates_202306_execution_cost_gate.json"
    )


def test_sprint8_universe_contract_excludes_ada_from_approved_pairs() -> None:
    contract = load_sprint8_universe_contract()

    assert all("ADAUSDT" not in pair.split("/") for pair in contract.approved_pairs)
    assert all("ADAUSDT" in pair.split("/") for pair in contract.blocked_pairs)


def test_sprint8_universe_contract_blocks_all_ada_pairs_fail_closed() -> None:
    contract = load_sprint8_universe_contract()

    for pair in contract.blocked_pairs:
        with pytest.raises(Sprint8ContractError, match="blocked by Sprint 8 cost evidence"):
            assert_pair_cost_gated(pair, contract)


def test_sprint8_universe_contract_blocks_statistical_only_unknown_pair() -> None:
    contract = load_sprint8_universe_contract()

    with pytest.raises(Sprint8ContractError, match="outside the Sprint 8 cost-gated universe"):
        assert_pair_cost_gated("XRPUSDT/UNIUSDT", contract)


def test_sprint8_universe_contract_self_validates() -> None:
    contract = load_sprint8_universe_contract()

    validate_sprint8_universe_contract(contract)
