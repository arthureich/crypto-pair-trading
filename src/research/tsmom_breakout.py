"""Causal Donchian-breakout trend-following backtest with an ATR trailing stop.

Implements the hypothesis pre-registered in
`docs/pre_registers/TASK-TSMOM-001.md`: single-asset breakout entries
(price crosses a trailing Donchian channel), inverse-volatility position
sizing, and a 3xATR trailing stop exit with NO fixed profit target --
"surf the trend until it reverses." This is a materially different
mechanism from the fixed-horizon time-series-momentum diagnostic already
run and aborted this session (`scripts/diagnostic_tsmom.py`), which could
not measure this strategy's specific (potentially asymmetric) payoff
shape.

Causality: both the Donchian channel and the ATR used for entries/stops
at bar t are computed from bars strictly before t (``shift(1)``, per the
pre-registration's explicit invariant) -- never the current bar's own
high/low.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import StrEnum

import pandas as pd

DEFAULT_DONCHIAN_WINDOW_HOURS = 24
DEFAULT_ATR_PERIOD_HOURS = 14
DEFAULT_ATR_STOP_MULTIPLIER = 3.0
DEFAULT_COST_BPS_ROUNDTRIP = 12.0
DEFAULT_PROFIT_FACTOR_GATE = 1.20
DEFAULT_MIN_WIN_RATE = 0.30
_REQUIRED_COLUMNS = ("symbol", "open_time", "high", "low", "close")


class TSMOMError(ValueError):
    """Raised when TSMOM backtest inputs are invalid."""


class TradeSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(StrEnum):
    RESOLVED = "RESOLVED"
    OPEN_AT_END = "OPEN_AT_END"


@dataclass(frozen=True, slots=True)
class TSMOMConfig:
    """Pre-registered configuration -- see TASK-TSMOM-001 for the rationale."""

    donchian_window_hours: int = DEFAULT_DONCHIAN_WINDOW_HOURS
    atr_period_hours: int = DEFAULT_ATR_PERIOD_HOURS
    atr_stop_multiplier: float = DEFAULT_ATR_STOP_MULTIPLIER
    cost_bps_roundtrip: float = DEFAULT_COST_BPS_ROUNDTRIP
    profit_factor_gate: float = DEFAULT_PROFIT_FACTOR_GATE
    min_win_rate: float = DEFAULT_MIN_WIN_RATE

    def __post_init__(self) -> None:
        if self.donchian_window_hours < 1:
            raise TSMOMError("donchian_window_hours must be >= 1")
        if self.atr_period_hours < 1:
            raise TSMOMError("atr_period_hours must be >= 1")
        if not math.isfinite(self.atr_stop_multiplier) or self.atr_stop_multiplier <= 0:
            raise TSMOMError("atr_stop_multiplier must be finite and positive")
        cost = self.cost_bps_roundtrip
        if not math.isfinite(cost) or cost < 0:
            raise TSMOMError("cost_bps_roundtrip must be finite and non-negative")
        if not math.isfinite(self.profit_factor_gate) or self.profit_factor_gate <= 0:
            raise TSMOMError("profit_factor_gate must be finite and positive")
        if not (0.0 <= self.min_win_rate <= 1.0):
            raise TSMOMError("min_win_rate must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class TSMOMTrade:
    """One resolved (or still-open) breakout trade."""

    symbol: str
    side: TradeSide
    status: TradeStatus
    entry_time: int
    exit_time: int | None
    entry_price: float
    exit_price: float | None
    entry_atr: float
    gross_return: float | None
    net_return: float | None
    weight: float


@dataclass(frozen=True, slots=True)
class TSMOMSummary:
    """Aggregate metrics across all resolved trades."""

    trade_count: int
    resolved_count: int
    open_at_end_count: int
    win_rate: float
    gross_pnl_bps: float
    net_pnl_bps: float
    cost_bps: float
    profit_factor: float
    max_drawdown_bps: float
    gate_pass: bool


def _causal_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.shift(1).rolling(period).mean()


def _simulate_symbol(
    symbol: str,
    bars: pd.DataFrame,
    config: TSMOMConfig,
) -> list[TSMOMTrade]:
    """Sequential, causal single-position-at-a-time simulation for one symbol."""

    close = bars["close"].to_numpy()
    open_time = bars["open_time"].to_numpy()

    donchian_high = bars["high"].shift(1).rolling(config.donchian_window_hours).max().to_numpy()
    donchian_low = bars["low"].shift(1).rolling(config.donchian_window_hours).min().to_numpy()
    atr = _causal_atr(bars["high"], bars["low"], bars["close"], config.atr_period_hours).to_numpy()

    trades: list[TSMOMTrade] = []
    side: TradeSide | None = None
    entry_price = 0.0
    entry_time = 0
    entry_atr = 0.0
    running_extreme = 0.0

    for t in range(len(bars)):
        if math.isnan(donchian_high[t]) or math.isnan(donchian_low[t]) or math.isnan(atr[t]):
            continue
        close_t = float(close[t])

        if side is None:
            if close_t > donchian_high[t]:
                side, entry_price, entry_time, entry_atr = (
                    TradeSide.LONG,
                    close_t,
                    int(open_time[t]),
                    float(atr[t]),
                )
                running_extreme = close_t
            elif close_t < donchian_low[t]:
                side, entry_price, entry_time, entry_atr = (
                    TradeSide.SHORT,
                    close_t,
                    int(open_time[t]),
                    float(atr[t]),
                )
                running_extreme = close_t
            continue

        exit_time = int(open_time[t])
        if side is TradeSide.LONG:
            running_extreme = max(running_extreme, close_t)
            stop_level = running_extreme - config.atr_stop_multiplier * float(atr[t])
            if close_t <= stop_level:
                trades.append(
                    _resolved_trade(
                        symbol, side, entry_time, exit_time, entry_price, close_t, entry_atr, config
                    )
                )
                side = None
        else:
            running_extreme = min(running_extreme, close_t)
            stop_level = running_extreme + config.atr_stop_multiplier * float(atr[t])
            if close_t >= stop_level:
                trades.append(
                    _resolved_trade(
                        symbol, side, entry_time, exit_time, entry_price, close_t, entry_atr, config
                    )
                )
                side = None

    if side is not None:
        trades.append(
            TSMOMTrade(
                symbol=symbol,
                side=side,
                status=TradeStatus.OPEN_AT_END,
                entry_time=entry_time,
                exit_time=None,
                entry_price=entry_price,
                exit_price=None,
                entry_atr=entry_atr,
                gross_return=None,
                net_return=None,
                weight=0.0,
            )
        )
    return trades


def _resolved_trade(
    symbol: str,
    side: TradeSide,
    entry_time: int,
    exit_time: int,
    entry_price: float,
    exit_price: float,
    entry_atr: float,
    config: TSMOMConfig,
) -> TSMOMTrade:
    if side is TradeSide.LONG:
        gross_return = (exit_price - entry_price) / entry_price
    else:
        gross_return = (entry_price - exit_price) / entry_price
    net_return = gross_return - (config.cost_bps_roundtrip / 10_000.0)
    return TSMOMTrade(
        symbol=symbol,
        side=side,
        status=TradeStatus.RESOLVED,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        entry_atr=entry_atr,
        gross_return=gross_return,
        net_return=net_return,
        weight=0.0,
    )


def run_tsmom_backtest(bars: pd.DataFrame, config: TSMOMConfig) -> tuple[TSMOMTrade, ...]:
    """Run the pre-registered breakout backtest across every symbol in ``bars``.

    ``bars`` must contain one row per (symbol, open_time), sorted or
    sortable by ``open_time`` within each symbol, with at least
    ``symbol``, ``open_time``, ``high``, ``low``, ``close``.
    """

    missing = [column for column in _REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise TSMOMError(f"missing required columns: {missing}")

    frame = bars[list(_REQUIRED_COLUMNS)].copy()
    duplicate_mask = frame.duplicated(subset=["open_time", "symbol"])
    if bool(duplicate_mask.any()):
        raise TSMOMError("duplicate (symbol, open_time) rows are not allowed")

    all_trades: list[TSMOMTrade] = []
    for symbol, group in frame.groupby("symbol", sort=True):
        ordered = group.sort_values("open_time", kind="mergesort").reset_index(drop=True)
        all_trades.extend(_simulate_symbol(str(symbol), ordered, config))

    resolved = [t for t in all_trades if t.status is TradeStatus.RESOLVED]
    if resolved:
        atr_pct = [t.entry_atr / t.entry_price for t in resolved]
        inv_atr_pct = [1.0 / value if value > 0 else 0.0 for value in atr_pct]
        mean_inv_atr_pct = sum(inv_atr_pct) / len(inv_atr_pct)
        weight_by_key = {
            (t.symbol, t.entry_time): (inv / mean_inv_atr_pct) if mean_inv_atr_pct > 0 else 0.0
            for t, inv in zip(resolved, inv_atr_pct, strict=True)
        }
        all_trades = [
            t
            if t.status is not TradeStatus.RESOLVED
            else replace(t, weight=weight_by_key[(t.symbol, t.entry_time)])
            for t in all_trades
        ]
    return tuple(all_trades)


def summarize_tsmom_backtest(trades: tuple[TSMOMTrade, ...], config: TSMOMConfig) -> TSMOMSummary:
    """Aggregate resolved trades and evaluate the pre-registered gate."""

    resolved = [t for t in trades if t.status is TradeStatus.RESOLVED]
    open_at_end = sum(1 for t in trades if t.status is TradeStatus.OPEN_AT_END)
    resolved_count = len(resolved)

    if resolved_count == 0:
        return TSMOMSummary(
            trade_count=len(trades),
            resolved_count=0,
            open_at_end_count=open_at_end,
            win_rate=float("nan"),
            gross_pnl_bps=0.0,
            net_pnl_bps=0.0,
            cost_bps=0.0,
            profit_factor=float("nan"),
            max_drawdown_bps=0.0,
            gate_pass=False,
        )

    ordered_by_exit = sorted(resolved, key=lambda t: t.exit_time)
    gross_bps = [t.weight * t.gross_return * 10_000.0 for t in ordered_by_exit]
    net_bps = [t.weight * t.net_return * 10_000.0 for t in ordered_by_exit]

    gross_pnl_bps = sum(gross_bps)
    net_pnl_bps = sum(net_bps)
    cost_bps = gross_pnl_bps - net_pnl_bps
    win_rate = sum(1 for value in net_bps if value > 0.0) / resolved_count

    gains = sum(value for value in net_bps if value > 0.0)
    losses = sum(value for value in net_bps if value < 0.0)
    if losses == 0.0:
        profit_factor = float("inf") if gains > 0.0 else float("nan")
    else:
        profit_factor = gains / abs(losses)

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in net_bps:
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)

    gate_pass = (
        not math.isnan(profit_factor)
        and profit_factor >= config.profit_factor_gate
        and win_rate >= config.min_win_rate
    )

    return TSMOMSummary(
        trade_count=len(trades),
        resolved_count=resolved_count,
        open_at_end_count=open_at_end,
        win_rate=win_rate,
        gross_pnl_bps=gross_pnl_bps,
        net_pnl_bps=net_pnl_bps,
        cost_bps=cost_bps,
        profit_factor=profit_factor,
        max_drawdown_bps=max_drawdown,
        gate_pass=gate_pass,
    )


__all__ = [
    "TSMOMConfig",
    "TSMOMError",
    "TSMOMSummary",
    "TSMOMTrade",
    "TradeSide",
    "TradeStatus",
    "run_tsmom_backtest",
    "summarize_tsmom_backtest",
]
