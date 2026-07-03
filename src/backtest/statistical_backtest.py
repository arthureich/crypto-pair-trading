"""Candle-level statistical backtest with directional triple-barrier exits.

Implements the roadmap's canonical Sprint 8 ("Triple Barrier direcional e
backtest estatistico", see `project_control/ROADMAP.md` and
`project_control/DECISIONS.md` ADR-0009): a fast, candle-level (1h bar)
backtest using a conservative FIXED cost assumption, distinct from the
tick-level real-execution simulation built for the (non-canonical) Sprint 8
and Sprint 9 (see `src/backtest/execution_simulator.py`). This module is
evaluated on all 41 Sprint 7 statistical candidate pairs, not the cost-gated
subset -- ADR-0009 explains why.

Signal generation is causal: entries only use a trailing causal rolling
z-score and a per-index causal OU refit (same trailing-window technique
already reviewed for the non-canonical Sprint 8, avoiding the look-ahead bug
found there). Triple-barrier RESOLUTION legitimately scans forward through
already-known historical bars -- see `src.research.triple_barrier` for why
that is not look-ahead in the sense this project prohibits for signal
generation.

Caveats for readers of the aggregated metrics (see `StatisticalBacktestMetrics`):

- Every threshold-crossing bar generates its own independent entry, with no
  tracking of whether a prior trade on the same pair is still "open." Trades
  can and do overlap in time, so trade_count/turnover/hit_rate/profit_factor/
  Sharpe/Sortino describe unconstrained concurrent exposure, not a single
  representative position -- they should not be read as what one deployed
  strategy instance would have realized.
- Sharpe/Sortino are simple per-trade mean/std ratios (not annualized, and
  Sortino here is the std of losing-trade PnL, not a textbook downside
  deviation against a minimum acceptable return). Treat them as an internal
  ranking heuristic, not a cross-strategy-comparable statistic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd

from src.research.kalman import KalmanFilterConfig, fit_kalman_filter
from src.research.ou import estimate_ou, rolling_zscore
from src.research.triple_barrier import (
    BarrierOutcome,
    BarrierSide,
    TripleBarrierConfig,
    TripleBarrierLabel,
    label_directional_triple_barrier,
)

HOUR_MS = 60 * 60 * 1000
HOURS_PER_DAY = 24.0
DEFAULT_ZSCORE_WINDOW = 168
DEFAULT_OU_WINDOW = 168
DEFAULT_ENTRY_ZSCORE = 2.0
DEFAULT_MAX_HALF_LIFE_HOURS = 240.0
DEFAULT_HALF_LIFE_MULTIPLIER = 4.0
DEFAULT_MAX_VERTICAL_BARS = 240
DEFAULT_CONSERVATIVE_FEE_SLIPPAGE_BPS_PER_LEG_ROUNDTRIP = 6.0
DEFAULT_TARGET_NOTIONAL = 1_000.0
MIN_PROFIT_FACTOR = 1.10
PAIR_SYMBOL_COUNT = 2


class StatisticalBacktestError(ValueError):
    """Raised when statistical-backtest inputs are invalid."""


class TradeStatus(StrEnum):
    """Whether a triple-barrier trade resolved to a usable PnL observation."""

    RESOLVED = "RESOLVED"
    UNRESOLVED_NO_DATA = "UNRESOLVED_NO_DATA"


@dataclass(frozen=True, slots=True)
class StatisticalBacktestConfig:
    """Thresholds for the canonical Sprint 8 candle-level backtest."""

    zscore_window: int = DEFAULT_ZSCORE_WINDOW
    ou_window: int = DEFAULT_OU_WINDOW
    entry_zscore: float = DEFAULT_ENTRY_ZSCORE
    max_half_life_hours: float = DEFAULT_MAX_HALF_LIFE_HOURS
    half_life_multiplier: float = DEFAULT_HALF_LIFE_MULTIPLIER
    max_vertical_bars: int = DEFAULT_MAX_VERTICAL_BARS
    # Not a measurement: a conservative flat assumption per ADR-0009, distinct
    # from Sprint 9's real tick-level cost evidence. Binance USD-M futures
    # taker fee is ~4-5bps per side before any slippage, so this constant
    # should be sanity-checked against the current fee schedule before it is
    # trusted to gate a real capital-allocation decision.
    conservative_fee_slippage_bps_per_leg_roundtrip: float = (
        DEFAULT_CONSERVATIVE_FEE_SLIPPAGE_BPS_PER_LEG_ROUNDTRIP
    )
    target_notional: float = DEFAULT_TARGET_NOTIONAL
    # Real-time duration of one bar, in hours. Default 1.0 matches every bar
    # this module has consumed so far (Sprint 7's hourly candles). Threading
    # this through estimate_ou's `dt` and the funding-cost holding-days
    # calculation is what makes this module valid for any bar interval, not
    # just 1h -- without it, a 5-minute bar would be silently treated as if
    # it were an hour, both for the OU half-life estimate (units would be
    # "per 5-min-bar", not hours, while still being compared against an
    # hours-denominated max_half_life_hours) and for funding cost.
    bar_duration_hours: float = 1.0

    def __post_init__(self) -> None:
        _positive_int("zscore_window", self.zscore_window)
        _positive_int("ou_window", self.ou_window)
        _positive_finite("entry_zscore", self.entry_zscore)
        _positive_finite("max_half_life_hours", self.max_half_life_hours)
        _positive_finite("half_life_multiplier", self.half_life_multiplier)
        _positive_int("max_vertical_bars", self.max_vertical_bars)
        _non_negative_finite(
            "conservative_fee_slippage_bps_per_leg_roundtrip",
            self.conservative_fee_slippage_bps_per_leg_roundtrip,
        )
        _positive_finite("target_notional", self.target_notional)
        _positive_finite("bar_duration_hours", self.bar_duration_hours)


@dataclass(frozen=True, slots=True)
class StatisticalTradeResult:
    """One resolved (or unresolved) triple-barrier trade for one pair."""

    pair: str
    status: TradeStatus
    side: BarrierSide
    entry_time: int
    entry_zscore: float
    exit_time: int | None
    outcome: BarrierOutcome
    bars_held: int
    gross_pnl_bps: float
    cost_bps: float
    net_pnl_bps: float


@dataclass(frozen=True, slots=True)
class StatisticalBacktestMetrics:
    """Aggregated metrics for one pair's resolved trades."""

    trade_count: int
    gross_pnl_bps: float
    cost_bps: float
    net_pnl_bps: float
    hit_rate: float
    profit_factor: float
    sharpe: float
    sortino: float
    max_drawdown_bps: float
    avg_win_bps: float
    avg_loss_bps: float
    avg_bars_held: float
    turnover_notional: float

    @property
    def profit_factor_gate_pass(self) -> bool:
        # profit_factor is +inf, not NaN, when every resolved trade is a
        # winner (zero gross loss) -- that must PASS, not be vetoed. NaN
        # (no resolved trades) correctly fails the ">=" comparison already.
        return not math.isnan(self.profit_factor) and self.profit_factor >= MIN_PROFIT_FACTOR


