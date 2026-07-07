"""Cross-sectional funding-rate carry backtest.

Implements the hypothesis pre-registered in
`tasks/funding_carry/TASK-FUND-001-define-hypothesis.md` (see
`project_control/DECISIONS.md` ADR-0013): at each real Binance funding
settlement (~3x/day, every 8h), rank the universe by `funding_rate_asof`
and go short the K symbols with the highest funding rate (short receives
funding when the rate is positive) and long the K symbols with the lowest
funding rate (long pays less, or receives, when the rate is low/negative),
equal-notional, dollar-neutral, fully rebalanced every interval.

`funding_rate_asof` is already causal: `historical_dataset.py::_merge_funding_asof`
joins it via `pd.merge_asof(..., direction="backward")` on `close_time`, so
at any bar it reflects only the most recently *settled* funding rate, never
a future one. This module only reads that column; it does not re-derive or
alter its causality.

Cost model (fase 1, per ADR-0013): a conservative FIXED round-trip cost per
leg, reusing the same constant and "estimate, not measurement" framing
already established for the canonical Sprint 8 backtest
(`src/backtest/statistical_backtest.py`) -- not the tick-level real-execution
simulation (that is fase 2, deferred until fase 1 clears its own gate).

``run_incremental_funding_carry_backtest`` (TASK-FUND-003, per
`tasks/funding_carry/TASK-FUND-003-incremental-rebalancing.md`) implements
the same signal and the same PnL/sign convention, but only trades a leg
when a swap clears a pre-registered yield threshold -- reusing
``cost_bps_per_leg_roundtrip`` itself as the threshold, so no new tunable
parameter is introduced beyond what fase 1 already pre-registered.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

HOUR_MS = 60 * 60 * 1000
DEFAULT_REBALANCE_INTERVAL_HOURS = 8
DEFAULT_COST_BPS_PER_LEG_ROUNDTRIP = 6.0
DEFAULT_MIN_REBALANCES_FOR_GATE = 500
DEFAULT_PROFIT_FACTOR_GATE = 1.10
_REQUIRED_COLUMNS = ("symbol", "open_time", "funding_rate_asof", "log_price")


class FundingCarryError(ValueError):
    """Raised when funding-carry backtest inputs are invalid."""


class RebalanceStatus(StrEnum):
    """Outcome of attempting one cross-sectional rebalance."""

    RESOLVED = "RESOLVED"
    INSUFFICIENT_SYMBOLS = "INSUFFICIENT_SYMBOLS"
    NO_DATA = "NO_DATA"


@dataclass(frozen=True, slots=True)
class FundingCarryConfig:
    """Pre-registered configuration for one funding-carry backtest run.

    ``k`` is the only parameter this project's pre-registration allows to
    vary across a run (K=5 primary, K=3/K=8 descriptive-only per
    TASK-FUND-001) -- no other field should be swept after seeing a result.
    """

    k: int
    rebalance_interval_hours: int = DEFAULT_REBALANCE_INTERVAL_HOURS
    cost_bps_per_leg_roundtrip: float = DEFAULT_COST_BPS_PER_LEG_ROUNDTRIP
    min_rebalances_for_gate: int = DEFAULT_MIN_REBALANCES_FOR_GATE
    profit_factor_gate: float = DEFAULT_PROFIT_FACTOR_GATE

    def __post_init__(self) -> None:
        if self.k < 1:
            raise FundingCarryError("k must be >= 1")
        if self.rebalance_interval_hours < 1:
            raise FundingCarryError("rebalance_interval_hours must be >= 1")
        cost = self.cost_bps_per_leg_roundtrip
        if not math.isfinite(cost) or cost < 0:
            raise FundingCarryError("cost_bps_per_leg_roundtrip must be finite and non-negative")
        if self.min_rebalances_for_gate < 1:
            raise FundingCarryError("min_rebalances_for_gate must be >= 1")
        if not math.isfinite(self.profit_factor_gate) or self.profit_factor_gate <= 0:
            raise FundingCarryError("profit_factor_gate must be finite and positive")


@dataclass(frozen=True, slots=True)
class RebalanceResult:
    """Result of one cross-sectional rebalance attempt."""

    rebalance_time: int
    status: RebalanceStatus
    eligible_symbol_count: int
    long_symbols: tuple[str, ...]
    short_symbols: tuple[str, ...]
    funding_pnl_bps: float
    price_pnl_bps: float
    cost_bps: float
    gross_pnl_bps: float
    net_pnl_bps: float


@dataclass(frozen=True, slots=True)
class FundingCarrySummary:
    """Aggregate metrics across all resolved rebalances."""

    rebalance_count: int
    resolved_count: int
    insufficient_symbols_count: int
    no_data_count: int
    gross_pnl_bps: float
    funding_pnl_bps: float
    price_pnl_bps: float
    cost_bps: float
    net_pnl_bps: float
    profit_factor: float
    hit_rate: float
    avg_net_pnl_bps: float
    profit_factor_gate_pass: bool


def run_funding_carry_backtest(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
) -> tuple[RebalanceResult, ...]:
    """Run the pre-registered cross-sectional funding-carry backtest.

    ``bars`` must contain one row per (symbol, open_time) with at least
    ``symbol``, ``open_time``, ``funding_rate_asof``, and ``log_price``.
    Duplicate (symbol, open_time) rows fail closed rather than silently
    picking one.
    """

    indexed, interval_ms, rebalance_times = _build_indexed_frame_and_rebalance_times(bars, config)

    results = []
    for t in rebalance_times:
        results.append(_resolve_rebalance(indexed, t, interval_ms, config))
    return tuple(results)


def _build_indexed_frame_and_rebalance_times(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
) -> tuple[pd.DataFrame, int, list[int]]:
    """Shared validation/indexing for both the fase-1 and incremental backtests."""

    missing = [column for column in _REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise FundingCarryError(f"missing required columns: {missing}")

    frame = bars[list(_REQUIRED_COLUMNS)].copy()
    duplicate_mask = frame.duplicated(subset=["open_time", "symbol"])
    if bool(duplicate_mask.any()):
        raise FundingCarryError("duplicate (symbol, open_time) rows are not allowed")

    total_symbols = frame["symbol"].nunique()
    if 2 * config.k > total_symbols:
        raise FundingCarryError(
            f"k={config.k} requires 2*k={2 * config.k} symbols, "
            f"but the universe only has {total_symbols}"
        )

    indexed = frame.set_index(["open_time", "symbol"]).sort_index()
    interval_ms = config.rebalance_interval_hours * HOUR_MS
    interval_hours = config.rebalance_interval_hours
    open_times = indexed.index.get_level_values(0)
    rebalance_times = sorted(
        {int(t) for t in open_times.unique() if (int(t) // HOUR_MS) % interval_hours == 0}
    )
    return indexed, interval_ms, rebalance_times


def _resolve_rebalance(
    indexed: pd.DataFrame,
    t: int,
    interval_ms: int,
    config: FundingCarryConfig,
) -> RebalanceResult:
    forward_time = t + interval_ms
    known_times = indexed.index.get_level_values(0)
    if t not in known_times or forward_time not in known_times:
        return _empty_result(t, RebalanceStatus.NO_DATA)

    snapshot = indexed.loc[t]
    forward = indexed.loc[forward_time]

    eligible = _eligible_symbols(snapshot, forward)
    if len(eligible) < 2 * config.k:
        return _empty_result(
            t, RebalanceStatus.INSUFFICIENT_SYMBOLS, eligible_symbol_count=len(eligible)
        )

    ranked = snapshot.loc[list(eligible), "funding_rate_asof"].sort_values(kind="mergesort")
    long_symbols = tuple(ranked.index[: config.k])
    short_symbols = tuple(ranked.index[-config.k :])

    weight = 1.0 / (2.0 * config.k)
    funding_pnl_bps, price_pnl_bps = _book_funding_and_price_pnl_bps(
        snapshot, forward, long_symbols, short_symbols, weight
    )
    gross_pnl_bps = funding_pnl_bps + price_pnl_bps
    cost_bps = config.cost_bps_per_leg_roundtrip
    net_pnl_bps = gross_pnl_bps - cost_bps

    return RebalanceResult(
        rebalance_time=t,
        status=RebalanceStatus.RESOLVED,
        eligible_symbol_count=len(eligible),
        long_symbols=long_symbols,
        short_symbols=short_symbols,
        funding_pnl_bps=funding_pnl_bps,
        price_pnl_bps=price_pnl_bps,
        cost_bps=cost_bps,
        gross_pnl_bps=gross_pnl_bps,
        net_pnl_bps=net_pnl_bps,
    )


def _eligible_symbols(snapshot: pd.DataFrame, forward: pd.DataFrame) -> set[str]:
    return {
        symbol
        for symbol in snapshot.index
        if symbol in forward.index
        and math.isfinite(snapshot.loc[symbol, "funding_rate_asof"])
        and math.isfinite(snapshot.loc[symbol, "log_price"])
        and math.isfinite(forward.loc[symbol, "log_price"])
    }


def _book_funding_and_price_pnl_bps(
    snapshot: pd.DataFrame,
    forward: pd.DataFrame,
    long_symbols: tuple[str, ...],
    short_symbols: tuple[str, ...],
    weight: float,
) -> tuple[float, float]:
    """Shared PnL formula for both the fase-1 and incremental backtests.

    Binance mechanics: fundingRate > 0 means longs pay shorts. A LONG
    position's funding PnL fraction is therefore -funding_rate (pays when
    positive, receives when negative); its price PnL fraction is the raw
    price_return (gains when price rises). A SHORT position is the mirror
    image of both: +funding_rate, -price_return. Independently verified by
    adversarial review (see HANDOFFS.md).
    """

    funding_frac = 0.0
    price_frac = 0.0
    for symbol in long_symbols:
        funding_rate = float(snapshot.loc[symbol, "funding_rate_asof"])
        price_return = _price_return(snapshot, forward, symbol)
        funding_frac += weight * (-funding_rate)
        price_frac += weight * price_return
    for symbol in short_symbols:
        funding_rate = float(snapshot.loc[symbol, "funding_rate_asof"])
        price_return = _price_return(snapshot, forward, symbol)
        funding_frac += weight * funding_rate
        price_frac += weight * (-price_return)
    return funding_frac * 10_000.0, price_frac * 10_000.0


def _price_return(snapshot: pd.DataFrame, forward: pd.DataFrame, symbol: str) -> float:
    return float(forward.loc[symbol, "log_price"]) - float(snapshot.loc[symbol, "log_price"])


def _empty_result(
    t: int,
    status: RebalanceStatus,
    eligible_symbol_count: int = 0,
) -> RebalanceResult:
    return RebalanceResult(
        rebalance_time=t,
        status=status,
        eligible_symbol_count=eligible_symbol_count,
        long_symbols=(),
        short_symbols=(),
        funding_pnl_bps=0.0,
        price_pnl_bps=0.0,
        cost_bps=0.0,
        gross_pnl_bps=0.0,
        net_pnl_bps=0.0,
    )


@dataclass(frozen=True, slots=True)
class IncrementalRebalanceResult:
    """Result of one incremental (yield-threshold) rebalance attempt.

    Structurally compatible with ``summarize_funding_carry_backtest`` (same
    ``status``/``*_pnl_bps``/``cost_bps`` field names), so fase-1 and
    TASK-FUND-003 results can be summarized by the same function.
    """

    rebalance_time: int
    status: RebalanceStatus
    held_long: tuple[str, ...]
    held_short: tuple[str, ...]
    swap_count: int
    funding_pnl_bps: float
    price_pnl_bps: float
    cost_bps: float
    gross_pnl_bps: float
    net_pnl_bps: float


def run_incremental_funding_carry_backtest(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
) -> tuple[IncrementalRebalanceResult, ...]:
    """Run the TASK-FUND-003 incremental (yield-threshold) funding-carry backtest.

    Same universe, signal, rebalance grid, sign convention, and gate as
    ``run_funding_carry_backtest``. The only difference: a held leg is kept
    from one interval to the next unless a swap clears the pre-registered
    yield threshold (the swap's funding-rate improvement, in bps, must
    exceed ``cost_bps_per_leg_roundtrip`` -- the same constant fase 1
    already used, no new parameter). Only legs that actually enter or exit
    pay ``cost_bps_per_leg_roundtrip`` that interval; legs held unchanged
    pay nothing. The book is bootstrapped fresh (identical to fase 1, same
    flat cost) whenever it starts empty (the first successful rebalance, or
    after a hypothetical mass-ineligibility wipeout that this real dataset
    never exercises).
    """

    indexed, interval_ms, rebalance_times = _build_indexed_frame_and_rebalance_times(bars, config)
    weight = 1.0 / (2.0 * config.k)

    held_long: tuple[str, ...] = ()
    held_short: tuple[str, ...] = ()
    results = []
    for t in rebalance_times:
        forward_time = t + interval_ms
        known_times = indexed.index.get_level_values(0)
        if t not in known_times or forward_time not in known_times:
            results.append(
                _empty_incremental_result(t, RebalanceStatus.NO_DATA, held_long, held_short)
            )
            continue

        snapshot = indexed.loc[t]
        forward = indexed.loc[forward_time]
        eligible = _eligible_symbols(snapshot, forward)

        held_long = tuple(symbol for symbol in held_long if symbol in eligible)
        held_short = tuple(symbol for symbol in held_short if symbol in eligible)
        held = set(held_long) | set(held_short)
        pool = [symbol for symbol in eligible if symbol not in held]

        held_long_list, pool, refill_long = _refill_vacancies(
            snapshot, list(held_long), pool, config.k, ascending=True
        )
        held_short_list, pool, refill_short = _refill_vacancies(
            snapshot, list(held_short), pool, config.k, ascending=False
        )
        held_long, held_short, voluntary_swaps = _apply_yield_threshold_swaps(
            snapshot, tuple(held_long_list), tuple(held_short_list), pool, config
        )
        swap_count = refill_long + refill_short + voluntary_swaps

        funding_pnl_bps, price_pnl_bps = _book_funding_and_price_pnl_bps(
            snapshot, forward, held_long, held_short, weight
        )
        gross_pnl_bps = funding_pnl_bps + price_pnl_bps
        cost_bps = swap_count * weight * config.cost_bps_per_leg_roundtrip
        net_pnl_bps = gross_pnl_bps - cost_bps

        results.append(
            IncrementalRebalanceResult(
                rebalance_time=t,
                status=RebalanceStatus.RESOLVED,
                held_long=held_long,
                held_short=held_short,
                swap_count=swap_count,
                funding_pnl_bps=funding_pnl_bps,
                price_pnl_bps=price_pnl_bps,
                cost_bps=cost_bps,
                gross_pnl_bps=gross_pnl_bps,
                net_pnl_bps=net_pnl_bps,
            )
        )
    return tuple(results)


def _refill_vacancies(
    snapshot: pd.DataFrame,
    held: list[str],
    pool: list[str],
    k: int,
    *,
    ascending: bool,
) -> tuple[list[str], list[str], int]:
    """Fill empty slots (bootstrap or forced exits) unconditionally, best-first.

    Holding an empty slot is strictly worse than holding any real eligible
    candidate, so this never checks the yield threshold -- it always fills
    what it can, up to ``k``, greedily taking the lowest funding rate
    (``ascending=True``, for the long side) or the highest (``ascending=False``,
    for the short side) from the shared candidate pool first.
    """

    held = list(held)
    pool = list(pool)
    refill_count = 0
    while len(held) < k and pool:
        best_index = _extreme_funding_index(snapshot, pool, pick_max=not ascending)
        held.append(pool.pop(best_index))
        refill_count += 1
    return held, pool, refill_count


def _extreme_funding_index(snapshot: pd.DataFrame, symbols: list[str], *, pick_max: bool) -> int:
    """Index of the symbol with the highest (``pick_max``) or lowest funding_rate_asof."""

    rates = [float(snapshot.loc[symbol, "funding_rate_asof"]) for symbol in symbols]
    return rates.index(max(rates)) if pick_max else rates.index(min(rates))


def _apply_yield_threshold_swaps(
    snapshot: pd.DataFrame,
    held_long: tuple[str, ...],
    held_short: tuple[str, ...],
    pool: list[str],
    config: FundingCarryConfig,
) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    """Greedily swap the worst held leg for the best pool candidate while it pays.

    A swap on the LONG side (which wants the lowest funding rate) fires only
    when the currently-worst-held long leg's funding rate exceeds the best
    available candidate's by more than ``cost_bps_per_leg_roundtrip`` (in
    bps) -- the pre-registered yield threshold, reusing the existing cost
    constant instead of a new tunable parameter. The SHORT side is the
    mirror image. The candidate pool is fixed for the whole interval (no
    intra-interval recycling of just-exited symbols).
    """

    held_long = list(held_long)
    held_short = list(held_short)
    pool = list(pool)
    threshold_bps = config.cost_bps_per_leg_roundtrip
    swap_count = 0

    while held_long and pool:
        worst_index = _extreme_funding_index(snapshot, held_long, pick_max=True)
        best_index = _extreme_funding_index(snapshot, pool, pick_max=False)
        worst_rate = float(snapshot.loc[held_long[worst_index], "funding_rate_asof"])
        candidate_rate = float(snapshot.loc[pool[best_index], "funding_rate_asof"])
        gain_bps = (worst_rate - candidate_rate) * 10_000.0
        if gain_bps <= threshold_bps:
            break
        held_long[worst_index] = pool.pop(best_index)
        swap_count += 1

    while held_short and pool:
        worst_index = _extreme_funding_index(snapshot, held_short, pick_max=False)
        best_index = _extreme_funding_index(snapshot, pool, pick_max=True)
        worst_rate = float(snapshot.loc[held_short[worst_index], "funding_rate_asof"])
        candidate_rate = float(snapshot.loc[pool[best_index], "funding_rate_asof"])
        gain_bps = (candidate_rate - worst_rate) * 10_000.0
        if gain_bps <= threshold_bps:
            break
        held_short[worst_index] = pool.pop(best_index)
        swap_count += 1

    return tuple(held_long), tuple(held_short), swap_count


def _empty_incremental_result(
    t: int,
    status: RebalanceStatus,
    held_long: tuple[str, ...],
    held_short: tuple[str, ...],
) -> IncrementalRebalanceResult:
    return IncrementalRebalanceResult(
        rebalance_time=t,
        status=status,
        held_long=held_long,
        held_short=held_short,
        swap_count=0,
        funding_pnl_bps=0.0,
        price_pnl_bps=0.0,
        cost_bps=0.0,
        gross_pnl_bps=0.0,
        net_pnl_bps=0.0,
    )


def summarize_funding_carry_backtest(
    results: tuple[RebalanceResult, ...] | tuple[IncrementalRebalanceResult, ...],
    config: FundingCarryConfig,
) -> FundingCarrySummary:
    """Aggregate resolved rebalances and evaluate the pre-registered gate.

    Works for both fase-1 (``RebalanceResult``) and TASK-FUND-003
    (``IncrementalRebalanceResult``) results -- both share the same
    ``status``/``*_pnl_bps``/``cost_bps`` fields this function reads.
    """

    resolved = tuple(r for r in results if r.status is RebalanceStatus.RESOLVED)
    insufficient = sum(1 for r in results if r.status is RebalanceStatus.INSUFFICIENT_SYMBOLS)
    no_data = sum(1 for r in results if r.status is RebalanceStatus.NO_DATA)

    resolved_count = len(resolved)
    gross_pnl_bps = sum(r.gross_pnl_bps for r in resolved)
    funding_pnl_bps = sum(r.funding_pnl_bps for r in resolved)
    price_pnl_bps = sum(r.price_pnl_bps for r in resolved)
    cost_bps = sum(r.cost_bps for r in resolved)
    net_pnl_bps = sum(r.net_pnl_bps for r in resolved)

    gains = sum(r.net_pnl_bps for r in resolved if r.net_pnl_bps > 0.0)
    losses = sum(r.net_pnl_bps for r in resolved if r.net_pnl_bps < 0.0)
    if resolved_count == 0:
        profit_factor = float("nan")
    elif losses == 0.0:
        profit_factor = float("inf") if gains > 0.0 else float("nan")
    else:
        profit_factor = gains / abs(losses)

    hit_rate = (
        sum(1 for r in resolved if r.net_pnl_bps > 0.0) / resolved_count
        if resolved_count > 0
        else float("nan")
    )
    avg_net_pnl_bps = net_pnl_bps / resolved_count if resolved_count > 0 else float("nan")

    gate_pass = (
        not math.isnan(profit_factor)
        and profit_factor >= config.profit_factor_gate
        and resolved_count >= config.min_rebalances_for_gate
    )

    return FundingCarrySummary(
        rebalance_count=len(results),
        resolved_count=resolved_count,
        insufficient_symbols_count=insufficient,
        no_data_count=no_data,
        gross_pnl_bps=gross_pnl_bps,
        funding_pnl_bps=funding_pnl_bps,
        price_pnl_bps=price_pnl_bps,
        cost_bps=cost_bps,
        net_pnl_bps=net_pnl_bps,
        profit_factor=profit_factor,
        hit_rate=hit_rate,
        avg_net_pnl_bps=avg_net_pnl_bps,
        profit_factor_gate_pass=gate_pass,
    )


__all__ = [
    "FundingCarryConfig",
    "FundingCarryError",
    "FundingCarrySummary",
    "IncrementalRebalanceResult",
    "RebalanceResult",
    "RebalanceStatus",
    "run_funding_carry_backtest",
    "run_incremental_funding_carry_backtest",
    "summarize_funding_carry_backtest",
]
