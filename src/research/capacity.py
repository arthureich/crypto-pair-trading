"""Capacity / liquidity / impact analysis for the canonical TSM (TASK-DEPLOY-001, Phase 4).

Given the per-symbol L/S weights (exposed read-only by the backtest) and per-symbol
executable dollar-volume, estimate how much capital the strategy can run before its
own market impact erodes the edge. Participation = order notional / available
dollar-volume; slippage grows with participation via the pre-declared execution
model. Capital scenarios are for CHARACTERIZATION only -- never to pick the capital
that maximizes Sharpe. Impact assumptions are conservative and documented; this is
an estimate, not a guarantee.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "capacity_net_returns",
    "participation_matrix",
    "slippage_bps_matrix",
    "turnover_matrix",
]


def turnover_matrix(weight_rows) -> np.ndarray:
    """Per-rebalance per-symbol traded fraction |Δw| (T x N).

    Row 0 is |w0| (entering from flat); row t is |w[t] - w[t-1]|.
    """
    w = np.asarray(weight_rows, dtype=float)
    if w.ndim != 2:  # noqa: PLR2004
        raise ValueError("weight_rows must be 2D (rebalances x symbols)")
    prev = np.vstack([np.zeros((1, w.shape[1])), w[:-1]])
    return np.abs(w - prev)


def participation_matrix(
    turnover: np.ndarray, dollar_volume: np.ndarray, capital: float
) -> np.ndarray:
    """order_notional / available dollar-volume, per rebalance per symbol.

    order_notional = capital * |Δw| (weights are unit-gross, so |Δw| is the
    fraction of capital traded in that symbol). Zero/NaN volume -> participation 0
    (no trade attributed where we have no liquidity data; flagged upstream).
    """
    dv = np.where((dollar_volume > 0) & np.isfinite(dollar_volume), dollar_volume, np.nan)
    part = (capital * turnover) / dv
    return np.nan_to_num(part, nan=0.0, posinf=0.0)


def slippage_bps_matrix(
    participation: np.ndarray, slippage_bps_at_full: float, max_participation: float
) -> np.ndarray:
    """Linear participation slippage (bps), clipped at max_participation (same as
    the execution model's per_leg_cost_bps)."""
    p = np.clip(participation, 0.0, max_participation)
    return slippage_bps_at_full * p


def capacity_net_returns(
    gross: np.ndarray,
    turnover: np.ndarray,
    slippage_bps: np.ndarray,
    *,
    base_cost_bps: float,
) -> np.ndarray:
    """Per-rebalance net return at a given capital.

    net[t] = gross[t] - sum_i |Δw_i|[t] * (base_cost_bps + slippage_bps_i[t]) / 1e4.
    `base_cost_bps` is the size-independent executable cost per leg (fee +
    half-spread); slippage is the size-dependent part.
    """
    per_symbol_cost = turnover * (base_cost_bps + slippage_bps) / 10_000.0
    return np.asarray(gross, dtype=float) - per_symbol_cost.sum(axis=1)
