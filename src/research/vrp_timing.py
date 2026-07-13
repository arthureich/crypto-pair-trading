"""TASK-ALT-012: variance-risk-premium timing strategy for BTC/ETH (ADR-0032).

The ALT-011 hit (`vrp_z@7d` predicts forward returns) tested AS A STRATEGY: a
weekly (non-overlapping) book that goes long an asset when its VRP is above its
trailing average (vrp_z > 0) and short when below, unit-gross across BTC/ETH,
net of cost -- correcting the overlapping-sample bias of the decile economic
check. Development backtest; promotion is OOS-gated. Signal is causal
(`compute_vrp_z` mirrors the ALT-011 construction exactly, shift(1)); the
forward interval return is the only forward-looking term.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

_ANNUALIZE_DAYS = 365
_MIN_OBS_FOR_SHARPE = 2
DVOL_PERCENT = 100.0


class VrpTimingError(ValueError):
    """Raised when VRP-timing inputs are invalid."""


@dataclass(frozen=True, slots=True)
class VrpTimingConfig:
    hold_days: int = 7  # weekly, non-overlapping (matches the validated 7d horizon)
    cost_bps_per_leg: float = 6.0
    rv_window_days: int = 30
    z_window_days: int = 90
    long_only: bool = False  # secondary descriptive variant (long high-VRP, flat low)

    def __post_init__(self) -> None:
        for name in ("hold_days", "rv_window_days", "z_window_days"):
            if getattr(self, name) < 1:
                raise VrpTimingError(f"{name} must be >= 1")
        if not math.isfinite(self.cost_bps_per_leg) or self.cost_bps_per_leg < 0:
            raise VrpTimingError("cost_bps_per_leg must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class VrpTimingResult:
    rebalance_times: tuple[int, ...]
    strat_net: tuple[float, ...]
    baseline: tuple[float, ...]
    turnover: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class VrpTimingSummary:
    n_rebalances: int
    strat_sharpe: float
    baseline_sharpe: float
    strat_max_drawdown: float
    baseline_max_drawdown: float
    strat_net_pnl: float
    baseline_net_pnl: float
    mean_turnover: float


def compute_vrp_z(
    dvol_wide: pd.DataFrame, daily_logprice: pd.DataFrame, config: VrpTimingConfig
) -> pd.DataFrame:
    """Causal vrp_z, identical to the ALT-011 diagnostic (VRP=IV^2-RV^2, z, shift1)."""

    iv = dvol_wide / DVOL_PERCENT
    rv = daily_logprice.diff().rolling(config.rv_window_days).std() * math.sqrt(_ANNUALIZE_DAYS)
    vrp = iv**2 - rv**2
    mean = vrp.shift(1).rolling(config.z_window_days).mean()
    std = vrp.shift(1).rolling(config.z_window_days).std()
    return ((vrp - mean) / std).shift(1)


def run_vrp_timing_backtest(
    daily_logprice: pd.DataFrame, vrp_z: pd.DataFrame, config: VrpTimingConfig
) -> VrpTimingResult:
    """Weekly VRP-timing book over the daily BTC/ETH log-price + vrp_z panels."""

    if daily_logprice.empty:
        raise VrpTimingError("empty price panel")
    price = daily_logprice.sort_index()
    signal = vrp_z.reindex(index=price.index, columns=price.columns)

    rows = price.index[:: config.hold_days]
    price_r = price.loc[rows]
    signal_r = signal.loc[rows]
    forward_r = price_r.shift(-1) - price_r  # non-overlapping interval return per asset

    direction = np.sign(signal_r)
    if config.long_only:
        direction = direction.clip(lower=0.0)
    weight = _unit_gross(direction)
    base_weight = _unit_gross(price_r.notna().astype(float))  # equal-weight long buy-hold

    strat_gross = (weight * forward_r).sum(axis=1, skipna=True)
    baseline = (base_weight * forward_r).sum(axis=1, skipna=True)
    turnover = weight.diff().abs().sum(axis=1, skipna=True)
    cost = config.cost_bps_per_leg / 10_000.0
    strat_net = strat_gross - turnover * cost

    valid = forward_r.notna().any(axis=1)
    times = tuple(int(t) for t in rows[valid])
    return VrpTimingResult(
        rebalance_times=times,
        strat_net=tuple(float(x) for x in strat_net[valid]),
        baseline=tuple(float(x) for x in baseline[valid]),
        turnover=tuple(float(x) for x in turnover[valid]),
    )


def _unit_gross(raw: pd.DataFrame) -> pd.DataFrame:
    clean = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    gross = clean.abs().sum(axis=1)
    return clean.div(gross, axis=0).fillna(0.0)


def summarize_vrp_timing(result: VrpTimingResult, config: VrpTimingConfig) -> VrpTimingSummary:
    if not result.rebalance_times:
        raise VrpTimingError("no rebalances to summarize")
    strat = np.array(result.strat_net)
    base = np.array(result.baseline)
    turnover = np.array(result.turnover)
    ann = math.sqrt(_ANNUALIZE_DAYS / config.hold_days)
    return VrpTimingSummary(
        n_rebalances=len(strat),
        strat_sharpe=_sharpe(strat, ann),
        baseline_sharpe=_sharpe(base, ann),
        strat_max_drawdown=_max_drawdown(strat),
        baseline_max_drawdown=_max_drawdown(base),
        strat_net_pnl=float(strat.sum()),
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
