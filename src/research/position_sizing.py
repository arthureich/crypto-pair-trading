"""Risk-based position-sizing overlay for the funding-carry K=5 signal.

Pre-registered in `docs/pre_registers/TASK-FC-II-001.md` (ADR-0027,
"Funding Iteration 2"). Replaces the fixed equal 1/(2K) leg weights with:

  1. Inverse-volatility weighting WITHIN each side (calmer legs weigh more),
     renormalized so each side keeps 50% notional (dollar-neutral preserved).
  2. Whole-book volatility targeting to the equal-weight book's own trailing
     realized vol (self-referential -> average scale ~1, no leverage knob),
     with a fixed anti-blowup clamp.

This is a risk-management OVERLAY, not a new alpha claim: it never sizes by
funding magnitude and never changes which legs the primary policy selects.
The primary signal, leg selection, and cost model in `funding_carry.py` are
unchanged. Uniform vol-targeting is profit-factor-invariant, so this targets
Sharpe / max-drawdown, not PF. All volatility inputs are causal (shift(1)
before rolling). Development metrics only -- promotion is gated on untouched
OOS (see the pre-registration); nothing here computes a verdict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.research.funding_carry import (
    HOUR_MS,
    FundingCarryConfig,
    RebalanceStatus,
    _build_indexed_frame_and_rebalance_times,
    leg_pnl_fracs,
    run_incremental_funding_carry_backtest,
)

DEFAULT_VOL_LOOKBACK_HOURS = 168
DEFAULT_VOL_TARGET_WINDOW_HOURS = 2160
DEFAULT_SCALE_MIN = 0.5
DEFAULT_SCALE_MAX = 2.0
_HOURS_PER_YEAR = 24 * 365

__all__ = [
    "PositionSizingError",
    "RiskSizedSummary",
    "SizedRebalanceResult",
    "run_risk_sized_backtest",
    "summarize_risk_sized",
]


class PositionSizingError(ValueError):
    """Raised when position-sizing inputs are invalid."""


@dataclass(frozen=True, slots=True)
class SizedRebalanceResult:
    rebalance_time: int
    baseline_net_bps: float
    sized_net_bps: float
    scale: float


@dataclass(frozen=True, slots=True)
class RiskSizedSummary:
    n_rebalances: int
    baseline_net_pnl_bps: float
    sized_net_pnl_bps: float
    baseline_sharpe: float
    sized_sharpe: float
    baseline_max_drawdown_bps: float
    sized_max_drawdown_bps: float


def run_risk_sized_backtest(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
    *,
    vol_lookback_hours: int = DEFAULT_VOL_LOOKBACK_HOURS,
    vol_target_window_hours: int = DEFAULT_VOL_TARGET_WINDOW_HOURS,
    scale_min: float = DEFAULT_SCALE_MIN,
    scale_max: float = DEFAULT_SCALE_MAX,
) -> tuple[SizedRebalanceResult, ...]:
    """Apply the pre-registered risk-sizing overlay to the K=5 held-set path.

    Runs the primary incremental policy unchanged, then for each resolved
    rebalance computes both the equal-weight baseline net PnL and the
    inverse-vol-weighted + vol-targeted sized net PnL. Vol-targeting uses the
    baseline book's own trailing volatility as the target (self-referential),
    clamped to [scale_min, scale_max].
    """

    if vol_lookback_hours < 1 or vol_target_window_hours < 1:
        raise PositionSizingError("vol windows must be >= 1 hour")
    if not 0 < scale_min <= scale_max:
        raise PositionSizingError("require 0 < scale_min <= scale_max")

    results = run_incremental_funding_carry_backtest(bars, config)
    indexed, interval_ms, _ = _build_indexed_frame_and_rebalance_times(bars, config)
    leg_vol = _causal_leg_vol(bars, vol_lookback_hours)
    cost_bps = config.cost_bps_per_leg_roundtrip

    times: list[int] = []
    baseline_net: list[float] = []
    pre_scale_net: list[float] = []
    previous_held: set[tuple[str, str]] = set()
    for result in results:
        if result.status is not RebalanceStatus.RESOLVED:
            continue
        t = int(result.rebalance_time)
        snapshot = indexed.loc[t]
        forward = indexed.loc[t + interval_ms]

        long_weights = _inverse_vol_weights(result.held_long, leg_vol, t)
        short_weights = _inverse_vol_weights(result.held_short, leg_vol, t)

        gross_frac = 0.0
        for symbol, weight in long_weights.items():
            leg_funding, leg_price = leg_pnl_fracs(
                snapshot, forward, symbol, is_long=True, weight=weight
            )
            gross_frac += leg_funding + leg_price
        for symbol, weight in short_weights.items():
            leg_funding, leg_price = leg_pnl_fracs(
                snapshot, forward, symbol, is_long=False, weight=weight
            )
            gross_frac += leg_funding + leg_price
        sized_gross_bps = gross_frac * 10_000.0

        weight_of: dict[tuple[str, str], float] = {}
        for symbol, weight in long_weights.items():
            weight_of[(symbol, "long")] = weight
        for symbol, weight in short_weights.items():
            weight_of[(symbol, "short")] = weight
        current = set(weight_of)
        sized_cost_bps = sum(weight_of[key] for key in current - previous_held) * cost_bps

        times.append(t)
        baseline_net.append(result.net_pnl_bps)
        pre_scale_net.append(sized_gross_bps - sized_cost_bps)
        previous_held = current

    scales = _vol_target_scales(
        np.array(baseline_net),
        np.array(pre_scale_net),
        window=max(1, vol_target_window_hours // (interval_ms // HOUR_MS)),
        scale_min=scale_min,
        scale_max=scale_max,
    )
    return tuple(
        SizedRebalanceResult(
            rebalance_time=t,
            baseline_net_bps=b,
            sized_net_bps=p * s,
            scale=s,
        )
        for t, b, p, s in zip(times, baseline_net, pre_scale_net, scales, strict=True)
    )


def _causal_leg_vol(bars: pd.DataFrame, lookback_hours: int) -> pd.DataFrame:
    working = bars[["symbol", "open_time", "log_price"]].copy()
    working["open_time"] = pd.to_numeric(working["open_time"], errors="raise")
    working["log_price"] = pd.to_numeric(working["log_price"], errors="raise")
    price_wide = working.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    hourly_return = price_wide.diff()
    return hourly_return.shift(1).rolling(lookback_hours).std()


def _inverse_vol_weights(
    symbols: tuple[str, ...], leg_vol: pd.DataFrame, t: int
) -> dict[str, float]:
    """Weights within one side summing to 0.5; falls back to equal on bad vol."""

    if not symbols:
        return {}
    equal = 0.5 / len(symbols)
    inverses: dict[str, float] = {}
    for symbol in symbols:
        vol = leg_vol.at[t, symbol] if (t in leg_vol.index and symbol in leg_vol.columns) else None
        if vol is None or not np.isfinite(vol) or vol <= 0.0:
            return dict.fromkeys(symbols, equal)  # fail-safe: equal weight this interval
        inverses[symbol] = 1.0 / float(vol)
    total = sum(inverses.values())
    return {symbol: 0.5 * inv / total for symbol, inv in inverses.items()}


def _vol_target_scales(
    baseline: np.ndarray,
    pre_scale: np.ndarray,
    *,
    window: int,
    scale_min: float,
    scale_max: float,
) -> np.ndarray:
    """scale[t] = clip(trailing_std(baseline) / trailing_std(pre_scale), min, max).

    Both trailing stds are causal (shifted by one so t is excluded).
    """

    target = pd.Series(baseline).shift(1).rolling(window).std().to_numpy()
    current = pd.Series(pre_scale).shift(1).rolling(window).std().to_numpy()
    scales = np.ones(len(pre_scale), dtype=float)
    for i in range(len(pre_scale)):
        tgt, cur = target[i], current[i]
        if np.isfinite(tgt) and np.isfinite(cur) and cur > 0.0:
            scales[i] = min(max(tgt / cur, scale_min), scale_max)
    return scales


def summarize_risk_sized(
    results: tuple[SizedRebalanceResult, ...],
    config: FundingCarryConfig,
) -> RiskSizedSummary:
    """Risk-adjusted comparison of the sized overlay vs the equal-weight baseline."""

    if not results:
        raise PositionSizingError("no resolved rebalances to summarize")
    baseline = np.array([r.baseline_net_bps for r in results])
    sized = np.array([r.sized_net_bps for r in results])
    ann = math.sqrt(_HOURS_PER_YEAR / config.rebalance_interval_hours)
    return RiskSizedSummary(
        n_rebalances=len(results),
        baseline_net_pnl_bps=float(baseline.sum()),
        sized_net_pnl_bps=float(sized.sum()),
        baseline_sharpe=_sharpe(baseline, ann),
        sized_sharpe=_sharpe(sized, ann),
        baseline_max_drawdown_bps=_max_drawdown_bps(baseline),
        sized_max_drawdown_bps=_max_drawdown_bps(sized),
    )


def _sharpe(returns: np.ndarray, annualization: float) -> float:
    std = returns.std(ddof=1) if len(returns) > 1 else 0.0
    if not np.isfinite(std) or std == 0.0:
        return float("nan")
    return float(returns.mean() / std * annualization)


def _max_drawdown_bps(returns: np.ndarray) -> float:
    equity = np.cumsum(returns)
    running_max = np.maximum.accumulate(equity)
    return float(np.max(running_max - equity)) if len(equity) else 0.0
