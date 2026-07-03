"""Directional triple-barrier labeling for pair-spread mean reversion.

Implements the roadmap's Sprint 8 canonical exit logic (`project_control/ROADMAP.md`,
see `project_control/DECISIONS.md` ADR-0009): a SHORT_SPREAD position profits
if the spread z-score falls back toward the mean and stops out if it rises
further; a LONG_SPREAD position profits if the z-score rises and stops out
if it falls further. A vertical barrier (a bar-count cap derived from the
pair's OU half-life) resolves positions that never hit profit or stop.

No look-ahead in the entry decision: entries are only considered at indices
where a causal z-score (already shifted, e.g. `src.research.ou.rolling_zscore`)
crosses the entry threshold. Barrier RESOLUTION legitimately scans forward
through bars that already exist in the historical dataset -- this is standard
backtest label resolution (the same category as Sprint 8/9's "look at the
next known bar to price a already-causally-generated signal"), not look-ahead
in the sense this project prohibits for signal generation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd

HOUR_MS = 60 * 60 * 1000
DEFAULT_ENTRY_ZSCORE = 2.0
DEFAULT_PROFIT_ZSCORE = 0.0
DEFAULT_STOP_ZSCORE_BUFFER = 1.0
DEFAULT_HALF_LIFE_MULTIPLIER = 4.0
DEFAULT_MAX_VERTICAL_BARS = 240
MIN_VERTICAL_BARS = 1


class BarrierSide(StrEnum):
    """Direction of a triple-barrier position on the spread."""

    LONG_SPREAD = "LONG_SPREAD"
    SHORT_SPREAD = "SHORT_SPREAD"


class BarrierOutcome(StrEnum):
    """Which of the three barriers resolved the position."""

    PROFIT = "PROFIT"
    STOP = "STOP"
    VERTICAL = "VERTICAL"
    NO_DATA = "NO_DATA"


class TripleBarrierError(ValueError):
    """Raised when triple-barrier inputs are invalid."""


@dataclass(frozen=True, slots=True)
class TripleBarrierConfig:
    """Thresholds controlling directional triple-barrier labeling."""

    entry_zscore: float = DEFAULT_ENTRY_ZSCORE
    profit_zscore: float = DEFAULT_PROFIT_ZSCORE
    stop_zscore_buffer: float = DEFAULT_STOP_ZSCORE_BUFFER
    half_life_hours: float = 1.0
    half_life_multiplier: float = DEFAULT_HALF_LIFE_MULTIPLIER
    max_vertical_bars: int = DEFAULT_MAX_VERTICAL_BARS
    bar_duration_hours: float = 1.0

    def __post_init__(self) -> None:
        _positive_finite("entry_zscore", self.entry_zscore)
        _finite("profit_zscore", self.profit_zscore)
        _positive_finite("stop_zscore_buffer", self.stop_zscore_buffer)
        _positive_finite("half_life_hours", self.half_life_hours)
        _positive_finite("half_life_multiplier", self.half_life_multiplier)
        if isinstance(self.max_vertical_bars, bool) or not isinstance(self.max_vertical_bars, int):
            raise TripleBarrierError("max_vertical_bars must be an integer")
        if self.max_vertical_bars < MIN_VERTICAL_BARS:
            raise TripleBarrierError("max_vertical_bars must be at least 1")
        if not -self.entry_zscore < self.profit_zscore < self.entry_zscore:
            raise TripleBarrierError(
                "profit_zscore must fall strictly between -entry_zscore and entry_zscore, "
                "otherwise it can overlap or invert the stop zone"
            )
        if not math.isfinite(self.half_life_hours * self.half_life_multiplier):
            raise TripleBarrierError("half_life_hours * half_life_multiplier must be finite")
        _positive_finite("bar_duration_hours", self.bar_duration_hours)

    @property
    def vertical_barrier_bars(self) -> int:
        """Bar-count cap for the vertical barrier, derived from half-life."""

        raw_hours = self.half_life_hours * self.half_life_multiplier
        raw = math.ceil(raw_hours / self.bar_duration_hours)
        return max(MIN_VERTICAL_BARS, min(raw, self.max_vertical_bars))


@dataclass(frozen=True, slots=True)
class TripleBarrierLabel:
    """Resolved outcome of one directional triple-barrier position."""

    entry_index: int
    entry_time: int
    side: BarrierSide
    entry_zscore: float
    outcome: BarrierOutcome
    exit_index: int | None
    exit_time: int | None
    exit_zscore: float | None
    bars_held: int


def label_directional_triple_barrier(
    zscores: pd.Series,
    open_time: pd.Series,
    config: TripleBarrierConfig,
) -> tuple[TripleBarrierLabel, ...]:
    """Label every causal entry crossing with a directional triple barrier.

    ``zscores`` must already be causal (e.g. shifted rolling z-score with
    ``lookahead_safe`` attrs set by ``src.research.ou.rolling_zscore``); this
    function does not itself enforce that -- it only consumes whatever series
    it is given, entry index by entry index, and never reads beyond the
    supplied series when resolving a barrier.
    """

    if len(zscores) != len(open_time):
        raise TripleBarrierError("zscores and open_time must have the same length")
    numeric_open_time = pd.to_numeric(open_time, errors="coerce")
    if numeric_open_time.isna().any():
        raise TripleBarrierError("open_time must not contain NaN or non-numeric values")
    int64_bounds = np.iinfo(np.int64)
    if ((numeric_open_time < int64_bounds.min) | (numeric_open_time > int64_bounds.max)).any():
        raise TripleBarrierError("open_time must fit within int64 range")
    values = zscores.to_numpy(dtype=float)
    times = numeric_open_time.to_numpy(dtype=np.int64)
    labels = []
    for index, zscore in enumerate(values):
        if not math.isfinite(zscore) or abs(zscore) < config.entry_zscore:
            continue
        side = BarrierSide.SHORT_SPREAD if zscore > 0.0 else BarrierSide.LONG_SPREAD
        labels.append(
            _resolve_barrier(
                values=values,
                times=times,
                entry_index=index,
                side=side,
                entry_zscore=float(zscore),
                config=config,
            )
        )
    return tuple(labels)


def _resolve_barrier(
    *,
    values: np.ndarray,
    times: np.ndarray,
    entry_index: int,
    side: BarrierSide,
    entry_zscore: float,
    config: TripleBarrierConfig,
) -> TripleBarrierLabel:
    """Scan forward for PROFIT/STOP within a duration derived from a bar cap.

    The vertical barrier is a target holding duration
    (``vertical_barrier_bars * bar_duration_hours``), evaluated against actual
    elapsed wall-clock time via ``times`` rather than array-position offsets.
    This matters because the upstream pair-alignment join drops any period
    missing on either leg, so array position and elapsed time silently diverge
    whenever real data has gaps -- treating a post-gap bar as "N bars later"
    would understate how long the position was actually held.

    Fails closed to NO_DATA (rather than fabricating an early VERTICAL exit)
    whenever the series runs out before the target duration is confirmed
    reached, unless PROFIT or STOP already resolved the position first.
    """

    entry_time = int(times[entry_index])
    target_elapsed_ms = math.ceil(
        config.vertical_barrier_bars * config.bar_duration_hours * HOUR_MS
    )
    stop_zscore = (
        entry_zscore + config.stop_zscore_buffer
        if side is BarrierSide.SHORT_SPREAD
        else entry_zscore - config.stop_zscore_buffer
    )

    last_within_budget_index = entry_index
    reached_time_budget = False
    for future_index in range(entry_index + 1, len(values)):
        elapsed_ms = int(times[future_index]) - entry_time
        if elapsed_ms > target_elapsed_ms:
            reached_time_budget = True
            break
        last_within_budget_index = future_index
        future_z = values[future_index]
        if not math.isfinite(future_z):
            continue
        outcome = _check_barriers(
            side=side,
            zscore=future_z,
            profit_zscore=config.profit_zscore,
            stop_zscore=stop_zscore,
        )
        if outcome is not None:
            return TripleBarrierLabel(
                entry_index=entry_index,
                entry_time=entry_time,
                side=side,
                entry_zscore=entry_zscore,
                outcome=outcome,
                exit_index=future_index,
                exit_time=int(times[future_index]),
                exit_zscore=float(future_z),
                bars_held=future_index - entry_index,
            )

    if not reached_time_budget:
        return TripleBarrierLabel(
            entry_index=entry_index,
            entry_time=entry_time,
            side=side,
            entry_zscore=entry_zscore,
            outcome=BarrierOutcome.NO_DATA,
            exit_index=None,
            exit_time=None,
            exit_zscore=None,
            bars_held=0,
        )

    exit_zscore = values[last_within_budget_index]
    return TripleBarrierLabel(
        entry_index=entry_index,
        entry_time=entry_time,
        side=side,
        entry_zscore=entry_zscore,
        outcome=BarrierOutcome.VERTICAL,
        exit_index=last_within_budget_index,
        exit_time=int(times[last_within_budget_index]),
        exit_zscore=float(exit_zscore) if math.isfinite(exit_zscore) else None,
        bars_held=last_within_budget_index - entry_index,
    )


def _check_barriers(
    *,
    side: BarrierSide,
    zscore: float,
    profit_zscore: float,
    stop_zscore: float,
) -> BarrierOutcome | None:
    if side is BarrierSide.SHORT_SPREAD:
        if zscore <= profit_zscore:
            return BarrierOutcome.PROFIT
        if zscore >= stop_zscore:
            return BarrierOutcome.STOP
        return None
    if zscore >= profit_zscore:
        return BarrierOutcome.PROFIT
    if zscore <= stop_zscore:
        return BarrierOutcome.STOP
    return None


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TripleBarrierError(f"{name} must be numeric")
    if not math.isfinite(value):
        raise TripleBarrierError(f"{name} must be finite")
    return float(value)


def _positive_finite(name: str, value: float) -> float:
    _finite(name, value)
    if value <= 0.0:
        raise TripleBarrierError(f"{name} must be positive")
    return float(value)


__all__ = [
    "BarrierOutcome",
    "BarrierSide",
    "TripleBarrierConfig",
    "TripleBarrierError",
    "TripleBarrierLabel",
    "label_directional_triple_barrier",
]
