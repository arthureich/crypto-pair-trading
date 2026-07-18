"""Pre-declared conservative execution model (TASK-DEPLOY-001, Phase 3).

ONE execution policy, declared A PRIORI -- NOT chosen to maximize backtest Sharpe.
The goal is to measure honestly the gap between theoretical and executable P&L,
never to find an execution that flatters the backtest.

Policy (conservative, fixed):
- execute at the first observable price AFTER the signal (no same-close fill, no
  best-posterior-price-in-bar);
- cross the spread: buy at ask, sell at bid -> pay a half-spread per leg;
- pay a realistic TAKER fee (no maker-fill assumption);
- add causal slippage that grows with participation (order size / bar volume);
- funding is already inside the strategy's gross return (include_funding) and is
  NOT re-charged here.

Constants are a-priori and conservative (documented, not tuned). Because we have
hourly klines (no bid/ask/tick data), spread and slippage are MODELED as a cost
overlay on the causal backtest returns, not simulated at tick level -- a
limitation stated in every report. The model is memoryless per rebalance: the
cost at t uses only turnover/participation at t (no lookahead).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["ExecutionCostModel", "ExecutionDecomposition"]

# Declared per-registration cost the backtest already charged (FC-II-008).
DECLARED_COST_BPS_PER_LEG = 6.0


@dataclass(frozen=True, slots=True)
class ExecutionDecomposition:
    fee_bps: float
    half_spread_bps: float
    slippage_bps: float
    total_bps: float


@dataclass(frozen=True, slots=True)
class ExecutionCostModel:
    """Conservative, a-priori execution cost model (bps per leg, on turnover)."""

    taker_fee_bps: float = 4.5  # Binance USDM taker ~0.045%
    half_spread_bps: float = 2.0  # conservative half-spread for liquid perps
    slippage_bps_at_full_participation: float = 10.0  # linear impact vs participation
    max_participation: float = 1.0  # participation is clipped to [0, this] for the cost

    def per_leg_cost_bps(self, participation_rate: float = 0.0) -> ExecutionDecomposition:
        """Executable cost of one unit of turnover, in bps.

        participation_rate = order_notional / bar_volume_notional at t (0 for the
        small-size base case). Slippage grows linearly with participation.
        """
        p = float(np.clip(participation_rate, 0.0, self.max_participation))
        slip = self.slippage_bps_at_full_participation * p
        total = self.taker_fee_bps + self.half_spread_bps + slip
        return ExecutionDecomposition(
            fee_bps=self.taker_fee_bps,
            half_spread_bps=self.half_spread_bps,
            slippage_bps=slip,
            total_bps=total,
        )

    def executable_net(
        self,
        gross_pre_cost: pd.Series,
        turnover: pd.Series,
        participation: pd.Series | None = None,
    ) -> pd.Series:
        """Executable net = gross (funding incl.) - executable frictions on turnover.

        `gross_pre_cost` is the strategy return BEFORE the declared cost (funding
        already inside). `turnover` is sum|dw| per rebalance. `participation` is
        optional per-rebalance participation (default 0 -> small-size base case).
        No lookahead: element t uses only turnover[t]/participation[t].
        """
        if participation is None:
            participation = pd.Series(0.0, index=turnover.index)
        cost_bps = (
            participation.reindex(turnover.index)
            .fillna(0.0)
            .map(lambda p: self.per_leg_cost_bps(p).total_bps)
        )
        return gross_pre_cost - turnover * (cost_bps / 10_000.0)

    def theoretical_net(self, gross_pre_cost: pd.Series, turnover: pd.Series) -> pd.Series:
        """Theoretical net = gross - the originally-declared 6bps/leg on turnover."""
        return gross_pre_cost - turnover * (DECLARED_COST_BPS_PER_LEG / 10_000.0)
