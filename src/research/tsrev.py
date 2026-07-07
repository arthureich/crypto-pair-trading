"""Time-series and cross-sectional reversal backtests (Research Family C - TSREV).

Implements the hypothesis pre-registered in
`docs/pre_registers/TASK-TSREV-001.md` (see `project_control/DECISIONS.md`
ADR-0014). Exactly one cell is decisive: Family A (time-series reversal),
24h horizon, evaluated only on the out-of-sample period. Every other cell
(Family A at 6h/12h/48h; Family B, cross-sectional, at 6h/12h/24h/48h) is
descriptive only and must never be substituted for the primary result.

Both families share the same causal signal:

    r[t]           = log_price[t] - log_price[t-H]           (own return)
    sigma_hourly[t] = hourly_return.shift(1).rolling(720).std()  (30d, causal)
    sigma_H[t]      = sigma_hourly[t] * sqrt(H)
    z[t]            = r[t] / sigma_H[t]

Family A trades each symbol independently (enter when |z| crosses a fixed
threshold, exit exactly H hours later, no trailing stop, no barrier).
Family B ranks all symbols cross-sectionally by z at every H-hour interval
and trades a decile-based dollar-neutral book, fully closed and reopened
every interval (same "full rebalance" convention as the funding-carry
fase-1 backtest, reused here for a different ranking variable).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import StrEnum

import pandas as pd

DEFAULT_VOL_LOOKBACK_HOURS = 720
DEFAULT_ZSCORE_THRESHOLD = 1.0
DEFAULT_COST_BPS_ROUNDTRIP = 6.0
DEFAULT_MIN_TRADES_FOR_GATE = 200
DEFAULT_PROFIT_FACTOR_GATE = 1.05
DEFAULT_DECILE_K = 2
_REQUIRED_COLUMNS = ("symbol", "open_time", "log_price")


class TSREVError(ValueError):
    """Raised when TSREV backtest inputs are invalid."""


class TradeSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(StrEnum):
    RESOLVED = "RESOLVED"
    OPEN_AT_END = "OPEN_AT_END"


def compute_zscore_matrix(
    wide_log_price: pd.DataFrame,
    horizon_hours: int,
    vol_lookback_hours: int = DEFAULT_VOL_LOOKBACK_HOURS,
) -> pd.DataFrame:
    """Causal, own-history-volatility-standardized return, per symbol.

    ``wide_log_price`` is indexed by ``open_time`` with one column per
    symbol. Both the return and its volatility denominator use only
    information available at or before the current row.
    """

    z, _sigma_h = compute_zscore_and_sigma(wide_log_price, horizon_hours, vol_lookback_hours)
    return z


def compute_zscore_and_sigma(
    wide_log_price: pd.DataFrame,
    horizon_hours: int,
    vol_lookback_hours: int = DEFAULT_VOL_LOOKBACK_HOURS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Same as ``compute_zscore_matrix`` but also returns sigma_H (bps

    denominator), needed by the inverse-volatility position sizing.
    """

    r = wide_log_price.diff(horizon_hours)
    hourly_ret = wide_log_price.diff(1)
    sigma_hourly = hourly_ret.shift(1).rolling(vol_lookback_hours).std()
    sigma_h = sigma_hourly * math.sqrt(horizon_hours)
    sigma_h_safe = sigma_h.replace(0.0, float("nan"))
    return r / sigma_h_safe, sigma_h_safe


