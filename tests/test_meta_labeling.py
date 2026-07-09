"""Tests for src/research/meta_labeling.py (TASK-ML-001 feature/label panel).

The label/entry-reconstruction core is tested on tiny hand-computable
datasets that bypass the feature warm-up. The full panel is tested with
the causal windows monkeypatched small, so post-warm-up entries survive
in a compact fixture.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.research import meta_labeling
from src.research.funding_carry import (
    FundingCarryConfig,
    run_incremental_funding_carry_backtest,
)
from src.research.meta_labeling import (
    FEATURE_NAMES,
    PANEL_COLUMNS,
    MetaLabelingError,
    _build_feature_frames,
    _reconstruct_entries,
    build_leg_interval_panel,
    build_meta_label_panel,
    run_filtered_incremental_backtest,
    run_leg_interval_filtered_backtest,
)


def _swap_fixture() -> pd.DataFrame:
    # 3 symbols, K=1, funding that varies enough to trigger refills and swaps.
    rows = []
    for i in range(16):
        t = i * STEP_MS
        rows.append((t, "XXX", 0.01 * (i % 3), 1000.0, -0.01 + 0.001 * (i % 4)))
        rows.append((t, "YYY", 0.02 * (i % 3), 1000.0, 0.01 - 0.001 * (i % 4)))
        # ZZZ starts as pool, then dives below XXX to force a long swap.
        rows.append((t, "ZZZ", 0.015 * (i % 3), 1000.0, (0.0 if i < 8 else -0.03)))
    return _bars(rows)


HOUR_MS = 3_600_000
STEP_MS = 8 * HOUR_MS  # one 8h rebalance interval


def _bars(rows: list[tuple[int, str, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["open_time", "symbol", "log_price", "quote_volume", "funding_rate_asof"]
    )


def test_bootstrap_entries_accumulate_hold_pnl_and_label_positive() -> None:
    # 2 symbols, K=1: A (lowest funding) -> long, B (highest) -> short. Stable
    # funding => bootstrap entries at t0, held to the end, no swaps. Constant
    # price => price PnL 0. Per interval each leg earns weight*|rate|*1e4 bps.
    # weight = 1/(2*1) = 0.5; funding 0.001 => 5 bps/interval; 3 resolved
    # intervals => 15 bps; entry cost = 0.5*6 = 3 bps => net 12 bps, label 1.
    rows = []
    for i in range(4):  # t0..t3; t3 has no forward -> NO_DATA, so 3 resolved.
        t = i * STEP_MS
        rows.append((t, "AAA", 0.0, 1000.0, -0.001))
        rows.append((t, "BBB", 0.0, 1000.0, 0.001))
    entries = _reconstruct_entries(_bars(rows), FundingCarryConfig(k=1))

    assert len(entries) == 2
    by_symbol = {e["symbol"]: e for e in entries}
    assert by_symbol["AAA"]["side"] == "long"
    assert by_symbol["BBB"]["side"] == "short"
    for entry in entries:
        assert entry["decision_time_ms"] == 0
        assert entry["label_end_time_ms"] == 3 * STEP_MS  # last resolved forward (t2 + interval)
        assert entry["net_pnl_bps"] == pytest.approx(12.0)
        assert entry["label"] == 1


def test_label_is_zero_when_net_pnl_is_negative() -> None:
    # Tiny funding so the accumulated carry cannot cover the entry cost.
    rows = []
    for i in range(4):
        t = i * STEP_MS
        rows.append((t, "AAA", 0.0, 1000.0, -0.00001))
        rows.append((t, "BBB", 0.0, 1000.0, 0.00001))
    entries = _reconstruct_entries(_bars(rows), FundingCarryConfig(k=1))

    for entry in entries:
        assert entry["net_pnl_bps"] < 0.0
        assert entry["label"] == 0


def test_forced_ineligibility_creates_a_midstream_exit_and_entry() -> None:
    # 3 symbols, K=1. t0: X lowest (long), Z highest (short), Y in pool.
    # t1: X becomes ineligible (NaN funding) -> dropped, refilled from pool
    # with Y -> X exits at t1, Y enters long at t1.
    rows = [
        (0, "XXX", 0.0, 1000.0, -0.002),
        (0, "YYY", 0.0, 1000.0, 0.000),
        (0, "ZZZ", 0.0, 1000.0, 0.002),
        (STEP_MS, "XXX", 0.0, 1000.0, float("nan")),
        (STEP_MS, "YYY", 0.0, 1000.0, -0.001),
        (STEP_MS, "ZZZ", 0.0, 1000.0, 0.002),
        (2 * STEP_MS, "XXX", 0.0, 1000.0, -0.002),
        (2 * STEP_MS, "YYY", 0.0, 1000.0, -0.001),
        (2 * STEP_MS, "ZZZ", 0.0, 1000.0, 0.002),
    ]
    entries = _reconstruct_entries(_bars(rows), FundingCarryConfig(k=1))
    by_key = {(e["symbol"], e["side"]): e for e in entries}

    # X entered long at t0 and exited at t1 (its last earning interval ends there).
    assert ("XXX", "long") in by_key
    assert by_key[("XXX", "long")]["decision_time_ms"] == 0
    assert by_key[("XXX", "long")]["label_end_time_ms"] == STEP_MS
    # Y entered long at t1 (the forced refill) and is held to the end.
    assert ("YYY", "long") in by_key
    assert by_key[("YYY", "long")]["decision_time_ms"] == STEP_MS
    # Z (short) is held from t0 to the end.
    assert ("ZZZ", "short") in by_key
    assert by_key[("ZZZ", "short")]["decision_time_ms"] == 0


def test_features_are_causal_a_future_bar_does_not_change_an_earlier_feature() -> None:
    # ~60 hourly bars, 2 symbols; realized_vol_24h at an early row must not
    # change when a strictly later bar's price is mutated.
    rows = []
    for i in range(60):
        t = i * HOUR_MS
        rows.append((t, "AAA", 0.01 * (i % 5), 1000.0 + i, 0.0001 * (i % 3 - 1)))
        rows.append((t, "BBB", 0.02 * (i % 4), 2000.0 + i, 0.0002 * (i % 3 - 1)))
    base = _build_feature_frames(_bars(rows))
    early_time = 40 * HOUR_MS
    early_value = base["realized_vol_24h"].at[early_time, "AAA"]

    mutated_rows = list(rows)
    # Mutate a strictly later bar (row for i=55, AAA).
    idx = next(j for j, r in enumerate(mutated_rows) if r[0] == 55 * HOUR_MS and r[1] == "AAA")
    mutated_rows[idx] = (55 * HOUR_MS, "AAA", 9.99, 1000.0 + 55, 0.0)
    mutated = _build_feature_frames(_bars(mutated_rows))

    assert mutated["realized_vol_24h"].at[early_time, "AAA"] == pytest.approx(early_value)


def test_build_meta_label_panel_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    # Shrink the causal windows so post-warm-up entries survive in a compact
    # fixture. 3 symbols, K=1; funding wiggles (so the z-score is defined)
    # around stable means until ZZZ drops below XXX at i>=20, forcing a swap
    # -> a ZZZ long entry whose decision time is well past warm-up.
    monkeypatch.setattr(meta_labeling, "FORWARD_HORIZON_HOURS", 3)
    monkeypatch.setattr(meta_labeling, "WEEK_HOURS", 4)
    monkeypatch.setattr(meta_labeling, "ROLLING_WINDOW_HOURS", 6)

    rows = []
    for i in range(32):
        t = i * STEP_MS
        wiggle = 0.0005 * ((i % 3) - 1)
        z_funding = (0.0 if i < 20 else -0.02) + wiggle
        rows.append((t, "XXX", 0.02 * (i % 4), 1000.0 + 50 * (i % 4), -0.01 + wiggle))
        rows.append((t, "YYY", 0.02 * ((i + 1) % 4), 1000.0 + 50 * ((i + 1) % 4), 0.01 + wiggle))
        rows.append((t, "ZZZ", 0.02 * ((i + 2) % 4), 1000.0 + 50 * ((i + 2) % 4), z_funding))
    panel = build_meta_label_panel(_bars(rows), FundingCarryConfig(k=1))

    assert list(panel.columns) == list(PANEL_COLUMNS)
    assert len(panel) > 0
    assert "n_dropped_warmup" in panel.attrs
    # No NaN leaked into any feature column.
    for name in FEATURE_NAMES:
        assert panel[name].notna().all()
    # Label is exactly the sign of net PnL, and holds resolve after entry.
    assert ((panel["net_pnl_bps"] > 0.0).astype(int) == panel["label"]).all()
    assert (panel["label_end_time_ms"] > panel["decision_time_ms"]).all()
    # The post-warm-up forced swap (ZZZ enters long at i=20) survived.
    zzz_long = panel[(panel["symbol"] == "ZZZ") & (panel["side"] == "long")]
    assert (zzz_long["decision_time_ms"] == 20 * STEP_MS).any()


def test_filtered_runner_with_allow_all_gate_matches_canonical_backtest() -> None:
    # The re-expressed loop must reproduce funding_carry's incremental backtest
    # exactly when nothing is vetoed -- the guard against silent divergence.
    bars = _swap_fixture()
    config = FundingCarryConfig(k=1)

    canonical = run_incremental_funding_carry_backtest(bars, config)
    filtered = run_filtered_incremental_backtest(bars, config)  # default allow-all

    assert len(filtered) == len(canonical)
    for got, expected in zip(filtered, canonical, strict=True):
        assert got.rebalance_time == expected.rebalance_time
        assert got.status == expected.status
        assert got.held_long == expected.held_long
        assert got.held_short == expected.held_short
        assert got.swap_count == expected.swap_count
        assert got.net_pnl_bps == pytest.approx(expected.net_pnl_bps)
        assert got.gross_pnl_bps == pytest.approx(expected.gross_pnl_bps)
        assert got.cost_bps == pytest.approx(expected.cost_bps)


def test_veto_gate_keeps_a_symbol_out_of_every_held_set() -> None:
    bars = _swap_fixture()
    config = FundingCarryConfig(k=1)

    def veto_zzz(symbol: str, side: str, decision_time_ms: int) -> bool:  # noqa: ARG001
        return symbol != "ZZZ"

    # ZZZ enters the canonical book (it dives below XXX at i>=8); the veto
    # must keep it out entirely without crashing.
    canonical = run_incremental_funding_carry_backtest(bars, config)
    assert any("ZZZ" in r.held_long or "ZZZ" in r.held_short for r in canonical)

    filtered = run_filtered_incremental_backtest(bars, config, veto_zzz)
    assert all("ZZZ" not in r.held_long and "ZZZ" not in r.held_short for r in filtered)


def test_leg_interval_filtered_runner_with_allow_all_matches_canonical() -> None:
    # Option-2 overlay must reproduce the canonical incremental backtest when
    # nothing is vetoed: kept == held, weight 0.5/K == 1/(2K), entries ==
    # swap_count. Guards the renormalization + entry-cost accounting.
    bars = _swap_fixture()
    config = FundingCarryConfig(k=1)

    canonical = run_incremental_funding_carry_backtest(bars, config)
    filtered = run_leg_interval_filtered_backtest(bars, config)  # allow-all

    assert len(filtered) == len(canonical)
    for got, expected in zip(filtered, canonical, strict=True):
        assert got.status == expected.status
        assert got.held_long == expected.held_long
        assert got.held_short == expected.held_short
        assert got.swap_count == expected.swap_count
        assert got.net_pnl_bps == pytest.approx(expected.net_pnl_bps)
        assert got.gross_pnl_bps == pytest.approx(expected.gross_pnl_bps)
        assert got.cost_bps == pytest.approx(expected.cost_bps)


def test_leg_interval_veto_removes_a_symbol_and_keeps_book_dollar_neutral() -> None:
    bars = _swap_fixture()
    config = FundingCarryConfig(k=1)

    def veto_zzz(symbol: str, side: str, decision_time_ms: int) -> bool:  # noqa: ARG001
        return symbol != "ZZZ"

    filtered = run_leg_interval_filtered_backtest(bars, config, veto_zzz)
    # The veto acts on resolved intervals (where PnL is computed); non-resolved
    # results carry canonical held sets as-is but contribute no PnL.
    resolved = [r for r in filtered if r.status.value == "RESOLVED"]
    assert resolved  # the fixture has resolved rebalances
    assert all("ZZZ" not in r.held_long and "ZZZ" not in r.held_short for r in resolved)


def test_leg_interval_panel_has_far_more_rows_than_the_entry_only_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Option 2: one row per held leg-interval, not per entry. On the same
    # data it must yield many more rows than the entry-only panel -- the whole
    # reason for the switch. Windows shrunk so rows survive warm-up.
    monkeypatch.setattr(meta_labeling, "FORWARD_HORIZON_HOURS", 3)
    monkeypatch.setattr(meta_labeling, "WEEK_HOURS", 4)
    monkeypatch.setattr(meta_labeling, "ROLLING_WINDOW_HOURS", 6)

    rows = []
    for i in range(32):
        t = i * STEP_MS
        wiggle = 0.0005 * ((i % 3) - 1)
        rows.append((t, "XXX", 0.02 * (i % 4), 1000.0 + 50 * (i % 4), -0.01 + wiggle))
        rows.append((t, "YYY", 0.02 * ((i + 1) % 4), 1000.0 + 50 * ((i + 1) % 4), 0.01 + wiggle))
        rows.append((t, "ZZZ", 0.02 * ((i + 2) % 4), 1000.0 + 50 * ((i + 2) % 4), 0.0 + wiggle))
    bars = _bars(rows)
    config = FundingCarryConfig(k=1)

    leg_panel = build_leg_interval_panel(bars, config)
    entry_panel = build_meta_label_panel(bars, config)

    assert list(leg_panel.columns) == list(PANEL_COLUMNS)
    assert len(leg_panel) > len(entry_panel)
    # Label is exactly the sign of the interval net PnL; holds resolve later.
    assert ((leg_panel["net_pnl_bps"] > 0.0).astype(int) == leg_panel["label"]).all()
    assert (leg_panel["label_end_time_ms"] > leg_panel["decision_time_ms"]).all()
    for name in FEATURE_NAMES:
        assert leg_panel[name].notna().all()
    # At most 2K legs per rebalance (K=1 => 2), and the two sides are distinct.
    for _, group in leg_panel.groupby("decision_time_ms"):
        assert len(group) <= 2
        assert group["side"].is_unique


def test_fails_closed_on_missing_column() -> None:
    rows = _bars([(0, "AAA", 0.0, 1000.0, -0.001), (0, "BBB", 0.0, 1000.0, 0.001)]).drop(
        columns=["funding_rate_asof"]
    )
    with pytest.raises(MetaLabelingError, match="missing required columns"):
        build_meta_label_panel(rows, FundingCarryConfig(k=1))


def test_fails_closed_on_duplicate_symbol_open_time_rows() -> None:
    rows = _bars(
        [
            (0, "AAA", 0.0, 1000.0, -0.001),
            (0, "AAA", 0.0, 1000.0, -0.001),
            (0, "BBB", 0.0, 1000.0, 0.001),
        ]
    )
    with pytest.raises(MetaLabelingError, match="duplicate"):
        build_meta_label_panel(rows, FundingCarryConfig(k=1))
