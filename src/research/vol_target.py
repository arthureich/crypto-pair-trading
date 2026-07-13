"""TASK-TSM-007: volatility-targeting overlay for a strategy return stream (ADR-0031).

Moreira-Muir managed-volatility applied to the TSM's per-rebalance returns: scale
each period's return inversely to the strategy's own trailing realized volatility,
targeting roughly constant vol (average leverage ~1, no persistent leverage knob).
Pure and causal -- sigma and the target both use shift(1); the scale for period t
uses only information available before t. Operates on the RETURN STREAM (does not
touch the base signal).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_VOL_WINDOW = 12  # rebalances (~60d at a 5d hold); literature-standard
DEFAULT_SCALE_CAP = 3.0  # a-priori risk sanity bound on leverage (not tuned)
_MIN_OBS = 2


class VolTargetError(ValueError):
    """Raised when vol-target inputs are invalid."""


def vol_target_scale(
    returns: pd.Series, window: int = DEFAULT_VOL_WINDOW, cap: float = DEFAULT_SCALE_CAP
) -> pd.Series:
    """Causal per-period scale factor targeting ~constant volatility.

    sigma_t   = trailing std of returns (shift(1), rolling `window`)
    target_t  = expanding causal mean of sigma (so the average scale is ~1)
    scale_t   = clip(target_t / sigma_t, 0, cap); warm-up / undefined -> 1.0
    """

    if window < _MIN_OBS:
        raise VolTargetError("window must be >= 2")
    if not np.isfinite(cap) or cap <= 0:
        raise VolTargetError("cap must be finite and positive")
    sigma = returns.shift(1).rolling(window).std()
    target = sigma.shift(1).expanding().mean()
    scale = (target / sigma).clip(lower=0.0, upper=cap)
    return scale.replace([np.inf, -np.inf], np.nan).fillna(1.0)


def apply_vol_target(
    returns: pd.Series, window: int = DEFAULT_VOL_WINDOW, cap: float = DEFAULT_SCALE_CAP
) -> pd.Series:
    """Scale a return stream by the causal vol-target factor (P&L and cost scale together)."""

    scale = vol_target_scale(returns, window=window, cap=cap)
    return returns * scale
