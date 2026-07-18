"""Canonical drawdown computation with explicit unit semantics (TASK-DEPLOY-001, Phase 1).

Two DISTINCT framings, never conflated:

- COMPOUNDED (canonical, the one "maxDD" and "%" normally mean):
      equity = (1 + returns).cumprod()
      drawdown = equity / running_peak - 1        # fractional, e.g. -0.55 = -55%
  This assumes P&L is REINVESTED (bet size scales with equity). A return <= -1
  drives equity non-positive -> drawdown <= -100%; that state is flagged.

- ADDITIVE / fixed-notional (what the TSM validation scripts actually reported
  via np.cumsum): equity is the cumulative sum of per-rebalance returns, i.e.
  cumulative P&L measured in units of ONE unit of (constant) gross notional.
      equity = returns.cumsum()
      drawdown = equity - running_peak            # in return units, NOT a percent
  A 0.80 additive drawdown means cumulative losses reached 0.80 of one unit of
  gross exposure -- it is NOT an 80% equity drawdown.

This module does not touch any strategy signal, weight, or parameter -- it only
measures a return stream. NaN returns are treated as 0.0 (no P&L that bar) and
flagged; this keeps the equity curve aligned with any timestamp vector.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

__all__ = ["DrawdownStats", "compute_drawdown"]


@dataclass(frozen=True, slots=True)
class DrawdownStats:
    mode: str  # "compounded" | "additive"
    n: int
    max_drawdown: float  # POSITIVE magnitude; fraction (compounded) or return-units (additive)
    max_drawdown_percent: float | None  # compounded only (×100); None for additive
    peak_index: int | None
    trough_index: int | None
    recovery_index: int | None  # None if never recovered to the peak
    unrecovered: bool
    peak_equity: float | None
    trough_equity: float | None
    peak_timestamp: str | None
    trough_timestamp: str | None
    recovery_timestamp: str | None
    duration_bars: int  # peak -> recovery (or peak -> end if unrecovered)
    time_underwater_fraction: float
    had_nan: bool
    equity_non_positive: bool  # compounded only: a return <= -1 wiped equity

    def as_dict(self) -> dict:
        return asdict(self)


def _ts(times: np.ndarray | None, idx: int | None) -> str | None:
    if times is None or idx is None:
        return None
    return pd.Timestamp(int(times[idx]), unit="ms", tz="UTC").isoformat()


def compute_drawdown(returns, times=None, *, compound: bool = True) -> DrawdownStats:
    """Drawdown of a per-period return stream.

    `compound=True` -> compounded fractional drawdown (canonical). `False` ->
    additive fixed-notional drawdown (the np.cumsum framing). `times` (ms) is
    optional; when given, peak/trough/recovery timestamps are filled.
    """

    r = np.asarray(returns, dtype=float)
    had_nan = bool(np.isnan(r).any())
    r = np.nan_to_num(r, nan=0.0)
    mode = "compounded" if compound else "additive"
    if r.size == 0:
        return DrawdownStats(
            mode, 0, 0.0, 0.0 if compound else None, None, None, None, False,
            None, None, None, None, None, 0, 0.0, had_nan, False,
        )  # fmt: skip

    if compound:
        equity = np.cumprod(1.0 + r)
        equity_non_positive = bool(np.any(equity <= 0.0))
        running_peak = np.maximum.accumulate(equity)
        dd = equity / running_peak - 1.0  # <= 0
    else:
        equity = np.cumsum(r)
        equity_non_positive = False
        running_peak = np.maximum.accumulate(equity)
        dd = equity - running_peak  # <= 0, in return units

    trough_index = int(np.argmin(dd))
    max_dd = float(-dd[trough_index])
    if max_dd <= 0.0:  # no drawdown at all (monotone non-decreasing)
        tw = float(np.mean(equity < running_peak))
        return DrawdownStats(
            mode, r.size, 0.0, 0.0 if compound else None, None, None, None, False,
            None, None, None, None, None, 0, tw, had_nan, equity_non_positive,
        )  # fmt: skip

    peak_index = int(np.argmax(equity[: trough_index + 1]))
    peak_equity = float(equity[peak_index])
    # recovery: first bar after the trough that regains the peak equity
    after = np.where(equity[trough_index + 1 :] >= peak_equity)[0]
    recovery_index = int(after[0] + trough_index + 1) if after.size else None
    unrecovered = recovery_index is None
    end_index = recovery_index if recovery_index is not None else r.size - 1
    duration_bars = int(end_index - peak_index)
    time_underwater = float(np.mean(equity < running_peak))

    return DrawdownStats(
        mode=mode,
        n=r.size,
        max_drawdown=max_dd,
        max_drawdown_percent=max_dd * 100.0 if compound else None,
        peak_index=peak_index,
        trough_index=trough_index,
        recovery_index=recovery_index,
        unrecovered=unrecovered,
        peak_equity=peak_equity,
        trough_equity=float(equity[trough_index]),
        peak_timestamp=_ts(times, peak_index),
        trough_timestamp=_ts(times, trough_index),
        recovery_timestamp=_ts(times, recovery_index),
        duration_bars=duration_bars,
        time_underwater_fraction=time_underwater,
        had_nan=had_nan,
        equity_non_positive=equity_non_positive,
    )