def split_out_of_sample(
    bars: pd.DataFrame,
    oos_start_ms: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split bars into (in_sample, out_of_sample) by ``open_time``.

    The split is a fixed calendar boundary decided in the pre-registration,
    never chosen after inspecting results.
    """

    in_sample = bars[bars["open_time"] < oos_start_ms].copy()
    out_of_sample = bars[bars["open_time"] >= oos_start_ms].copy()
    return in_sample, out_of_sample


def buy_and_hold_max_drawdown_bps(wide_log_price: pd.DataFrame) -> float:
    """Max drawdown (bps) of an equal-weight buy-and-hold book of every

    symbol present in ``wide_log_price``, over exactly the rows given
    (callers slice to the desired period first).
    """

    returns = wide_log_price.diff(1).mean(axis=1).fillna(0.0)
    cumulative = returns.cumsum()
    running_max = cumulative.cummax()
    drawdown = (running_max - cumulative) * 10_000.0
    return float(drawdown.max())


@dataclass(frozen=True, slots=True)
class TimeSeriesReversalConfig:
    """Pre-registered configuration for one Family A (time-series) cell."""

    horizon_hours: int
    vol_lookback_hours: int = DEFAULT_VOL_LOOKBACK_HOURS
    zscore_threshold: float = DEFAULT_ZSCORE_THRESHOLD
    cost_bps_roundtrip: float = DEFAULT_COST_BPS_ROUNDTRIP
    profit_factor_gate: float = DEFAULT_PROFIT_FACTOR_GATE
    min_trades_for_gate: int = DEFAULT_MIN_TRADES_FOR_GATE

    def __post_init__(self) -> None:
        if self.horizon_hours < 1:
            raise TSREVError("horizon_hours must be >= 1")
        if self.vol_lookback_hours < 1:
            raise TSREVError("vol_lookback_hours must be >= 1")
        if not math.isfinite(self.zscore_threshold) or self.zscore_threshold <= 0:
            raise TSREVError("zscore_threshold must be finite and positive")
        cost = self.cost_bps_roundtrip
        if not math.isfinite(cost) or cost < 0:
            raise TSREVError("cost_bps_roundtrip must be finite and non-negative")
        if not math.isfinite(self.profit_factor_gate) or self.profit_factor_gate <= 0:
            raise TSREVError("profit_factor_gate must be finite and positive")
        if self.min_trades_for_gate < 1:
            raise TSREVError("min_trades_for_gate must be >= 1")


@dataclass(frozen=True, slots=True)
class TSREVTrade:
    symbol: str
    side: TradeSide
    status: TradeStatus
    entry_time: int
    exit_time: int | None
    entry_log_price: float
    exit_log_price: float | None
    entry_sigma_h: float
    gross_return: float | None
    net_return: float | None
    weight: float


@dataclass(frozen=True, slots=True)
class TSREVSummary:
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


def run_time_series_reversal_backtest(
    bars: pd.DataFrame,
    config: TimeSeriesReversalConfig,
) -> tuple[TSREVTrade, ...]:
    """Family A: independent per-symbol threshold entry, fixed-horizon exit."""

    missing = [column for column in _REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise TSREVError(f"missing required columns: {missing}")
    frame = bars[list(_REQUIRED_COLUMNS)].copy()
    if bool(frame.duplicated(subset=["open_time", "symbol"]).any()):
        raise TSREVError("duplicate (symbol, open_time) rows are not allowed")

    wide = frame.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    z, sigma_h = compute_zscore_and_sigma(wide, config.horizon_hours, config.vol_lookback_hours)

    all_trades: list[TSREVTrade] = []
    for symbol in wide.columns:
        all_trades.extend(
            _simulate_symbol_fixed_horizon(symbol, wide[symbol], z[symbol], sigma_h[symbol], config)
        )

    resolved = [t for t in all_trades if t.status is TradeStatus.RESOLVED]
    if resolved:
        inv_sigma = [1.0 / t.entry_sigma_h if t.entry_sigma_h > 0 else 0.0 for t in resolved]
        mean_inv_sigma = sum(inv_sigma) / len(inv_sigma)
        weight_by_key = {
            (t.symbol, t.entry_time): (inv / mean_inv_sigma) if mean_inv_sigma > 0 else 0.0
            for t, inv in zip(resolved, inv_sigma, strict=True)
        }
        all_trades = [
            t
            if t.status is not TradeStatus.RESOLVED
            else _with_weight(t, weight_by_key[(t.symbol, t.entry_time)])
            for t in all_trades
        ]
    return tuple(all_trades)


def _with_weight(trade: TSREVTrade, weight: float) -> TSREVTrade:
    return replace(trade, weight=weight)


def _simulate_symbol_fixed_horizon(
    symbol: str,
    log_price: pd.Series,
    z: pd.Series,
    sigma_h: pd.Series,
    config: TimeSeriesReversalConfig,
) -> list[TSREVTrade]:
    open_times = log_price.index.to_numpy()
    prices = log_price.to_numpy()
    z_values = z.to_numpy()
    sigma_values = sigma_h.to_numpy()
    n = len(prices)

    trades: list[TSREVTrade] = []
    side: TradeSide | None = None
    entry_index = -1
    entry_log_price = 0.0
    entry_sigma_h = 0.0

    for t in range(n):
        if side is None:
            z_t = z_values[t]
            if math.isnan(z_t):
                continue
            if z_t < -config.zscore_threshold:
                side = TradeSide.LONG
            elif z_t > config.zscore_threshold:
                side = TradeSide.SHORT
            else:
                continue
            entry_index = t
            entry_log_price = float(prices[t])
            entry_sigma_h = float(sigma_values[t])
            continue

        exit_index = entry_index + config.horizon_hours
        if t == exit_index:
            exit_log_price = float(prices[t])
            trades.append(
                _resolved_trade(
                    symbol,
                    side,
                    int(open_times[entry_index]),
                    int(open_times[t]),
                    entry_log_price,
                    exit_log_price,
                    entry_sigma_h,
                    config,
                )
            )
            side = None

    if side is not None:
        trades.append(
            TSREVTrade(
                symbol=symbol,
                side=side,
                status=TradeStatus.OPEN_AT_END,
                entry_time=int(open_times[entry_index]),
                exit_time=None,
                entry_log_price=entry_log_price,
                exit_log_price=None,
                entry_sigma_h=entry_sigma_h,
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
    entry_log_price: float,
    exit_log_price: float,
    entry_sigma_h: float,
    config: TimeSeriesReversalConfig,
) -> TSREVTrade:
    # log_price difference approximates the simple return, the same
    # convention already used in src/research/funding_carry.py -- never
    # divide by a log price (that formula is only valid for real prices).
    if side is TradeSide.LONG:
        gross_return = exit_log_price - entry_log_price
    else:
        gross_return = entry_log_price - exit_log_price
    net_return = gross_return - (config.cost_bps_roundtrip / 10_000.0)
    return TSREVTrade(
        symbol=symbol,
        side=side,
        status=TradeStatus.RESOLVED,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_log_price=entry_log_price,
        exit_log_price=exit_log_price,
        entry_sigma_h=entry_sigma_h,
        gross_return=gross_return,
        net_return=net_return,
        weight=0.0,
    )


def summarize_time_series_reversal(
    trades: tuple[TSREVTrade, ...],
    config: TimeSeriesReversalConfig,
    baseline_max_drawdown_bps: float | None = None,
) -> TSREVSummary:
    resolved = [t for t in trades if t.status is TradeStatus.RESOLVED]
    open_at_end = sum(1 for t in trades if t.status is TradeStatus.OPEN_AT_END)
    resolved_count = len(resolved)

    if resolved_count == 0:
        return TSREVSummary(
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

    return TSREVSummary(
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


@dataclass(frozen=True, slots=True)
class CrossSectionalReversalConfig:
    """Pre-registered configuration for one Family B (cross-sectional) cell."""

    horizon_hours: int
    vol_lookback_hours: int = DEFAULT_VOL_LOOKBACK_HOURS
    decile_k: int = DEFAULT_DECILE_K
    cost_bps_roundtrip: float = DEFAULT_COST_BPS_ROUNDTRIP

    def __post_init__(self) -> None:
        if self.horizon_hours < 1:
            raise TSREVError("horizon_hours must be >= 1")
        if self.decile_k < 1:
            raise TSREVError("decile_k must be >= 1")
        cost = self.cost_bps_roundtrip
        if not math.isfinite(cost) or cost < 0:
            raise TSREVError("cost_bps_roundtrip must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class CrossSectionalRebalanceResult:
    rebalance_time: int
    status: TradeStatus
    long_symbols: tuple[str, ...]
    short_symbols: tuple[str, ...]
    gross_pnl_bps: float
    cost_bps: float
    net_pnl_bps: float


def run_cross_sectional_reversal_backtest(
    bars: pd.DataFrame,
    config: CrossSectionalReversalConfig,
) -> tuple[CrossSectionalRebalanceResult, ...]:
    """Family B: cross-sectional decile book, fully rebalanced every interval."""

    missing = [column for column in _REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise TSREVError(f"missing required columns: {missing}")
    frame = bars[list(_REQUIRED_COLUMNS)].copy()
    if bool(frame.duplicated(subset=["open_time", "symbol"]).any()):
        raise TSREVError("duplicate (symbol, open_time) rows are not allowed")

    wide = frame.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    total_symbols = wide.shape[1]
    if 2 * config.decile_k > total_symbols:
        raise TSREVError(
            f"decile_k={config.decile_k} requires 2*decile_k symbols, "
            f"but the universe only has {total_symbols}"
        )
    z = compute_zscore_matrix(wide, config.horizon_hours, config.vol_lookback_hours)

    interval = config.horizon_hours
    open_times = wide.index.to_numpy()
    rebalance_indices = range(0, len(open_times), interval)

    weight = 1.0 / (2.0 * config.decile_k)
    results = []
    for i in rebalance_indices:
        exit_i = i + interval
        if exit_i >= len(open_times):
            results.append(
                CrossSectionalRebalanceResult(
                    rebalance_time=int(open_times[i]),
                    status=TradeStatus.OPEN_AT_END,
                    long_symbols=(),
                    short_symbols=(),
                    gross_pnl_bps=0.0,
                    cost_bps=0.0,
                    net_pnl_bps=0.0,
                )
            )
            continue

        z_row = z.iloc[i]
        eligible = z_row.dropna().index
        if len(eligible) < 2 * config.decile_k:
            continue
        ranked = z_row[eligible].sort_values(kind="mergesort")
        long_symbols = tuple(ranked.index[: config.decile_k])
        short_symbols = tuple(ranked.index[-config.decile_k :])

        price_now = wide.iloc[i]
        price_exit = wide.iloc[exit_i]
        gross_frac = 0.0
        for symbol in long_symbols:
            gross_frac += weight * (price_exit[symbol] - price_now[symbol])
        for symbol in short_symbols:
            gross_frac += weight * (price_now[symbol] - price_exit[symbol])
        gross_bps = gross_frac * 10_000.0
        cost_bps = config.cost_bps_roundtrip
        net_bps = gross_bps - cost_bps
        results.append(
            CrossSectionalRebalanceResult(
                rebalance_time=int(open_times[i]),
                status=TradeStatus.RESOLVED,
                long_symbols=long_symbols,
                short_symbols=short_symbols,
                gross_pnl_bps=gross_bps,
                cost_bps=cost_bps,
                net_pnl_bps=net_bps,
            )
        )
    return tuple(results)


def summarize_cross_sectional_reversal(
    results: tuple[CrossSectionalRebalanceResult, ...],
) -> dict[str, float | int]:
    resolved = [r for r in results if r.status is TradeStatus.RESOLVED]
    resolved_count = len(resolved)
    if resolved_count == 0:
        return {
            "rebalance_count": len(results),
            "resolved_count": 0,
            "net_pnl_bps": 0.0,
            "profit_factor": float("nan"),
        }
    net_bps = [r.net_pnl_bps for r in resolved]
    gains = sum(v for v in net_bps if v > 0.0)
    losses = sum(v for v in net_bps if v < 0.0)
    if losses == 0.0:
        profit_factor = float("inf") if gains > 0.0 else float("nan")
    else:
        profit_factor = gains / abs(losses)
    return {
        "rebalance_count": len(results),
        "resolved_count": resolved_count,
        "net_pnl_bps": sum(net_bps),
        "profit_factor": profit_factor,
    }


__all__ = [
    "CrossSectionalRebalanceResult",
    "CrossSectionalReversalConfig",
    "TSREVError",
    "TSREVSummary",
    "TSREVTrade",
    "TimeSeriesReversalConfig",
    "TradeSide",
    "TradeStatus",
    "buy_and_hold_max_drawdown_bps",
    "compute_zscore_matrix",
    "run_cross_sectional_reversal_backtest",
    "run_time_series_reversal_backtest",
    "split_out_of_sample",
    "summarize_cross_sectional_reversal",
    "summarize_time_series_reversal",
]
