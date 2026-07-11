"""Classic volatility-targeted time-series momentum (TASK-FC-II-005).

Pre-registered in `docs/pre_registers/TASK-FC-II-005.md` (ADR-0027). Distinct
from `tsmom_breakout.py` (Donchian + ATR stop): here the position is the SIGN
of the trailing return, sized inverse to realized volatility and normalized to
unit gross exposure (knob-free risk-parity trend), rebalanced on a fixed grid.
The external literature attributes trend profitability to vol-targeting, which
our Donchian TSMOM lacked; this tests that claim on the data we already have.

Development-window backtest; risk-adjusted metrics only, no promotion verdict
(gate, if warranted, is on untouched OOS). All inputs causal: the trailing
return uses a lag and realized vol uses shift(1) before rolling; the forward
interval return is the only forward-looking term.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

_HOURS_PER_YEAR = 24 * 365
_MIN_OBS_FOR_SHARPE = 2

__all__ = [
    "TsmTrendConfig",
    "TsmTrendResult",
    "TsmTrendSummary",
    "run_tsm_trend_backtest",
    "summarize_tsm_trend",
]


class TsmTrendError(ValueError):
    """Raised when TSM trend inputs are invalid."""


@dataclass(frozen=True, slots=True)
class TsmTrendConfig:
    lookback_hours: int = 672  # 28d trailing-return signal
    vol_window_hours: int = 168  # 7d realized-vol window
    hold_hours: int = 120  # 5d rebalance/hold
    cost_bps_per_leg: float = 6.0
    include_funding: bool = False  # add perp funding P&L over each hold (FC-II-008)

    def __post_init__(self) -> None:
        for name in ("lookback_hours", "vol_window_hours", "hold_hours"):
            if getattr(self, name) < 1:
                raise TsmTrendError(f"{name} must be >= 1")
        if not math.isfinite(self.cost_bps_per_leg) or self.cost_bps_per_leg < 0:
            raise TsmTrendError("cost_bps_per_leg must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class TsmTrendResult:
    rebalance_times: tuple[int, ...]
    tsm_net: tuple[float, ...]  # long/short vol-targeted, net of cost
    tsm_long_only_net: tuple[float, ...]
    baseline: tuple[float, ...]  # equal-weight buy-and-hold (reference)
    tsm_turnover: tuple[float, ...]  # sum|dw| per rebalance (long/short book)
    tsm_long_sleeve: tuple[float, ...]  # long-leg gross contribution (same book)
    tsm_short_sleeve: tuple[float, ...]  # short-leg gross contribution (sums to gross)


@dataclass(frozen=True, slots=True)
class TsmTrendSummary:
    n_rebalances: int
    tsm_sharpe: float
    tsm_long_only_sharpe: float
    baseline_sharpe: float
    tsm_max_drawdown: float
    baseline_max_drawdown: float
    tsm_net_pnl: float
    baseline_net_pnl: float
    mean_turnover: float


def run_tsm_trend_backtest(bars: pd.DataFrame, config: TsmTrendConfig) -> TsmTrendResult:
    """Vectorized classic vol-targeted TSM on hourly bars."""

    required = {"symbol", "open_time", "log_price"}
    if config.include_funding:
        required |= {"funding_rate_asof", "funding_interval_hours"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise TsmTrendError(f"missing required columns: {missing}")
    if bars.duplicated(["symbol", "open_time"]).any():
        raise TsmTrendError("duplicate (symbol, open_time) rows")

    price = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    hourly_return = price.diff()
    vol = hourly_return.shift(1).rolling(config.vol_window_hours).std()
    trailing = price - price.shift(config.lookback_hours)

    rows = price.index[:: config.hold_hours]
    price_r = price.loc[rows]
    trailing_r = trailing.loc[rows]
    vol_r = vol.loc[rows]
    forward_r = price_r.shift(-1) - price_r  # interval return per leg
    # Funding paid/received over each hold (realized, like forward_r): sum of
    # per-settlement rates, spread hourly then differenced between rebalances.
    funding_hold = _funding_over_hold(bars, price, rows) if config.include_funding else None

    ls_weight = _unit_gross(np.sign(trailing_r) / vol_r)
    lo_weight = _unit_gross(np.maximum(np.sign(trailing_r), 0.0) / vol_r)
    base_weight = _unit_gross(price_r.notna().astype(float))  # equal-weight long

    tsm_gross = (ls_weight * forward_r).sum(axis=1, skipna=True)
    long_sleeve = (ls_weight.clip(lower=0.0) * forward_r).sum(axis=1, skipna=True)
    short_sleeve = (ls_weight.clip(upper=0.0) * forward_r).sum(axis=1, skipna=True)
    lo_gross = (lo_weight * forward_r).sum(axis=1, skipna=True)
    baseline = (base_weight * forward_r).sum(axis=1, skipna=True)

    if funding_hold is not None:
        # Funding P&L of a signed-weight position per settlement is -w * rate
        # (long pays when rate>0; short receives). Reused from leg_pnl_fracs.
        tsm_gross = tsm_gross - (ls_weight * funding_hold).sum(axis=1, skipna=True)
        long_sleeve = long_sleeve - (ls_weight.clip(lower=0.0) * funding_hold).sum(
            axis=1, skipna=True
        )
        short_sleeve = short_sleeve - (ls_weight.clip(upper=0.0) * funding_hold).sum(
            axis=1, skipna=True
        )
        lo_gross = lo_gross - (lo_weight * funding_hold).sum(axis=1, skipna=True)

    ls_turnover = ls_weight.diff().abs().sum(axis=1, skipna=True)
    lo_turnover = lo_weight.diff().abs().sum(axis=1, skipna=True)
    cost = config.cost_bps_per_leg / 10_000.0
    tsm_net = tsm_gross - ls_turnover * cost
    lo_net = lo_gross - lo_turnover * cost

    valid = forward_r.notna().any(axis=1)  # drop the final row (no forward)
    times = tuple(int(t) for t in rows[valid])
    return TsmTrendResult(
        rebalance_times=times,
        tsm_net=tuple(float(x) for x in tsm_net[valid]),
        tsm_long_only_net=tuple(float(x) for x in lo_net[valid]),
        baseline=tuple(float(x) for x in baseline[valid]),
        tsm_turnover=tuple(float(x) for x in ls_turnover[valid]),
        tsm_long_sleeve=tuple(float(x) for x in long_sleeve[valid]),
        tsm_short_sleeve=tuple(float(x) for x in short_sleeve[valid]),
    )


def _unit_gross(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize each row so sum of |weight| == 1; all-zero/NaN rows -> 0."""

    clean = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    gross = clean.abs().sum(axis=1)
    normalized = clean.div(gross, axis=0)
    return normalized.fillna(0.0)


