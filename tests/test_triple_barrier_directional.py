from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.triple_barrier import (  # noqa: E402
    BarrierOutcome,
    BarrierSide,
    TripleBarrierConfig,
    TripleBarrierError,
    label_directional_triple_barrier,
)

HOUR_MS = 60 * 60 * 1000


def _series(values: list[float], *, step_ms: int = HOUR_MS) -> tuple[pd.Series, pd.Series]:
    zscores = pd.Series(values, dtype="float64")
    open_time = pd.Series([i * step_ms for i in range(len(values))], dtype="int64")
    return zscores, open_time


def test_short_spread_resolves_profit_when_zscore_reverts() -> None:
    # entry at index 0 (z=2.5, SHORT_SPREAD), reverts to 0 by index 2
    zscores, open_time = _series([2.5, 1.5, 0.0, 0.0])
    config = TripleBarrierConfig(entry_zscore=2.0, profit_zscore=0.0, stop_zscore_buffer=1.0)

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert len(labels) == 1
    label = labels[0]
    assert label.side is BarrierSide.SHORT_SPREAD
    assert label.outcome is BarrierOutcome.PROFIT
    assert label.exit_index == 2
    assert label.bars_held == 2


def test_long_spread_resolves_profit_when_zscore_rises() -> None:
    # entry at index 0 (z=-2.5, LONG_SPREAD), rises to 0 by index 1
    zscores, open_time = _series([-2.5, 0.0, 0.0])
    config = TripleBarrierConfig(entry_zscore=2.0, profit_zscore=0.0, stop_zscore_buffer=1.0)

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert len(labels) == 1
    label = labels[0]
    assert label.side is BarrierSide.LONG_SPREAD
    assert label.outcome is BarrierOutcome.PROFIT
    assert label.exit_index == 1


def test_short_spread_resolves_stop_before_profit_on_adverse_move() -> None:
    # entry z=2.0, stop buffer=1.0 -> stop at z>=3.0; z rises to 3.2 first.
    # index 1 (z=3.2) also crosses the entry threshold and becomes its own
    # entry -- only the FIRST label (entry_index=0) is asserted here.
    zscores, open_time = _series([2.0, 3.2, 0.0])
    config = TripleBarrierConfig(entry_zscore=2.0, profit_zscore=0.0, stop_zscore_buffer=1.0)

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert labels[0].entry_index == 0
    assert labels[0].outcome is BarrierOutcome.STOP
    assert labels[0].exit_index == 1


def test_vertical_barrier_when_neither_profit_nor_stop_touched() -> None:
    # every bar stays >= entry_zscore, so each index also becomes its own
    # entry; only the FIRST label (entry_index=0) is asserted here.
    zscores, open_time = _series([2.0, 2.1, 2.05, 2.0, 2.02, 2.01])
    config = TripleBarrierConfig(
        entry_zscore=2.0,
        profit_zscore=0.0,
        stop_zscore_buffer=5.0,
        half_life_hours=1.0,
        half_life_multiplier=2.0,
    )

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert labels[0].entry_index == 0
    assert labels[0].outcome is BarrierOutcome.VERTICAL
    assert labels[0].bars_held == config.vertical_barrier_bars


def test_no_data_when_entry_is_too_close_to_series_end() -> None:
    zscores, open_time = _series([1.0, 1.0, 1.0, 2.5])
    config = TripleBarrierConfig(entry_zscore=2.0, half_life_hours=10.0, half_life_multiplier=4.0)

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert len(labels) == 1
    assert labels[0].outcome is BarrierOutcome.NO_DATA
    assert labels[0].exit_index is None


def test_sub_threshold_zscore_generates_no_entry() -> None:
    zscores, open_time = _series([0.5, -0.5, 1.9, -1.9])
    config = TripleBarrierConfig(entry_zscore=2.0)

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert labels == ()


def test_barrier_resolution_is_causal_relative_to_truncated_series() -> None:
    """Truncating the series right at the resolution point must not change
    the outcome up to that point -- the barrier never reads beyond what is
    actually supplied to it."""

    full_values = [2.5, 2.2, 1.8, 0.5, 0.0, -5.0, -5.0]
    truncated_values = full_values[:5]
    config = TripleBarrierConfig(entry_zscore=2.0, profit_zscore=0.0, stop_zscore_buffer=10.0)

    full_zscores, full_times = _series(full_values)
    truncated_zscores, truncated_times = _series(truncated_values)

    full_labels = label_directional_triple_barrier(full_zscores, full_times, config)
    truncated_labels = label_directional_triple_barrier(truncated_zscores, truncated_times, config)

    assert full_labels[0] == truncated_labels[0]


