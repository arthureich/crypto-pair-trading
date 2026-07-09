"""Leg-level feature/label panel for the TASK-ML-001 meta-labeling filter.

Pre-registered in `docs/pre_registers/TASK-ML-001.md` (ADR-0026). Builds
the supervised panel the meta-model learns from: one row per ENTRY/SWAP
that the UNCHANGED incremental funding-carry policy (K=5) actually made,
with 9 causal features known at the entry time and a binary label = was
that leg net-profitable over its realized hold.

Reuse, not reimplementation:
  - The primary policy is run verbatim via
    `run_incremental_funding_carry_backtest`; this module only reads the
    held-set sequence it produces and diffs consecutive resolved
    rebalances to recover entries/exits.
  - Per-leg PnL uses `leg_pnl_fracs` from `funding_carry.py`, the single
    source of the Binance sign convention -- no PnL formula is redefined
    here.
  - The 6 regime features replicate TASK-ALT-003 / Family J exactly
    (same causal windows and shift(1)-before-rolling construction); the 3
    funding-native features are defined in the pre-registration.

Causality: every feature is computed from data known at the entry time t
(shift(1) before any rolling window). The LABEL is the only value that
uses data after t. Warm-up rows whose rolling features are not yet
defined are dropped (count exposed in ``frame.attrs["n_dropped_warmup"]``).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from src.research.funding_carry import (
    FundingCarryConfig,
    IncrementalRebalanceResult,
    RebalanceStatus,
    _book_funding_and_price_pnl_bps,
    _build_indexed_frame_and_rebalance_times,
    _eligible_symbols,
    _empty_incremental_result,
    _extreme_funding_index,
    leg_pnl_fracs,
    run_incremental_funding_carry_backtest,
)

# entry_gate(symbol, side, decision_time_ms) -> True to allow the entry/swap.
EntryGate = Callable[[str, str, int], bool]


def _allow_all_entries(symbol: str, side: str, decision_time_ms: int) -> bool:  # noqa: ARG001
    return True


FORWARD_HORIZON_HOURS = 24
WEEK_HOURS = 168
ROLLING_WINDOW_HOURS = 2160  # 90 days, causal (shift(1) before rolling)

REGIME_FEATURE_NAMES = (
    "realized_vol_24h",
    "realized_vol_168h",
    "trend_intensity_168h",
    "volume_shock_24h",
    "market_dispersion_24h",
    "market_abs_return_24h",
)
FUNDING_FEATURE_NAMES = (
    "funding_rate_asof",
    "funding_zscore",
    "cross_sectional_rank",
)
FEATURE_NAMES = REGIME_FEATURE_NAMES + FUNDING_FEATURE_NAMES

PANEL_COLUMNS = (
    "decision_time_ms",
    "label_end_time_ms",
    "symbol",
    "side",
    *FEATURE_NAMES,
    "net_pnl_bps",
    "label",
)

_BARS_REQUIRED_COLUMNS = ("symbol", "open_time", "log_price", "quote_volume", "funding_rate_asof")


class MetaLabelingError(ValueError):
    """Raised when meta-labeling panel inputs are invalid."""


def build_meta_label_panel(bars: pd.DataFrame, config: FundingCarryConfig) -> pd.DataFrame:
    """Build the leg-level feature/label panel for TASK-ML-001.

    Returns one row per entry/swap the incremental policy made, with the 9
    causal features and a binary ``label``. Rows whose features fall in the
    rolling warm-up window (undefined) are dropped;
    ``frame.attrs["n_dropped_warmup"]`` records how many.
    """

    _validate_bars(bars)
    features = _build_feature_frames(bars)
    entries = _reconstruct_entries(bars, config)

    rows: list[dict[str, object]] = []
    dropped_warmup = 0
    for entry in entries:
        feature_values = _lookup_features(features, entry["decision_time_ms"], entry["symbol"])
        if feature_values is None:
            dropped_warmup += 1
            continue
        rows.append({**entry, **feature_values})

    frame = pd.DataFrame(rows, columns=list(PANEL_COLUMNS))
    frame.attrs["n_entries_total"] = len(entries)
    frame.attrs["n_dropped_warmup"] = dropped_warmup
    return frame


def build_leg_interval_panel(bars: pd.DataFrame, config: FundingCarryConfig) -> pd.DataFrame:
    """Build the per-(leg, interval) feature/label panel for TASK-ML-001 (Option 2).

    One row per leg-slot the UNALTERED incremental policy holds during each
    resolved rebalance (newly entered or carried), labelled by that single
    interval's net PnL: funding +/- price return over [t, t+interval] at the
    fixed 1/(2K) weight, minus the per-leg entry cost only in the interval
    the leg entered. This yields tens of thousands of rows (vs ~38 for the
    entry-only unit), enough to train the meta-model. Warm-up rows with
    undefined features are dropped (``frame.attrs["n_dropped_warmup"]``).
    """

    _validate_bars(bars)
    features = _build_feature_frames(bars)
    results = run_incremental_funding_carry_backtest(bars, config)
    indexed, interval_ms, _ = _build_indexed_frame_and_rebalance_times(bars, config)
    weight = 1.0 / (2.0 * config.k)
    entry_cost_bps = weight * config.cost_bps_per_leg_roundtrip

    rows: list[dict[str, object]] = []
    dropped_warmup = 0
    previous_held: set[tuple[str, str]] = set()
    for result in results:
        if result.status is not RebalanceStatus.RESOLVED:
            continue  # policy holds carry through NO_DATA; no interval PnL
        t = int(result.rebalance_time)
        snapshot = indexed.loc[t]
        forward = indexed.loc[t + interval_ms]
        current = {(symbol, "long") for symbol in result.held_long}
        current |= {(symbol, "short") for symbol in result.held_short}

        for symbol, side in current:
            leg_funding, leg_price = leg_pnl_fracs(
                snapshot, forward, symbol, is_long=(side == "long"), weight=weight
            )
            gross_bps = (leg_funding + leg_price) * 10_000.0
            entered = (symbol, side) not in previous_held
            net_pnl_bps = gross_bps - (entry_cost_bps if entered else 0.0)
            feature_values = _lookup_features(features, t, symbol)
            if feature_values is None:
                dropped_warmup += 1
                continue
            rows.append(
                {
                    "decision_time_ms": t,
                    "label_end_time_ms": t + interval_ms,
                    "symbol": symbol,
                    "side": side,
                    "net_pnl_bps": net_pnl_bps,
                    "label": 1 if net_pnl_bps > 0.0 else 0,
                    **feature_values,
                }
            )
        previous_held = current

    frame = pd.DataFrame(rows, columns=list(PANEL_COLUMNS))
    frame.attrs["n_dropped_warmup"] = dropped_warmup
    return frame


def _validate_bars(bars: pd.DataFrame) -> None:
    missing = [column for column in _BARS_REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise MetaLabelingError(f"missing required columns: {missing}")
    if bars.duplicated(["symbol", "open_time"]).any():
        raise MetaLabelingError("duplicate (symbol, open_time) rows are not allowed")


def _reconstruct_entries(bars: pd.DataFrame, config: FundingCarryConfig) -> list[dict[str, object]]:
    """Diff consecutive resolved held-sets to recover each entry and its hold PnL."""

    results = run_incremental_funding_carry_backtest(bars, config)
    indexed, interval_ms, _ = _build_indexed_frame_and_rebalance_times(bars, config)
    weight = 1.0 / (2.0 * config.k)
    entry_cost_bps = weight * config.cost_bps_per_leg_roundtrip

    open_legs: dict[tuple[str, str], dict[str, float]] = {}
    finalized: list[dict[str, object]] = []
    last_resolved_forward_time: int | None = None

    for result in results:
        if result.status is not RebalanceStatus.RESOLVED:
            continue
        t = int(result.rebalance_time)
        forward_time = t + interval_ms
        last_resolved_forward_time = forward_time

        current = {(symbol, "long") for symbol in result.held_long}
        current |= {(symbol, "short") for symbol in result.held_short}

        for key in set(open_legs).difference(current):
            finalized.append(_finalize_leg(open_legs.pop(key), key, t, entry_cost_bps))
        for key in current.difference(open_legs):
            open_legs[key] = {"entry_time": float(t), "funding_bps": 0.0, "price_bps": 0.0}

        snapshot = indexed.loc[t]
        forward = indexed.loc[forward_time]
        for symbol, side in current:
            leg_funding, leg_price = leg_pnl_fracs(
                snapshot, forward, symbol, is_long=(side == "long"), weight=weight
            )
            record = open_legs[(symbol, side)]
            record["funding_bps"] += leg_funding * 10_000.0
            record["price_bps"] += leg_price * 10_000.0

    if last_resolved_forward_time is not None:
        for key, record in open_legs.items():
            finalized.append(_finalize_leg(record, key, last_resolved_forward_time, entry_cost_bps))

    return finalized


def _finalize_leg(
    record: dict[str, float],
    key: tuple[str, str],
    label_end_time: int,
    entry_cost_bps: float,
) -> dict[str, object]:
    symbol, side = key
    net_pnl_bps = record["funding_bps"] + record["price_bps"] - entry_cost_bps
    return {
        "decision_time_ms": int(record["entry_time"]),
        "label_end_time_ms": int(label_end_time),
        "symbol": symbol,
        "side": side,
        "net_pnl_bps": net_pnl_bps,
        "label": 1 if net_pnl_bps > 0.0 else 0,
    }


def _build_feature_frames(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute the 9 causal feature wide-frames (open_time x symbol)."""

    working = bars[list(_BARS_REQUIRED_COLUMNS)].copy()
    working["open_time"] = pd.to_numeric(working["open_time"], errors="raise")
    for column in ("log_price", "quote_volume", "funding_rate_asof"):
        working[column] = pd.to_numeric(working[column], errors="raise")

    price_wide = working.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    volume_wide = working.pivot(
        index="open_time", columns="symbol", values="quote_volume"
    ).sort_index()
    funding_wide = working.pivot(
        index="open_time", columns="symbol", values="funding_rate_asof"
    ).sort_index()

    hourly_return = price_wide.diff()
    return_24h = price_wide.diff(FORWARD_HORIZON_HOURS)

    realized_vol_24h = hourly_return.shift(1).rolling(FORWARD_HORIZON_HOURS).std()
    realized_vol_168h = hourly_return.shift(1).rolling(WEEK_HOURS).std()

    trend_denominator = (realized_vol_168h * np.sqrt(WEEK_HOURS)).replace(0.0, np.nan)
    past_return_168h = price_wide - price_wide.shift(WEEK_HOURS)
    trend_intensity_168h = past_return_168h.abs() / trend_denominator

    quote_volume_24h = volume_wide.shift(1).rolling(FORWARD_HORIZON_HOURS).sum()
    volume_shock_24h = _zscore_causal(np.log1p(quote_volume_24h))

    market_dispersion_24h = _repeat_context(return_24h.std(axis=1), price_wide.columns)
    market_abs_return_24h = _repeat_context(return_24h.mean(axis=1).abs(), price_wide.columns)

    funding_zscore = _zscore_causal(funding_wide)
    cross_sectional_rank = funding_wide.rank(axis=1, pct=True)

    return {
        "realized_vol_24h": realized_vol_24h,
        "realized_vol_168h": realized_vol_168h,
        "trend_intensity_168h": trend_intensity_168h,
        "volume_shock_24h": volume_shock_24h,
        "market_dispersion_24h": market_dispersion_24h,
        "market_abs_return_24h": market_abs_return_24h,
        "funding_rate_asof": funding_wide,
        "funding_zscore": funding_zscore,
        "cross_sectional_rank": cross_sectional_rank,
    }


