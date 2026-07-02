from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (
    OfflineSignalIntentError,
    Sprint8ContractError,
    generate_offline_signal_intent,
    generate_pair_signal_intents,
    load_sprint8_universe_contract,
    pair_execution_cost_bps,
    run_cost_aware_backtest,
    sprint8,
)

HOUR_MS = 60 * 60 * 1000


def _pair_bars(symbol_a: str, symbol_b: str, spread: np.ndarray, drift_step: float) -> pd.DataFrame:
    n = len(spread)
    x = np.cumsum(np.full(n, drift_step))
    y = x + spread
    open_time = np.arange(n, dtype=np.int64) * HOUR_MS
    return pd.concat(
        [
            pd.DataFrame({"symbol": symbol_a, "open_time": open_time, "log_price": y}),
            pd.DataFrame({"symbol": symbol_b, "open_time": open_time, "log_price": x}),
        ],
        ignore_index=True,
    )


def test_generate_offline_signal_intent_uses_research_only_schema() -> None:
    contract = load_sprint8_universe_contract()

    intent = generate_offline_signal_intent(
        pair="ARBUSDT/OPUSDT",
        zscore=2.5,
        beta=1.1,
        half_life_hours=48.0,
        created_at=1_685_577_600_000,
        contract=contract,
        target_notional=2_000.0,
    )

    assert intent is not None
    assert intent.side_a == "SELL"
    assert intent.side_b == "BUY"
    assert intent.signal_id == "S8-ARBUSDT-OPUSDT-1685577600000-SHORT_SPREAD"
    assert intent.to_dict()["source"] == "SPRINT8_RESEARCH_OFFLINE"


def test_generate_offline_signal_intent_ignores_sub_threshold_zscore() -> None:
    contract = load_sprint8_universe_contract()

    intent = generate_offline_signal_intent(
        pair="ARBUSDT/OPUSDT",
        zscore=1.99,
        beta=1.0,
        half_life_hours=24.0,
        created_at=1,
        contract=contract,
    )

    assert intent is None


def test_generate_offline_signal_intent_blocks_ada_pair() -> None:
    contract = load_sprint8_universe_contract()

    with pytest.raises(Sprint8ContractError, match="blocked by Sprint 8 cost evidence"):
        generate_offline_signal_intent(
            pair="ADAUSDT/DOTUSDT",
            zscore=-2.4,
            beta=1.0,
            half_life_hours=24.0,
            created_at=1,
            contract=contract,
        )


def test_run_cost_aware_backtest_subtracts_pair_execution_costs() -> None:
    contract = load_sprint8_universe_contract()
    intent = generate_offline_signal_intent(
        pair="ARBUSDT/OPUSDT",
        zscore=-2.5,
        beta=1.0,
        half_life_hours=12.0,
        created_at=1_685_577_600_000,
        contract=contract,
        target_notional=10_000.0,
    )
    assert intent is not None

    result = run_cost_aware_backtest(
        [intent],
        gross_edge_bps_by_signal_id={intent.signal_id: 14.0},
        symbol_cost_bps={"ARBUSDT": 1.5, "OPUSDT": 1.25},
        contract=contract,
    )

    assert result.metrics.trade_count == 1
    assert result.metrics.gross_pnl_bps == 14.0
    assert result.metrics.cost_bps == 2.75
    assert result.metrics.net_pnl_bps == 11.25
    assert result.metrics.net_pnl_quote == 11.25
    assert result.metrics.hit_rate == 1.0


def test_pair_execution_cost_fails_closed_when_leg_cost_is_missing() -> None:
    with pytest.raises(OfflineSignalIntentError, match="missing execution cost"):
        pair_execution_cost_bps("ARBUSDT/OPUSDT", {"ARBUSDT": 1.0})


def test_generate_pair_signal_intents_is_causal_across_appended_future_bars() -> None:
    """Signals produced for early bars must not change when later bars are appended.

    The mean-reversion/half-life gate previously fit OU once on the whole
    series, so a regime change appearing only in later bars could silently
    approve or reject signals earlier in the window. Appending a very
    different continuation must not change any signal whose created_at is
    inside the original, unchanged prefix.
    """

    rng = np.random.default_rng(1234)
    prefix_len = 60
    ou_window = 20
    phi_true = 0.85
    noise = rng.normal(0.0, 0.01, size=prefix_len)
    prefix_spread = np.zeros(prefix_len)
    for i in range(1, prefix_len):
        prefix_spread[i] = phi_true * prefix_spread[i - 1] + noise[i]

    # A sharply different continuation: a strong linear trend, not mean
    # reverting, which would pull a full-sample OU fit toward a different
    # phi/half-life than the causal trailing-window fit would find.
    extension = prefix_spread[-1] + 5.0 * np.arange(1, 41)
    full_spread = np.concatenate([prefix_spread, extension])

    prefix_bars = _pair_bars("ARBUSDT", "OPUSDT", prefix_spread, drift_step=0.001)
    full_bars = _pair_bars("ARBUSDT", "OPUSDT", full_spread, drift_step=0.001)

    contract = load_sprint8_universe_contract()
    prefix_intents = generate_pair_signal_intents(
        prefix_bars,
        "ARBUSDT/OPUSDT",
        contract=contract,
        zscore_window=ou_window,
        ou_window=ou_window,
        entry_zscore=0.5,
    )
    full_intents = generate_pair_signal_intents(
        full_bars,
        "ARBUSDT/OPUSDT",
        contract=contract,
        zscore_window=ou_window,
        ou_window=ou_window,
        entry_zscore=0.5,
    )
    prefix_cutoff = (prefix_len - 1) * HOUR_MS
    full_intents_in_prefix = tuple(
        intent for intent in full_intents if intent.created_at <= prefix_cutoff
    )

    assert prefix_intents == full_intents_in_prefix
    assert len(prefix_intents) > 0


def test_sprint8_module_does_not_import_live_execution_planes() -> None:
    source = inspect.getsource(sprint8)

    forbidden_imports = ("src.execution", "src.ledger", "src.live", "src.recovery")
    assert all(forbidden not in source for forbidden in forbidden_imports)
