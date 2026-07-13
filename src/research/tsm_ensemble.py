"""TASK-TSM-005: trend + carry ensemble diagnostic (ADR-0031, Line 5).

Blends two return STREAMS -- the vol-targeted TSM (trend) and the funding-carry
K=5 incremental (carry) -- at a common weekly frequency, standardized to unit
risk and combined equal-risk (50/50), then compares the blend's Sharpe to the
TSM alone. Trend and carry are the canonical diversifying CTA return sources
(Koijen-Moskowitz-Pedersen-Vrugt "Carry"; AQR trend+carry). Development
diagnostic only -- promotion is OOS-gated (and carry already printed a negative
first OOS month, so any dev benefit is provisional).

Pure functions (weekly bucketing, standardized equal-risk blend, annualized
Sharpe, max drawdown) are unit-tested; no I/O or backtest here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

WEEKS_PER_YEAR = 52
_MS = "ms"
_MIN_OBS = 2


class TsmEnsembleError(ValueError):
    """Raised when ensemble inputs are invalid."""


@dataclass(frozen=True, slots=True)
class BlendSummary:
    n_weeks: int
    tsm_sharpe: float
    carry_sharpe: float
    blend_sharpe: float
    correlation: float
    tsm_max_drawdown: float
    blend_max_drawdown: float


def weekly_pnl(times_ms: object, pnl: object) -> pd.Series:
    """Sum a (decision_time_ms, pnl) stream into calendar-week (W-MON) buckets."""

    t = np.asarray(times_ms, dtype="int64")
    p = np.asarray(pnl, dtype="float64")
    if len(t) != len(p):
        raise TsmEnsembleError("times and pnl length mismatch")
    if len(t) == 0:
        return pd.Series(dtype="float64")
    ts = pd.to_datetime(t, unit=_MS)  # naive UTC (epoch ms) -> no tz warning
    week = ts.to_period("W").start_time  # Monday-start calendar weeks
    return pd.Series(p, index=week).groupby(level=0).sum().sort_index()


def _annualized_sharpe(returns: np.ndarray) -> float:
    if len(returns) < _MIN_OBS:
        return float("nan")
    std = returns.std(ddof=1)
    if not np.isfinite(std) or std == 0.0:
        return float("nan")
    return float(returns.mean() / std * math.sqrt(WEEKS_PER_YEAR))


def _max_drawdown(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    equity = np.cumsum(returns)
    running_max = np.maximum.accumulate(equity)
    return float(np.max(running_max - equity))


def blend_diagnostic(tsm_weekly: pd.Series, carry_weekly: pd.Series) -> BlendSummary:
    """Equal-risk 50/50 blend of two weekly streams; Sharpe/corr/drawdown vs TSM.

    Each stream is standardized to unit in-sample volatility (scale-invariant),
    so the blend is a genuine equal-RISK combination regardless of the streams'
    native units (fractional TSM returns vs carry bps).
    """

    joined = pd.concat({"tsm": tsm_weekly, "carry": carry_weekly}, axis=1, join="inner").dropna()
    if len(joined) < _MIN_OBS:
        raise TsmEnsembleError("fewer than 2 overlapping weeks")
    tsm = joined["tsm"].to_numpy()
    carry = joined["carry"].to_numpy()

    tsm_std = tsm.std(ddof=1)
    carry_std = carry.std(ddof=1)
    if tsm_std == 0.0 or carry_std == 0.0:
        raise TsmEnsembleError("a stream has zero volatility")
    blend = 0.5 * (tsm / tsm_std) + 0.5 * (carry / carry_std)

    corr = float(np.corrcoef(tsm, carry)[0, 1])
    return BlendSummary(
        n_weeks=len(joined),
        tsm_sharpe=_annualized_sharpe(tsm),
        carry_sharpe=_annualized_sharpe(carry),
        blend_sharpe=_annualized_sharpe(blend),
        correlation=corr,
        tsm_max_drawdown=_max_drawdown(tsm / tsm_std),
        blend_max_drawdown=_max_drawdown(blend),
    )
