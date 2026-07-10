"""Tests for src/research/position_sizing.py (TASK-FC-II-001 risk sizing overlay)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.funding_carry import (
    FundingCarryConfig,
    RebalanceStatus,
    run_incremental_funding_carry_backtest,
)
from src.research.position_sizing import (
    PositionSizingError,
    _causal_leg_vol,
    _inverse_vol_weights,
    _vol_target_scales,
    run_risk_sized_backtest,
    summarize_risk_sized,
)

HOUR_MS = 3_600_000
STEP_MS = 8 * HOUR_MS


def _bars(rows: list[tuple[int, str, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["open_time", "symbol", "log_price", "quote_volume", "funding_rate_asof"]
    )


def test_inverse_vol_weights_favor_the_calmer_leg_and_sum_to_half() -> None:
    leg_vol = pd.DataFrame({"AAA": [1.0], "BBB": [2.0]}, index=[0])
    weights = _inverse_vol_weights(("AAA", "BBB"), leg_vol, 0)

    assert sum(weights.values()) == pytest.approx(0.5)
    assert weights["AAA"] > weights["BBB"]  # calmer leg heavier
    assert weights["AAA"] == pytest.approx(0.5 * (1.0) / (1.0 + 0.5))
    assert weights["BBB"] == pytest.approx(0.5 * (0.5) / (1.0 + 0.5))


@pytest.mark.parametrize("bad", [float("nan"), 0.0, -1.0])
def test_inverse_vol_weights_fall_back_to_equal_on_bad_vol(bad: float) -> None:
    leg_vol = pd.DataFrame({"AAA": [1.0], "BBB": [bad]}, index=[0])
    weights = _inverse_vol_weights(("AAA", "BBB"), leg_vol, 0)
    assert weights == {"AAA": 0.25, "BBB": 0.25}  # each side-half split equally


def test_inverse_vol_weights_empty_side() -> None:
    assert _inverse_vol_weights((), pd.DataFrame(), 0) == {}


def test_vol_target_scales_clamp_and_warmup() -> None:
    baseline = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    # pre_scale much more volatile -> target/current < 1 -> clamped at scale_min.
    pre_scale = np.array([10.0, -10.0, 10.0, -10.0, 10.0, -10.0])
    scales = _vol_target_scales(baseline, pre_scale, window=2, scale_min=0.5, scale_max=2.0)

    assert scales[0] == 1.0  # warm-up (no trailing std yet) -> neutral
    assert np.all(scales >= 0.5) and np.all(scales <= 2.0)
    # baseline is constant (std 0) -> target 0 -> scale clamps to the floor once defined.
    assert scales[-1] == pytest.approx(0.5)


def test_causal_leg_vol_a_future_bar_does_not_change_an_earlier_value() -> None:
    rows = [(i * HOUR_MS, "AAA", 0.01 * (i % 5), 1000.0, 0.0) for i in range(40)]
    rows += [(i * HOUR_MS, "BBB", 0.02 * (i % 4), 1000.0, 0.0) for i in range(40)]
    base = _causal_leg_vol(_bars(rows), lookback_hours=5)
    early = base.at[20 * HOUR_MS, "AAA"]

    mutated = list(rows)
    idx = next(j for j, r in enumerate(mutated) if r[0] == 33 * HOUR_MS and r[1] == "AAA")
    mutated[idx] = (33 * HOUR_MS, "AAA", 9.99, 1000.0, 0.0)
    after = _causal_leg_vol(_bars(mutated), lookback_hours=5)

    assert after.at[20 * HOUR_MS, "AAA"] == pytest.approx(early, nan_ok=True)


def _sizing_fixture() -> pd.DataFrame:
    # 2 symbols, K=1: AAA long (low funding), BBB short (high funding); price
    # varies so vols are defined; ~20 rebalances.
    rows = []
    for i in range(20):
        t = i * STEP_MS
        rows.append((t, "AAA", 0.01 * (i % 5), 1000.0, -0.001))
        rows.append((t, "BBB", 0.02 * (i % 3), 1000.0, 0.001))
    return _bars(rows)


def test_run_risk_sized_backtest_matches_baseline_and_clamps_scale() -> None:
    bars = _sizing_fixture()
    config = FundingCarryConfig(k=1)
    results = run_risk_sized_backtest(
        bars, config, vol_lookback_hours=3, vol_target_window_hours=32
    )

    canonical = [
        r
        for r in run_incremental_funding_carry_backtest(bars, config)
        if r.status is RebalanceStatus.RESOLVED
    ]
    assert len(results) == len(canonical)
    # Baseline leg of the overlay reproduces the canonical net PnL exactly.
    for sized, canon in zip(results, canonical, strict=True):
        assert sized.baseline_net_bps == pytest.approx(canon.net_pnl_bps)
        assert 0.5 <= sized.scale <= 2.0


def test_summarize_reports_baseline_and_sized_risk_metrics() -> None:
    bars = _sizing_fixture()
    config = FundingCarryConfig(k=1)
    summary = summarize_risk_sized(
        run_risk_sized_backtest(bars, config, vol_lookback_hours=3, vol_target_window_hours=32),
        config,
    )

    assert summary.n_rebalances > 0
    assert summary.baseline_max_drawdown_bps >= 0.0
    assert summary.sized_max_drawdown_bps >= 0.0
    assert np.isfinite(summary.baseline_net_pnl_bps)
    assert np.isfinite(summary.sized_net_pnl_bps)


def test_fails_closed_on_invalid_windows_and_scale_bounds() -> None:
    bars = _sizing_fixture()
    config = FundingCarryConfig(k=1)
    with pytest.raises(PositionSizingError, match="vol windows"):
        run_risk_sized_backtest(bars, config, vol_lookback_hours=0)
    with pytest.raises(PositionSizingError, match="scale_min"):
        run_risk_sized_backtest(bars, config, scale_min=0.0)
    with pytest.raises(PositionSizingError, match="scale_min"):
        run_risk_sized_backtest(bars, config, scale_min=3.0, scale_max=2.0)


def test_summarize_fails_closed_on_empty() -> None:
    with pytest.raises(PositionSizingError, match="no resolved"):
        summarize_risk_sized((), FundingCarryConfig(k=1))