def run_pair_statistical_backtest(
    bars: pd.DataFrame,
    pair: str,
    *,
    funding_carry_bps_per_day: float,
    config: StatisticalBacktestConfig | None = None,
) -> tuple[StatisticalTradeResult, ...]:
    """Run the canonical Sprint 8 triple-barrier backtest for one pair."""

    cfg = config or StatisticalBacktestConfig()
    symbol_a, symbol_b = _pair_symbols(pair)
    pair_bars = _pair_frame(bars, symbol_a, symbol_b)
    if len(pair_bars) < max(cfg.zscore_window, cfg.ou_window):
        return ()

    log_price_a = pair_bars["log_price_a"].to_numpy(dtype=float)
    log_price_b = pair_bars["log_price_b"].to_numpy(dtype=float)
    open_time = pair_bars["open_time"]

    kalman = fit_kalman_filter(
        y=log_price_a,
        x=log_price_b,
        config=KalmanFilterConfig(initial_beta=1.0),
    )
    spread = pd.Series(kalman.spread, index=pair_bars.index, name="spread")
    zscores = rolling_zscore(spread, window=cfg.zscore_window, min_periods=cfg.zscore_window)

    trades = []
    for index, zscore in zscores.dropna().items():
        position = int(index)
        if kalman.unstable_points[position]:
            continue
        beta = float(kalman.beta[position])
        if beta <= 0.0:
            continue
        if abs(zscore) < cfg.entry_zscore:
            continue
        window_start = position - cfg.ou_window + 1
        if window_start < 0:
            continue
        trailing_spread = spread.iloc[window_start : position + 1]
        try:
            ou = estimate_ou(
                trailing_spread, dt=cfg.bar_duration_hours, min_observations=cfg.ou_window
            )
        except ValueError:
            continue
        if not ou.mean_reverting or ou.half_life > cfg.max_half_life_hours:
            continue

        barrier_config = TripleBarrierConfig(
            entry_zscore=cfg.entry_zscore,
            half_life_hours=max(ou.half_life, 1e-6),
            half_life_multiplier=cfg.half_life_multiplier,
            max_vertical_bars=cfg.max_vertical_bars,
            bar_duration_hours=cfg.bar_duration_hours,
        )
        # Bound the resolution window by the configured bar-count cap plus one
        # confirming bar beyond it. The resolver uses real elapsed time (via
        # open_time) and fails closed to NO_DATA unless it can confirm that the
        # vertical budget was reached.
        window_end = min(position + cfg.max_vertical_bars + 2, len(zscores))
        labels = label_directional_triple_barrier(
            zscores=zscores.iloc[position:window_end].reset_index(drop=True),
            open_time=open_time.iloc[position:window_end].reset_index(drop=True),
            config=barrier_config,
        )
        if not labels or labels[0].entry_index != 0:
            continue
        label = labels[0]
        trades.append(
            resolve_trade_pnl(
                pair=pair,
                label=label,
                entry_position=position,
                log_price_a=log_price_a,
                log_price_b=log_price_b,
                beta=beta,
                funding_carry_bps_per_day=funding_carry_bps_per_day,
                config=cfg,
            )
        )
    return tuple(trades)


