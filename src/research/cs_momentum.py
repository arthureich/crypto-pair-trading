"""Cross-sectional momentum backtest (Research Family E - TASK-CS-001).

Implements the hypothesis pre-registered in
`docs/pre_registers/TASK-CS-001.md` (see `project_control/DECISIONS.md`
ADR-0017): a faithful replication of weekly cross-sectional crypto
momentum (Liu & Tsyvinski 2021, JFE style), not an internally-invented
signal.

Causal signal (no volatility normalization -- literature sorts on raw
formation return, unlike TSREV's z-score):

    r[t] = log_price[t] - log_price[t-H]     (own trailing return)

Every H hours, rank all symbols by r[t]. Long the top quintile
(winners), short the bottom quintile (losers), equal-weighted,
dollar-neutral, full rebalance (book closed and reopened every
interval, same convention as TSREV Family B / funding-carry fase 1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from src.research.tsrev import (
    TradeSide,
    TradeStatus,
    buy_and_hold_max_drawdown_bps,
    split_out_of_sample,
)

DEFAULT_FORMATION_HOURS = 168
DEFAULT_QUINTILE_K = 4
DEFAULT_COST_BPS_ROUNDTRIP = 6.0
DEFAULT_PROFIT_FACTOR_GATE = 1.10
DEFAULT_MIN_TRADES_FOR_GATE = 200
_REQUIRED_COLUMNS = ("symbol", "open_time", "log_price")

__all__ = [
    "CrossSectionalMomentumConfig",
    "CrossSectionalMomentumError",
    "MomentumLegTrade",
    "MomentumSummary",
    "buy_and_hold_max_drawdown_bps",
    "run_cross_sectional_momentum_backtest",
    "split_out_of_sample",
    "summarize_cross_sectional_momentum",
]


class CrossSectionalMomentumError(ValueError):
    """Raised when cross-sectional momentum backtest inputs are invalid."""


@dataclass(frozen=True, slots=True)
class CrossSectionalMomentumConfig:
    """Pre-registered configuration for TASK-CS-001.

    ``formation_hours`` doubles as the holding period and the rebalance
    interval, per the pre-registered "formation = holding, no
    skip-period" weekly convention -- not three independent parameters.
    """

    formation_hours: int = DEFAULT_FORMATION_HOURS
    quintile_k: int = DEFAULT_QUINTILE_K
    cost_bps_roundtrip: float = DEFAULT_COST_BPS_ROUNDTRIP
    profit_factor_gate: float = DEFAULT_PROFIT_FACTOR_GATE
    min_trades_for_gate: int = DEFAULT_MIN_TRADES_FOR_GATE

    def __post_init__(self) -> None:
        if self.formation_hours < 1:
            raise CrossSectionalMomentumError("formation_hours must be >= 1")
        if self.quintile_k < 1:
            raise CrossSectionalMomentumError("quintile_k must be >= 1")
        cost = self.cost_bps_roundtrip
        if not math.isfinite(cost) or cost < 0:
            raise CrossSectionalMomentumError("cost_bps_roundtrip must be finite and non-negative")
        if not math.isfinite(self.profit_factor_gate) or self.profit_factor_gate <= 0:
            raise CrossSectionalMomentumError("profit_factor_gate must be finite and positive")
        if self.min_trades_for_gate < 1:
            raise CrossSectionalMomentumError("min_trades_for_gate must be >= 1")


@dataclass(frozen=True, slots=True)
class MomentumLegTrade:
    symbol: str
    side: TradeSide
    status: TradeStatus
    entry_time: int
    exit_time: int | None
    entry_log_price: float
    exit_log_price: float | None
    formation_return: float
    gross_return: float | None
    net_return: float | None
    weight: float


@dataclass(frozen=True, slots=True)
class MomentumSummary:
    trade_count: int
    resolved_count: int
    open_at_end_count: int
    win_rate: float
    gross_pnl_bps: float
    net_pnl_bps: float
    cost_bps: float
    profit_factor: float
    max_drawdown_bps: float
    baseline_max_drawdown_bps: float | None
    gate_pass: bool


def run_cross_sectional_momentum_backtest(
    bars: pd.DataFrame,
    config: CrossSectionalMomentumConfig,
) -> tuple[MomentumLegTrade, ...]:
    """Rank by raw trailing return, long winners / short losers, full rebalance."""

    missing = [column for column in _REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise CrossSectionalMomentumError(f"missing required columns: {missing}")
    frame = bars[list(_REQUIRED_COLUMNS)].copy()
    if bool(frame.duplicated(subset=["open_time", "symbol"]).any()):
        raise CrossSectionalMomentumError("duplicate (symbol, open_time) rows are not allowed")

    wide = frame.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    total_symbols = wide.shape[1]
    if 2 * config.quintile_k > total_symbols:
        raise CrossSectionalMomentumError(
            f"quintile_k={config.quintile_k} requires 2*quintile_k symbols, "
            f"but the universe only has {total_symbols}"
        )

    formation_return = wide.diff(config.formation_hours)
    open_times = wide.index.to_numpy()
    interval = config.formation_hours
    weight = 1.0 / (2.0 * config.quintile_k)

    trades: list[MomentumLegTrade] = []
    for i in range(0, len(open_times), interval):
        r_row = formation_return.iloc[i]
        eligible = r_row.dropna().index
        if len(eligible) < 2 * config.quintile_k:
            continue
        ranked = r_row[eligible].sort_values(kind="mergesort")
        losers = tuple(ranked.index[: config.quintile_k])
        winners = tuple(ranked.index[-config.quintile_k :])

        exit_i = i + interval
        resolved = exit_i < len(open_times)
        entry_prices = wide.iloc[i]
        exit_prices = wide.iloc[exit_i] if resolved else None

        for symbol in winners:
            trades.append(
                _leg_trade(
                    symbol,
                    TradeSide.LONG,
                    int(open_times[i]),
                    int(open_times[exit_i]) if resolved else None,
                    float(entry_prices[symbol]),
                    float(exit_prices[symbol]) if resolved else None,
                    float(r_row[symbol]),
                    weight,
                    config,
                )
            )
        for symbol in losers:
            trades.append(
                _leg_trade(
                    symbol,
                    TradeSide.SHORT,
                    int(open_times[i]),
                    int(open_times[exit_i]) if resolved else None,
                    float(entry_prices[symbol]),
                    float(exit_prices[symbol]) if resolved else None,
                    float(r_row[symbol]),
                    weight,
                    config,
                )
            )
    return tuple(trades)


def _leg_trade(
    symbol: str,
    side: TradeSide,
    entry_time: int,
    exit_time: int | None,
    entry_log_price: float,
    exit_log_price: float | None,
    formation_return: float,
    weight: float,
    config: CrossSectionalMomentumConfig,
) -> MomentumLegTrade:
    if exit_log_price is None:
        return MomentumLegTrade(
            symbol=symbol,
            side=side,
            status=TradeStatus.OPEN_AT_END,
            entry_time=entry_time,
            exit_time=None,
            entry_log_price=entry_log_price,
            exit_log_price=None,
            formation_return=formation_return,
            gross_return=None,
            net_return=None,
            weight=0.0,
        )
    # log_price difference approximates the simple return, the same
    # convention already used in tsrev.py/funding_carry.py.
    if side is TradeSide.LONG:
        gross_return = exit_log_price - entry_log_price
    else:
        gross_return = entry_log_price - exit_log_price
    net_return = gross_return - (config.cost_bps_roundtrip / 10_000.0)
    return MomentumLegTrade(
        symbol=symbol,
        side=side,
        status=TradeStatus.RESOLVED,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_log_price=entry_log_price,
        exit_log_price=exit_log_price,
        formation_return=formation_return,
        gross_return=gross_return,
        net_return=net_return,
        weight=weight,
    )


def summarize_cross_sectional_momentum(
    trades: tuple[MomentumLegTrade, ...],
    config: CrossSectionalMomentumConfig,
    baseline_max_drawdown_bps: float | None = None,
) -> MomentumSummary:
    resolved = [t for t in trades if t.status is TradeStatus.RESOLVED]
    open_at_end = sum(1 for t in trades if t.status is TradeStatus.OPEN_AT_END)
    resolved_count = len(resolved)

    if resolved_count == 0:
        return MomentumSummary(
            trade_count=len(trades),
            resolved_count=0,
            open_at_end_count=open_at_end,
            win_rate=float("nan"),
            gross_pnl_bps=0.0,
            net_pnl_bps=0.0,
            cost_bps=0.0,
            profit_factor=float("nan"),
            max_drawdown_bps=0.0,
            baseline_max_drawdown_bps=baseline_max_drawdown_bps,
            gate_pass=False,
        )

    ordered = sorted(resolved, key=lambda t: t.exit_time)
    gross_bps = [t.weight * t.gross_return * 10_000.0 for t in ordered]
    net_bps = [t.weight * t.net_return * 10_000.0 for t in ordered]

    gross_pnl_bps = sum(gross_bps)
    net_pnl_bps = sum(net_bps)
    cost_bps = gross_pnl_bps - net_pnl_bps
    win_rate = sum(1 for v in net_bps if v > 0.0) / resolved_count

    gains = sum(v for v in net_bps if v > 0.0)
    losses = sum(v for v in net_bps if v < 0.0)
    if losses == 0.0:
        profit_factor = float("inf") if gains > 0.0 else float("nan")
    else:
        profit_factor = gains / abs(losses)

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for v in net_bps:
        cumulative += v
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)

    drawdown_ok = baseline_max_drawdown_bps is None or max_drawdown <= baseline_max_drawdown_bps
    gate_pass = (
        not math.isnan(profit_factor)
        and profit_factor > config.profit_factor_gate
        and net_pnl_bps > 0.0
        and drawdown_ok
        and resolved_count >= config.min_trades_for_gate
    )

    return MomentumSummary(
        trade_count=len(trades),
        resolved_count=resolved_count,
        open_at_end_count=open_at_end,
        win_rate=win_rate,
        gross_pnl_bps=gross_pnl_bps,
        net_pnl_bps=net_pnl_bps,
        cost_bps=cost_bps,
        profit_factor=profit_factor,
        max_drawdown_bps=max_drawdown,
        baseline_max_drawdown_bps=baseline_max_drawdown_bps,
        gate_pass=gate_pass,
    )
