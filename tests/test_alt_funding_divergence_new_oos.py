import math

import numpy as np
import pandas as pd
import pytest

from scripts.diagnostic_alt_funding_divergence_new_oos import (
    DATA_GATE_FAIL,
    DO_NOT_PROMOTE,
    HOUR_MS,
    build_funding_price_divergence_panel,
    run_new_oos_diagnostic,
)

START_MS = int(pd.Timestamp("2026-06-01", tz="UTC").timestamp() * 1000)
END_MS = int(pd.Timestamp("2026-07-01", tz="UTC").timestamp() * 1000)
BASE_HOURS = 2300
EXTENSION_HOURS = 720


def test_old_context_seeds_feature_but_old_rows_are_excluded_from_decision_panel():
    base = _bars("AAAUSDT", START_MS - BASE_HOURS * HOUR_MS, BASE_HOURS)
    extension = _bars("AAAUSDT", START_MS, EXTENSION_HOURS, offset=BASE_HOURS)

    panel = build_funding_price_divergence_panel(
        base,
        extension,
        start_ms=START_MS,
        end_ms=END_MS,
    )

    assert panel["open_time"].min() >= START_MS
    assert panel["open_time"].max() < END_MS
    assert panel["feature"].notna().any()


def test_future_mutation_does_not_change_current_funding_price_divergence():
    base = _bars("AAAUSDT", START_MS - BASE_HOURS * HOUR_MS, BASE_HOURS)
    extension = _bars("AAAUSDT", START_MS, EXTENSION_HOURS, offset=BASE_HOURS)
    decision_time = START_MS + 100 * HOUR_MS

    original = build_funding_price_divergence_panel(
        base,
        extension,
        start_ms=START_MS,
        end_ms=END_MS,
    )
    original_feature = _feature_at(original, decision_time)

    mutated = extension.copy()
    future_mask = mutated["open_time"] > decision_time
    mutated.loc[future_mask, "log_price"] = mutated.loc[future_mask, "log_price"] + 10.0
    mutated.loc[future_mask, "funding_rate_asof"] = (
        mutated.loc[future_mask, "funding_rate_asof"] + 1.0
    )
    after_mutation = build_funding_price_divergence_panel(
        base,
        mutated,
        start_ms=START_MS,
        end_ms=END_MS,
    )

    assert _feature_at(after_mutation, decision_time) == pytest.approx(original_feature)


def test_last_24h_without_forward_target_are_dropped_from_valid_observations():
    base = _bars("AAAUSDT", START_MS - BASE_HOURS * HOUR_MS, BASE_HOURS)
    extension = _bars("AAAUSDT", START_MS, EXTENSION_HOURS, offset=BASE_HOURS)

    diagnostic = run_new_oos_diagnostic(
        base,
        extension,
        symbols=("AAAUSDT",),
        start_month="2026-06",
        end_month_exclusive="2026-07",
        min_observations=1,
    )

    assert diagnostic.information_result is not None
    assert diagnostic.information_result.full_sample_n == EXTENSION_HOURS - 24


def test_data_gate_fails_closed_for_missing_symbol():
    base = _bars("AAAUSDT", START_MS - BASE_HOURS * HOUR_MS, BASE_HOURS)
    extension = _bars("AAAUSDT", START_MS, EXTENSION_HOURS, offset=BASE_HOURS)

    diagnostic = run_new_oos_diagnostic(
        base,
        extension,
        symbols=("AAAUSDT", "BBBUSDT"),
        start_month="2026-06",
        end_month_exclusive="2026-07",
        min_observations=1,
    )

    assert diagnostic.decision == DATA_GATE_FAIL
    assert diagnostic.information_result is None
    assert any("missing symbols" in reason for reason in diagnostic.data_gate.reasons)


def test_data_gate_fails_closed_for_duplicate_symbol_hour():
    base = _bars("AAAUSDT", START_MS - BASE_HOURS * HOUR_MS, BASE_HOURS)
    extension = _bars("AAAUSDT", START_MS, EXTENSION_HOURS, offset=BASE_HOURS)
    duplicated = pd.concat([extension, extension.iloc[[0]]], ignore_index=True)

    diagnostic = run_new_oos_diagnostic(
        base,
        duplicated,
        symbols=("AAAUSDT",),
        start_month="2026-06",
        end_month_exclusive="2026-07",
        min_observations=1,
    )

    assert diagnostic.decision == DATA_GATE_FAIL
    assert diagnostic.information_result is None
    assert any("duplicate" in reason for reason in diagnostic.data_gate.reasons)


def test_low_valid_observation_count_fails_data_gate_after_information_result():
    base = _bars("AAAUSDT", START_MS - BASE_HOURS * HOUR_MS, BASE_HOURS)
    extension = _bars("AAAUSDT", START_MS, EXTENSION_HOURS, offset=BASE_HOURS)

    diagnostic = run_new_oos_diagnostic(
        base,
        extension,
        symbols=("AAAUSDT",),
        start_month="2026-06",
        end_month_exclusive="2026-07",
        min_observations=EXTENSION_HOURS,
    )

    assert diagnostic.decision == DATA_GATE_FAIL
    assert diagnostic.information_result is not None
    assert diagnostic.information_result.full_sample_n == EXTENSION_HOURS - 24
    assert any("below minimum" in reason for reason in diagnostic.data_gate.reasons)


def test_valid_data_gate_still_does_not_promote_without_threshold_rho():
    base = _bars("AAAUSDT", START_MS - BASE_HOURS * HOUR_MS, BASE_HOURS)
    extension = _bars("AAAUSDT", START_MS, EXTENSION_HOURS, offset=BASE_HOURS)

    diagnostic = run_new_oos_diagnostic(
        base,
        extension,
        symbols=("AAAUSDT",),
        start_month="2026-06",
        end_month_exclusive="2026-07",
        min_observations=1,
    )

    assert diagnostic.data_gate.status == "PASS"
    assert diagnostic.decision in {DO_NOT_PROMOTE, "PROMOVE_PARA_FEASIBILITY"}


def _feature_at(panel: pd.DataFrame, open_time: int) -> float:
    value = panel.loc[panel["open_time"] == open_time, "feature"].iloc[0]
    assert math.isfinite(value)
    return float(value)


def _bars(symbol: str, start_ms: int, hours: int, *, offset: int = 0) -> pd.DataFrame:
    idx = np.arange(offset, offset + hours, dtype=float)
    open_time = start_ms + np.arange(hours, dtype=np.int64) * HOUR_MS
    price = 100.0 + 0.03 * idx + 0.4 * np.sin(idx / 13.0) + 0.2 * np.cos(idx / 29.0)
    funding = 0.0001 * np.sin(idx / 17.0) + 0.00005 * np.cos(idx / 31.0)
    return pd.DataFrame(
        {
            "symbol": symbol,
            "open_time": open_time,
            "log_price": np.log(price),
            "funding_rate_asof": funding,
        }
    )