def resolve_trade_pnl(
    *,
    pair: str,
    label: TripleBarrierLabel,
    entry_position: int,
    log_price_a: np.ndarray,
    log_price_b: np.ndarray,
    beta: float,
    funding_carry_bps_per_day: float,
    config: StatisticalBacktestConfig,
) -> StatisticalTradeResult:
    """Compute one trade's gross/cost/net PnL from a resolved triple-barrier label.

    Gross PnL reuses the beta-weighted spread-move combination already used
    and reviewed in Sprint 8/9: ``direction * (delta log_price_a - beta *
    delta log_price_b)`` in bps, where direction is -1 for SHORT_SPREAD
    (profits when the spread falls) and +1 for LONG_SPREAD (profits when the
    spread rises). Cost is funding_carry_bps_per_day (real, from Sprint 7)
    times days held, plus a fixed conservative fee/slippage assumption for
    both legs' round trip -- an explicit assumption, not a measurement.

    Fails closed on a non-finite funding_carry_bps_per_day rather than
    silently propagating NaN into every downstream aggregate metric.
    """

    if not math.isfinite(funding_carry_bps_per_day):
        raise StatisticalBacktestError("funding_carry_bps_per_day must be finite")

    if label.outcome is BarrierOutcome.NO_DATA or label.exit_index is None:
        return StatisticalTradeResult(
            pair=pair,
            status=TradeStatus.UNRESOLVED_NO_DATA,
            side=label.side,
            entry_time=label.entry_time,
            entry_zscore=label.entry_zscore,
            exit_time=None,
            outcome=label.outcome,
            bars_held=0,
            gross_pnl_bps=0.0,
            cost_bps=0.0,
            net_pnl_bps=0.0,
        )

    exit_position = entry_position + label.bars_held
    if exit_position >= len(log_price_a) or exit_position >= len(log_price_b):
        raise StatisticalBacktestError(
            f"exit_position {exit_position} is out of bounds for the supplied price arrays"
        )
    spread_change_bps = (
        (log_price_a[exit_position] - log_price_a[entry_position]) * 10_000.0
        - beta * (log_price_b[exit_position] - log_price_b[entry_position]) * 10_000.0
    )
    direction = -1.0 if label.side is BarrierSide.SHORT_SPREAD else 1.0
    gross_pnl_bps = direction * spread_change_bps

    holding_days = label.bars_held * config.bar_duration_hours / HOURS_PER_DAY
    funding_cost_bps = abs(funding_carry_bps_per_day) * holding_days
    fee_slippage_cost_bps = 2.0 * config.conservative_fee_slippage_bps_per_leg_roundtrip
    cost_bps = funding_cost_bps + fee_slippage_cost_bps
    net_pnl_bps = gross_pnl_bps - cost_bps

    return StatisticalTradeResult(
        pair=pair,
        status=TradeStatus.RESOLVED,
        side=label.side,
        entry_time=label.entry_time,
        entry_zscore=label.entry_zscore,
        exit_time=label.exit_time,
        outcome=label.outcome,
        bars_held=label.bars_held,
        gross_pnl_bps=gross_pnl_bps,
        cost_bps=cost_bps,
        net_pnl_bps=net_pnl_bps,
    )