def test_mismatched_lengths_fail_closed() -> None:
    zscores = pd.Series([1.0, 2.0])
    open_time = pd.Series([0])

    with pytest.raises(TripleBarrierError):
        label_directional_triple_barrier(zscores, open_time, TripleBarrierConfig())


def test_vertical_barrier_bars_derived_from_half_life_and_capped() -> None:
    config = TripleBarrierConfig(half_life_hours=100.0, half_life_multiplier=4.0, max_vertical_bars=50)

    assert config.vertical_barrier_bars == 50


def test_vertical_barrier_scales_sub_hour_duration_by_bar_duration() -> None:
    # half_life * multiplier = 0.25h. At 5-minute bars, that is 3 bars, not
    # one full hour. A prior bug rounded the duration up to 1h before applying
    # it against open_time.
    five_minute_ms = 5 * 60 * 1000
    zscores, open_time = _series([2.5, 2.4, 2.3, 2.2, 2.1], step_ms=five_minute_ms)
    config = TripleBarrierConfig(
        entry_zscore=2.0,
        profit_zscore=0.0,
        stop_zscore_buffer=10.0,
        half_life_hours=0.25,
        half_life_multiplier=1.0,
        bar_duration_hours=1.0 / 12.0,
    )

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert config.vertical_barrier_bars == 3
    assert labels[0].outcome is BarrierOutcome.VERTICAL
    assert labels[0].bars_held == 3
    assert labels[0].exit_time == 15 * 60 * 1000


def test_invalid_config_fails_closed() -> None:
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(entry_zscore=-1.0)
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(max_vertical_bars=0)
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(stop_zscore_buffer=-1.0)
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(half_life_hours=-1.0)
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(half_life_multiplier=-1.0)
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(max_vertical_bars=1.5)
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(bar_duration_hours=0.0)


def test_profit_zscore_outside_entry_bounds_fails_closed() -> None:
    # profit_zscore=3.0 &gt;= entry_zscore=2.0 would let PROFIT swallow the
    # entire intended STOP zone (stop_zscore = entry + buffer), silently
    # disabling risk control -- reject at construction instead.
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(entry_zscore=2.0, profit_zscore=3.0, stop_zscore_buffer=1.0)
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(entry_zscore=2.0, profit_zscore=-2.0)


def test_extreme_half_life_product_overflow_fails_closed() -> None:
    with pytest.raises(TripleBarrierError):
        TripleBarrierConfig(half_life_hours=1e300, half_life_multiplier=1e300)


def test_open_time_with_nan_fails_closed() -> None:
    zscores, _ = _series([2.5, 0.0, 0.0])
    open_time = pd.Series([0.0, float("nan"), 2.0 * HOUR_MS])

    with pytest.raises(TripleBarrierError):
        label_directional_triple_barrier(zscores, open_time, TripleBarrierConfig())


def test_no_data_when_only_a_partial_window_is_available() -> None:
    """Fewer future bars exist than the vertical-barrier duration requires,
    and neither PROFIT nor STOP is hit within what IS available -- must fail
    closed to NO_DATA rather than fabricate an early VERTICAL exit."""

    # vertical_barrier_bars = ceil(1.0 * 4.0) = 4, but only 2 bars follow entry.
    zscores, open_time = _series([2.5, 2.2, 1.8])
    config = TripleBarrierConfig(entry_zscore=2.0, profit_zscore=0.0, stop_zscore_buffer=10.0)

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert labels[0].outcome is BarrierOutcome.NO_DATA
    assert labels[0].exit_index is None


def test_vertical_barrier_uses_elapsed_time_not_bar_count_across_a_gap() -> None:
    """A data gap must not let a post-gap bar masquerade as 'N bars later' --
    the vertical barrier is a target duration, resolved via actual elapsed
    time in open_time, not array-position offsets."""

    # entry at t=0 (z=2.5, SHORT_SPREAD); vertical_barrier_bars = 2 hours.
    # The only future bar is 100 hours later -- far past the 2-hour budget,
    # and neither PROFIT nor STOP is touched at that single future point.
    zscores = pd.Series([2.5, 0.0])
    open_time = pd.Series([0, 100 * HOUR_MS], dtype="int64")
    config = TripleBarrierConfig(
        entry_zscore=2.0,
        profit_zscore=0.0,
        stop_zscore_buffer=10.0,
        half_life_hours=2.0,
        half_life_multiplier=1.0,
    )

    labels = label_directional_triple_barrier(zscores, open_time, config)

    assert labels[0].outcome is BarrierOutcome.VERTICAL
    assert labels[0].exit_index == 0
    assert labels[0].bars_held == 0