def _funding_over_hold(bars: pd.DataFrame, price: pd.DataFrame, rows: pd.Index) -> pd.DataFrame:
    """Sum of per-settlement funding rates over each hold, per symbol.

    Spreads each settled rate hourly (rate / funding_interval_hours) then sums
    between consecutive rebalances via a differenced cumulative -- same shape as
    the forward return, so it aligns element-wise with the rebalance weights.
    """

    funding = bars.pivot(index="open_time", columns="symbol", values="funding_rate_asof")
    interval = bars.pivot(index="open_time", columns="symbol", values="funding_interval_hours")
    hourly = (
        (funding / interval.replace(0.0, np.nan))
        .reindex(index=price.index, columns=price.columns)
        .fillna(0.0)
    )
    cum = hourly.cumsum().reindex(rows)
    return cum.shift(-1) - cum


def summarize_tsm_trend(result: TsmTrendResult, config: TsmTrendConfig) -> TsmTrendSummary:
    if not result.rebalance_times:
        raise TsmTrendError("no rebalances to summarize")
    tsm = np.array(result.tsm_net)
    lo = np.array(result.tsm_long_only_net)
    base = np.array(result.baseline)
    turnover = np.array(result.tsm_turnover)
    ann = math.sqrt(_HOURS_PER_YEAR / config.hold_hours)
    return TsmTrendSummary(
        n_rebalances=len(tsm),
        tsm_sharpe=_sharpe(tsm, ann),
        tsm_long_only_sharpe=_sharpe(lo, ann),
        baseline_sharpe=_sharpe(base, ann),
        tsm_max_drawdown=_max_drawdown(tsm),
        baseline_max_drawdown=_max_drawdown(base),
        tsm_net_pnl=float(tsm.sum()),
        baseline_net_pnl=float(base.sum()),
        mean_turnover=float(turnover.mean()) if len(turnover) else float("nan"),
    )


def _sharpe(returns: np.ndarray, annualization: float) -> float:
    if len(returns) < _MIN_OBS_FOR_SHARPE:
        return float("nan")
    std = returns.std(ddof=1)
    if not np.isfinite(std) or std == 0.0:
        return float("nan")
    return float(returns.mean() / std * annualization)


def _max_drawdown(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    equity = np.cumsum(returns)
    running_max = np.maximum.accumulate(equity)
    return float(np.max(running_max - equity))