def summarize_statistical_backtest(
    trades: tuple[StatisticalTradeResult, ...],
    *,
    target_notional: float = DEFAULT_TARGET_NOTIONAL,
) -> StatisticalBacktestMetrics:
    """Summarize resolved trades into roadmap-specified metrics."""

    resolved = tuple(
        sorted(
            (t for t in trades if t.status is TradeStatus.RESOLVED),
            key=lambda t: t.entry_time,
        )
    )
    if not resolved:
        return StatisticalBacktestMetrics(
            trade_count=0,
            gross_pnl_bps=0.0,
            cost_bps=0.0,
            net_pnl_bps=0.0,
            hit_rate=math.nan,
            profit_factor=math.nan,
            sharpe=math.nan,
            sortino=math.nan,
            max_drawdown_bps=0.0,
            avg_win_bps=math.nan,
            avg_loss_bps=math.nan,
            avg_bars_held=math.nan,
            turnover_notional=0.0,
        )

    net = np.array([t.net_pnl_bps for t in resolved], dtype=float)
    gross = float(sum(t.gross_pnl_bps for t in resolved))
    cost = float(sum(t.cost_bps for t in resolved))
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    hit_rate = float(len(wins)) / float(len(net))
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(-losses.sum()) if losses.size else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0.0 else math.inf
    mean_net = float(net.mean())
    std_net = float(net.std(ddof=1)) if len(net) > 1 else 0.0
    sharpe = (mean_net / std_net) if std_net > 0.0 else math.nan
    downside = net[net < 0.0]
    downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sortino = (mean_net / downside_std) if downside_std > 0.0 else math.nan

    return StatisticalBacktestMetrics(
        trade_count=len(resolved),
        gross_pnl_bps=gross,
        cost_bps=cost,
        net_pnl_bps=float(net.sum()),
        hit_rate=hit_rate,
        profit_factor=profit_factor,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown_bps=_max_drawdown_bps(net),
        avg_win_bps=float(wins.mean()) if wins.size else math.nan,
        avg_loss_bps=float(losses.mean()) if losses.size else math.nan,
        avg_bars_held=float(np.mean([t.bars_held for t in resolved])),
        turnover_notional=float(len(resolved) * target_notional),
    )


def _max_drawdown_bps(net_pnl_bps: np.ndarray) -> float:
    cumulative = np.cumsum(net_pnl_bps)
    running_peak = np.maximum.accumulate(cumulative)
    drawdown = running_peak - cumulative
    return float(drawdown.max()) if drawdown.size else 0.0


def _pair_symbols(pair: str) -> tuple[str, str]:
    parts = [part.strip() for part in str(pair).strip().upper().split("/")]
    if len(parts) != PAIR_SYMBOL_COUNT or not all(parts):
        raise StatisticalBacktestError(f"invalid pair id: {pair!r}")
    return parts[0], parts[1]


def _pair_frame(bars: pd.DataFrame, symbol_a: str, symbol_b: str) -> pd.DataFrame:
    required = {"symbol", "open_time", "log_price"}
    missing = required.difference(bars.columns)
    if missing:
        raise StatisticalBacktestError(f"bars missing required columns: {sorted(missing)}")
    left = (
        bars.loc[bars["symbol"] == symbol_a, ["open_time", "log_price"]]
        .rename(columns={"log_price": "log_price_a"})
        .copy()
    )
    right = (
        bars.loc[bars["symbol"] == symbol_b, ["open_time", "log_price"]]
        .rename(columns={"log_price": "log_price_b"})
        .copy()
    )
    for symbol, frame in ((symbol_a, left), (symbol_b, right)):
        if frame["open_time"].duplicated().any():
            raise StatisticalBacktestError(f"duplicate open_time rows for symbol {symbol!r}")
    joined = left.merge(right, on="open_time", how="inner", sort=True).dropna()
    return joined.reset_index(drop=True)


def _positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StatisticalBacktestError(f"{name} must be an integer")
    if value <= 0:
        raise StatisticalBacktestError(f"{name} must be positive")


def _positive_finite(name: str, value: float) -> None:
    _finite(name, value)
    if value <= 0.0:
        raise StatisticalBacktestError(f"{name} must be positive")


def _non_negative_finite(name: str, value: float) -> None:
    _finite(name, value)
    if value < 0.0:
        raise StatisticalBacktestError(f"{name} must be non-negative")


def _finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise StatisticalBacktestError(f"{name} must be numeric")
    if not math.isfinite(value):
        raise StatisticalBacktestError(f"{name} must be finite")


__all__ = [
    "StatisticalBacktestConfig",
    "StatisticalBacktestError",
    "StatisticalBacktestMetrics",
    "StatisticalTradeResult",
    "TradeStatus",
    "resolve_trade_pnl",
    "run_pair_statistical_backtest",
    "summarize_statistical_backtest",
]