def _zscore_causal(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    return (wide - mean) / std


def _repeat_context(series: pd.Series, columns: pd.Index) -> pd.DataFrame:
    repeated = pd.concat([series] * len(columns), axis=1)
    repeated.columns = columns
    return repeated


def _lookup_features(
    features: dict[str, pd.DataFrame], time_ms: int, symbol: str
) -> dict[str, float] | None:
    values: dict[str, float] = {}
    for name in FEATURE_NAMES:
        wide = features[name]
        if time_ms not in wide.index or symbol not in wide.columns:
            return None
        value = wide.at[time_ms, symbol]
        if value is None or not np.isfinite(value):
            return None
        values[name] = float(value)
    return values


def run_filtered_incremental_backtest(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
    entry_gate: EntryGate = _allow_all_entries,
) -> tuple[IncrementalRebalanceResult, ...]:
    """Incremental funding-carry policy with a meta-model veto on entries/swaps.

    Mirrors ``run_incremental_funding_carry_backtest`` exactly, but every
    NEW leg the policy would enter (a refill of an empty slot or a
    yield-threshold swap) must first be approved by ``entry_gate``. A vetoed
    candidate simply stays in the pool, so the slot is filled by the best
    APPROVED candidate instead, or left in cash if none is approved. Held
    legs are never touched by the gate -- only entries are.

    The primary policy in ``funding_carry.py`` is left byte-for-byte
    unchanged (the pre-registered invariant); this is a separate evaluation
    runner. ``test_meta_labeling.py`` proves that with the default
    allow-all gate this reproduces the canonical backtest exactly, guarding
    against any divergence in the re-expressed loop.
    """

    indexed, interval_ms, rebalance_times = _build_indexed_frame_and_rebalance_times(bars, config)
    weight = 1.0 / (2.0 * config.k)
    # Hoisted once (O(1) membership) -- the canonical loop recomputes this
    # per iteration, which is O(n^2); this runner is called ~1000x in CV.
    known_times = set(indexed.index.get_level_values(0).unique())

    held_long: tuple[str, ...] = ()
    held_short: tuple[str, ...] = ()
    results = []
    for t in rebalance_times:
        forward_time = t + interval_ms
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

        held_long_list, pool, refill_long = _gated_refill(
            snapshot,
            list(held_long),
            pool,
            config.k,
            ascending=True,
            side="long",
            entry_gate=entry_gate,
            decision_time_ms=int(t),
        )
        held_short_list, pool, refill_short = _gated_refill(
            snapshot,
            list(held_short),
            pool,
            config.k,
            ascending=False,
            side="short",
            entry_gate=entry_gate,
            decision_time_ms=int(t),
        )
        held_long, held_short, voluntary_swaps = _gated_swaps(
            snapshot,
            tuple(held_long_list),
            tuple(held_short_list),
            pool,
            config,
            entry_gate=entry_gate,
            decision_time_ms=int(t),
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


def _gated_refill(
    snapshot: pd.DataFrame,
    held: list[str],
    pool: list[str],
    k: int,
    *,
    ascending: bool,
    side: str,
    entry_gate: EntryGate,
    decision_time_ms: int,
) -> tuple[list[str], list[str], int]:
    """Refill empty slots best-first, but only with gate-approved candidates."""

    held = list(held)
    pool = list(pool)
    refill_count = 0
    while len(held) < k:
        approved = [symbol for symbol in pool if entry_gate(symbol, side, decision_time_ms)]
        if not approved:
            break
        index = _extreme_funding_index(snapshot, approved, pick_max=not ascending)
        chosen = approved[index]
        held.append(chosen)
        pool.remove(chosen)
        refill_count += 1
    return held, pool, refill_count


def _gated_swaps(
    snapshot: pd.DataFrame,
    held_long: tuple[str, ...],
    held_short: tuple[str, ...],
    pool: list[str],
    config: FundingCarryConfig,
    *,
    entry_gate: EntryGate,
    decision_time_ms: int,
) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    """Yield-threshold swaps, but only swapping in gate-approved candidates."""

    held_long = list(held_long)
    held_short = list(held_short)
    pool = list(pool)
    threshold_bps = config.cost_bps_per_leg_roundtrip
    swap_count = 0

    while held_long:
        approved = [symbol for symbol in pool if entry_gate(symbol, "long", decision_time_ms)]
        if not approved:
            break
        worst_index = _extreme_funding_index(snapshot, held_long, pick_max=True)
        candidate = approved[_extreme_funding_index(snapshot, approved, pick_max=False)]
        worst_rate = float(snapshot.loc[held_long[worst_index], "funding_rate_asof"])
        candidate_rate = float(snapshot.loc[candidate, "funding_rate_asof"])
        if (worst_rate - candidate_rate) * 10_000.0 <= threshold_bps:
            break
        held_long[worst_index] = candidate
        pool.remove(candidate)
        swap_count += 1

    while held_short:
        approved = [symbol for symbol in pool if entry_gate(symbol, "short", decision_time_ms)]
        if not approved:
            break
        worst_index = _extreme_funding_index(snapshot, held_short, pick_max=False)
        candidate = approved[_extreme_funding_index(snapshot, approved, pick_max=True)]
        worst_rate = float(snapshot.loc[held_short[worst_index], "funding_rate_asof"])
        candidate_rate = float(snapshot.loc[candidate, "funding_rate_asof"])
        if (candidate_rate - worst_rate) * 10_000.0 <= threshold_bps:
            break
        held_short[worst_index] = candidate
        pool.remove(candidate)
        swap_count += 1

    return tuple(held_long), tuple(held_short), swap_count


def run_leg_interval_filtered_backtest(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
    entry_gate: EntryGate = _allow_all_entries,
) -> tuple[IncrementalRebalanceResult, ...]:
    """Option-2 filter: veto held leg-slots per interval, renormalize the rest.

    The primary incremental policy runs UNALTERED (its held-set evolution is
    unchanged); the filter is a per-interval overlay. Each rebalance, any held
    leg the gate vetoes drops to cash for that interval; the kept legs on each
    side split 50% notional equally (dollar-neutral preserved). A leg the
    filtered book newly holds (kept now, not kept the prior interval) pays the
    per-leg entry cost at its current renormalized weight.

    With the default allow-all gate this reproduces
    ``run_incremental_funding_carry_backtest`` exactly (kept == held, weight
    0.5/K == 1/(2K), entries == swap_count) -- proven in the tests.
    """

    results = run_incremental_funding_carry_backtest(bars, config)
    indexed, interval_ms, _ = _build_indexed_frame_and_rebalance_times(bars, config)
    return filter_leg_interval_results(results, indexed, interval_ms, config, entry_gate)


def filter_leg_interval_results(
    results: tuple[IncrementalRebalanceResult, ...],
    indexed: pd.DataFrame,
    interval_ms: int,
    config: FundingCarryConfig,
    entry_gate: EntryGate,
) -> tuple[IncrementalRebalanceResult, ...]:
    """Apply the Option-2 per-interval veto to a PRECOMPUTED held-set sequence.

    Separated from the backtest so CV can run the (expensive) canonical policy
    once per span and reuse its held sets across every gate/threshold, instead
    of re-running it each time.
    """

    cost_bps = config.cost_bps_per_leg_roundtrip
    out: list[IncrementalRebalanceResult] = []
    previous_kept: set[tuple[str, str]] = set()
    for result in results:
        if result.status is not RebalanceStatus.RESOLVED:
            out.append(result)  # status-only; PnL summary ignores non-resolved
            continue
        t = int(result.rebalance_time)
        snapshot = indexed.loc[t]
        forward = indexed.loc[t + interval_ms]

        kept_long = [s for s in result.held_long if entry_gate(s, "long", t)]
        kept_short = [s for s in result.held_short if entry_gate(s, "short", t)]
        weight_long = 0.5 / len(kept_long) if kept_long else 0.0
        weight_short = 0.5 / len(kept_short) if kept_short else 0.0

        funding_frac = 0.0
        price_frac = 0.0
        for symbol in kept_long:
            leg_funding, leg_price = leg_pnl_fracs(
                snapshot, forward, symbol, is_long=True, weight=weight_long
            )
            funding_frac += leg_funding
            price_frac += leg_price
        for symbol in kept_short:
            leg_funding, leg_price = leg_pnl_fracs(
                snapshot, forward, symbol, is_long=False, weight=weight_short
            )
            funding_frac += leg_funding
            price_frac += leg_price
        funding_pnl_bps = funding_frac * 10_000.0
        price_pnl_bps = price_frac * 10_000.0
        gross_pnl_bps = funding_pnl_bps + price_pnl_bps

        kept = {(s, "long") for s in kept_long} | {(s, "short") for s in kept_short}
        entered = kept.difference(previous_kept)
        cost_bps_total = (
            sum((weight_long if side == "long" else weight_short) for _, side in entered) * cost_bps
        )
        net_pnl_bps = gross_pnl_bps - cost_bps_total

        out.append(
            IncrementalRebalanceResult(
                rebalance_time=t,
                status=RebalanceStatus.RESOLVED,
                held_long=tuple(kept_long),
                held_short=tuple(kept_short),
                swap_count=len(entered),
                funding_pnl_bps=funding_pnl_bps,
                price_pnl_bps=price_pnl_bps,
                cost_bps=cost_bps_total,
                gross_pnl_bps=gross_pnl_bps,
                net_pnl_bps=net_pnl_bps,
            )
        )
        previous_kept = kept
    return tuple(out)
