"""Sprint 8 research-only contracts and cost-aware backtest helpers.

This module is intentionally kept in the Research plane. It produces offline
SignalIntent-like records and simulated backtest fills, but it never imports or
calls the live execution, ledger, recovery, or model planes.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .kalman import KalmanFilterConfig, fit_kalman_filter
from .ou import estimate_ou, rolling_zscore

HOUR_MS = 60 * 60 * 1000
DEFAULT_ENTRY_ZSCORE = 2.0
DEFAULT_EXIT_ZSCORE = 0.5
DEFAULT_ZSCORE_WINDOW = 168
DEFAULT_OU_WINDOW = 168
DEFAULT_MAX_HALF_LIFE_HOURS = 240.0
DEFAULT_TARGET_NOTIONAL = 1_000.0
EXPECTED_APPROVED_PAIR_COUNT = 31
EXPECTED_BLOCKED_PAIR_COUNT = 10
PAIR_SYMBOL_COUNT = 2


class Sprint8ContractError(ValueError):
    """Raised when Sprint 8 inputs violate the approved evidence contract."""


class WalkForwardSplitError(ValueError):
    """Raised when walk-forward split inputs are invalid."""


class OfflineSignalIntentError(ValueError):
    """Raised when an offline SignalIntent cannot be produced safely."""


@dataclass(frozen=True, slots=True)
class Sprint8UniverseContract:
    """Machine-readable universe approved for Sprint 8 cost-aware backtests."""

    sprint: str
    evidence_scope: str
    approved_pairs: tuple[str, ...]
    blocked_reasons: Mapping[str, str]
    artifacts: Mapping[str, str]
    cost_gate: Mapping[str, Any]
    rules: tuple[str, ...]

    @property
    def blocked_pairs(self) -> tuple[str, ...]:
        """Pairs explicitly rejected by the evidence gate."""

        return tuple(self.blocked_reasons)


@dataclass(frozen=True, slots=True)
class WalkForwardSplitConfig:
    """Bar-count configuration for causal walk-forward folds."""

    train_bars: int
    test_bars: int
    step_bars: int

    def __post_init__(self) -> None:
        _positive_int("train_bars", self.train_bars)
        _positive_int("test_bars", self.test_bars)
        _positive_int("step_bars", self.step_bars)


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    """One causal walk-forward fold."""

    fold_index: int
    train_start_time: int
    train_end_time: int
    test_start_time: int
    test_end_time: int
    train_rows: int
    test_rows: int


@dataclass(frozen=True, slots=True)
class OfflineSignalIntent:
    """Research-plane SignalIntent shape for offline backtests."""

    signal_id: str
    pair: str
    symbol_a: str
    symbol_b: str
    side_a: str
    side_b: str
    target_notional: float
    zscore: float
    beta: float
    half_life_hours: float
    expected_edge_bps: float
    created_at: int
    expires_at: int
    barrier_policy_id: str
    source: str = "SPRINT8_RESEARCH_OFFLINE"

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""

        return {
            "signal_id": self.signal_id,
            "pair": self.pair,
            "symbol_a": self.symbol_a,
            "symbol_b": self.symbol_b,
            "side_a": self.side_a,
            "side_b": self.side_b,
            "target_notional": self.target_notional,
            "zscore": self.zscore,
            "beta": self.beta,
            "half_life_hours": self.half_life_hours,
            "expected_edge_bps": self.expected_edge_bps,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "barrier_policy_id": self.barrier_policy_id,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class BacktestTradeResult:
    """One simulated cost-aware Sprint 8 trade result."""

    signal_id: str
    pair: str
    gross_pnl_bps: float
    cost_bps: float
    net_pnl_bps: float
    target_notional: float
    net_pnl_quote: float


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    """Aggregated simulated backtest metrics."""

    trade_count: int
    gross_pnl_bps: float
    cost_bps: float
    net_pnl_bps: float
    hit_rate: float
    max_drawdown_bps: float
    turnover_notional: float
    net_pnl_quote: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Simulated backtest trades and metrics."""

    trades: tuple[BacktestTradeResult, ...]
    metrics: BacktestMetrics


def load_sprint8_universe_contract(path: str | Path | None = None) -> Sprint8UniverseContract:
    """Load the Sprint 8 cost-gated universe contract."""

    contract_path = Path(path) if path is not None else _default_contract_path()
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    approved_pairs = tuple(normalize_pair_id(pair) for pair in payload.get("approved_pairs", []))
    blocked_reasons = {
        normalize_pair_id(item["pair"]): str(item["reason"])
        for item in payload.get("blocked_pairs", [])
    }
    contract = Sprint8UniverseContract(
        sprint=str(payload["sprint"]),
        evidence_scope=str(payload["evidence_scope"]),
        approved_pairs=approved_pairs,
        blocked_reasons=blocked_reasons,
        artifacts=dict(payload.get("artifacts", {})),
        cost_gate=dict(payload.get("cost_gate", {})),
        rules=tuple(str(rule) for rule in payload.get("rules", [])),
    )
    validate_sprint8_universe_contract(contract)
    return contract


def validate_sprint8_universe_contract(contract: Sprint8UniverseContract) -> None:
    """Validate invariant counts and fail-closed ADA policy."""

    if contract.evidence_scope != "2023-06":
        raise Sprint8ContractError("Sprint 8 evidence_scope must be exactly 2023-06")
    if len(contract.approved_pairs) != EXPECTED_APPROVED_PAIR_COUNT:
        raise Sprint8ContractError("Sprint 8 contract must contain exactly 31 approved pairs")
    if len(contract.blocked_pairs) != EXPECTED_BLOCKED_PAIR_COUNT:
        raise Sprint8ContractError("Sprint 8 contract must contain exactly 10 blocked pairs")
    approved_set = set(contract.approved_pairs)
    if len(approved_set) != len(contract.approved_pairs):
        raise Sprint8ContractError("Sprint 8 approved pairs must be unique")
    if any("ADAUSDT" in pair_symbols(pair) for pair in contract.approved_pairs):
        raise Sprint8ContractError("ADAUSDT must not appear in approved Sprint 8 pairs")
    if not all("ADAUSDT" in pair_symbols(pair) for pair in contract.blocked_pairs):
        raise Sprint8ContractError("Sprint 8 blocked pairs must document ADAUSDT failures")
    if approved_set.intersection(contract.blocked_pairs):
        raise Sprint8ContractError("Sprint 8 approved and blocked pairs overlap")
    if not contract.cost_gate.get("cost_gated_pass"):
        raise Sprint8ContractError("Sprint 8 contract requires cost_gated_pass=true")
    required_artifacts = {
        "execution_cost_gate_json",
        "manifest_json",
        "source_review_json",
        "hourly_cost_csv",
        "bars_csv",
    }
    missing = sorted(required_artifacts.difference(contract.artifacts))
    if missing:
        raise Sprint8ContractError(f"Sprint 8 contract missing artifacts: {missing}")


def normalize_pair_id(pair: str) -> str:
    """Normalize pair IDs to SYMBOLA/SYMBOLB and reject malformed inputs."""

    pair_id = str(pair).strip().upper()
    parts = pair_id.split("/")
    if len(parts) != PAIR_SYMBOL_COUNT or not all(parts):
        raise Sprint8ContractError(f"invalid pair id: {pair!r}")
    return f"{parts[0]}/{parts[1]}"


def pair_symbols(pair: str) -> tuple[str, str]:
    """Return normalized symbols for a pair."""

    pair_id = normalize_pair_id(pair)
    symbol_a, symbol_b = pair_id.split("/", maxsplit=1)
    return symbol_a, symbol_b


def assert_pair_cost_gated(
    pair: str,
    contract: Sprint8UniverseContract | None = None,
) -> str:
    """Return normalized pair if approved, otherwise raise fail-closed."""

    active_contract = contract or load_sprint8_universe_contract()
    pair_id = normalize_pair_id(pair)
    if pair_id in active_contract.approved_pairs:
        return pair_id
    if pair_id in active_contract.blocked_reasons:
        reason = active_contract.blocked_reasons[pair_id]
        raise Sprint8ContractError(f"{pair_id} is blocked by Sprint 8 cost evidence: {reason}")
    raise Sprint8ContractError(f"{pair_id} is outside the Sprint 8 cost-gated universe")


def build_walk_forward_splits(
    bars_or_times: pd.DataFrame | Iterable[int],
    config: WalkForwardSplitConfig,
    *,
    time_column: str = "open_time",
) -> tuple[WalkForwardFold, ...]:
    """Build causal walk-forward folds with train_end strictly before test_start."""

    times = _sorted_unique_times(bars_or_times, time_column=time_column)
    required = config.train_bars + config.test_bars
    if len(times) < required:
        raise WalkForwardSplitError(
            f"need at least {required} unique bars, got {len(times)}"
        )

    folds: list[WalkForwardFold] = []
    fold_index = 0
    start = 0
    while start + config.train_bars + config.test_bars <= len(times):
        train = times[start : start + config.train_bars]
        test = times[start + config.train_bars : start + config.train_bars + config.test_bars]
        train_end = int(train[-1])
        test_start = int(test[0])
        if train_end >= test_start:
            raise WalkForwardSplitError("walk-forward fold overlaps train and test windows")
        folds.append(
            WalkForwardFold(
                fold_index=fold_index,
                train_start_time=int(train[0]),
                train_end_time=train_end,
                test_start_time=test_start,
                test_end_time=int(test[-1]),
                train_rows=len(train),
                test_rows=len(test),
            )
        )
        fold_index += 1
        start += config.step_bars
    return tuple(folds)


def generate_offline_signal_intent(
    *,
    pair: str,
    zscore: float,
    beta: float,
    half_life_hours: float,
    created_at: int,
    contract: Sprint8UniverseContract | None = None,
    target_notional: float = DEFAULT_TARGET_NOTIONAL,
    entry_zscore: float = DEFAULT_ENTRY_ZSCORE,
    expires_after_ms: int = HOUR_MS,
    barrier_policy_id: str = "SPRINT8_OFFLINE_BARRIER",
) -> OfflineSignalIntent | None:
    """Create a research-only SignalIntent when z-score crosses entry threshold."""

    pair_id = assert_pair_cost_gated(pair, contract)
    _finite_float("zscore", zscore)
    _finite_float("beta", beta)
    _finite_float("half_life_hours", half_life_hours)
    _positive_float("target_notional", target_notional)
    _positive_float("entry_zscore", entry_zscore)
    _positive_int("expires_after_ms", expires_after_ms)

    if abs(zscore) < entry_zscore:
        return None

    symbol_a, symbol_b = pair_symbols(pair_id)
    if zscore > 0.0:
        side_a, side_b, direction = "SELL", "BUY", "SHORT_SPREAD"
    else:
        side_a, side_b, direction = "BUY", "SELL", "LONG_SPREAD"
    expected_edge_bps = max(0.0, abs(float(zscore)) - entry_zscore) * 10.0
    return OfflineSignalIntent(
        signal_id=_signal_id(pair_id, created_at, direction),
        pair=pair_id,
        symbol_a=symbol_a,
        symbol_b=symbol_b,
        side_a=side_a,
        side_b=side_b,
        target_notional=float(target_notional),
        zscore=float(zscore),
        beta=float(beta),
        half_life_hours=float(half_life_hours),
        expected_edge_bps=expected_edge_bps,
        created_at=int(created_at),
        expires_at=int(created_at + expires_after_ms),
        barrier_policy_id=barrier_policy_id,
    )


def generate_pair_signal_intents(
    bars: pd.DataFrame,
    pair: str,
    *,
    contract: Sprint8UniverseContract | None = None,
    zscore_window: int = DEFAULT_ZSCORE_WINDOW,
    entry_zscore: float = DEFAULT_ENTRY_ZSCORE,
    max_half_life_hours: float = DEFAULT_MAX_HALF_LIFE_HOURS,
    target_notional: float = DEFAULT_TARGET_NOTIONAL,
    ou_window: int = DEFAULT_OU_WINDOW,
) -> tuple[OfflineSignalIntent, ...]:
    """Generate offline SignalIntent records from aligned pair bars.

    The mean-reversion/half-life gate is recomputed on a trailing causal
    window ending at each candidate bar, not once over the full series --
    fitting OU once on the whole sample would let a pair's later regime
    "approve" signals earlier in the same window before that regime existed.
    """

    pair_id = assert_pair_cost_gated(pair, contract)
    pair_bars = _pair_frame(bars, pair_id)
    if len(pair_bars) < max(zscore_window, ou_window):
        return ()

    kalman = fit_kalman_filter(
        y=pair_bars["log_price_a"].to_numpy(dtype=float),
        x=pair_bars["log_price_b"].to_numpy(dtype=float),
        config=KalmanFilterConfig(initial_beta=1.0),
    )
    spread = pd.Series(kalman.spread, index=pair_bars.index, name="spread")
    zscores = rolling_zscore(spread, window=zscore_window, min_periods=zscore_window)

    intents = []
    for index, zscore in zscores.dropna().items():
        position = int(index)
        if kalman.unstable_points[position]:
            continue
        beta = float(kalman.beta[position])
        if beta <= 0.0:
            continue
        window_start = position - ou_window + 1
        if window_start < 0:
            continue
        trailing_spread = spread.iloc[window_start : position + 1]
        try:
            ou = estimate_ou(trailing_spread, min_observations=ou_window)
        except ValueError:
            continue
        if not ou.mean_reverting or ou.half_life > max_half_life_hours:
            continue
        intent = generate_offline_signal_intent(
            pair=pair_id,
            zscore=float(zscore),
            beta=beta,
            half_life_hours=float(ou.half_life),
            created_at=int(pair_bars.loc[index, "open_time"]),
            contract=contract,
            target_notional=target_notional,
            entry_zscore=entry_zscore,
        )
        if intent is not None:
            intents.append(intent)
    return tuple(intents)


def run_cost_aware_backtest(
    intents: Sequence[OfflineSignalIntent],
    gross_edge_bps_by_signal_id: Mapping[str, float],
    symbol_cost_bps: Mapping[str, float],
    *,
    contract: Sprint8UniverseContract | None = None,
) -> BacktestResult:
    """Apply explicit execution costs to simulated gross edge per signal."""

    active_contract = contract or load_sprint8_universe_contract()
    trades = []
    for intent in intents:
        pair_id = assert_pair_cost_gated(intent.pair, active_contract)
        if intent.signal_id not in gross_edge_bps_by_signal_id:
            raise OfflineSignalIntentError(f"missing gross edge for signal {intent.signal_id}")
        gross_pnl_bps = _finite_float(
            f"gross_edge_bps_by_signal_id[{intent.signal_id}]",
            gross_edge_bps_by_signal_id[intent.signal_id],
        )
        cost_bps = pair_execution_cost_bps(pair_id, symbol_cost_bps)
        net_pnl_bps = gross_pnl_bps - cost_bps
        net_pnl_quote = intent.target_notional * net_pnl_bps / 10_000.0
        trades.append(
            BacktestTradeResult(
                signal_id=intent.signal_id,
                pair=pair_id,
                gross_pnl_bps=gross_pnl_bps,
                cost_bps=cost_bps,
                net_pnl_bps=net_pnl_bps,
                target_notional=float(intent.target_notional),
                net_pnl_quote=net_pnl_quote,
            )
        )
    return BacktestResult(trades=tuple(trades), metrics=summarize_backtest_metrics(trades))


def pair_execution_cost_bps(pair: str, symbol_cost_bps: Mapping[str, float]) -> float:
    """Return summed per-leg execution cost in bps for a pair."""

    symbol_a, symbol_b = pair_symbols(pair)
    missing = [symbol for symbol in (symbol_a, symbol_b) if symbol not in symbol_cost_bps]
    if missing:
        raise OfflineSignalIntentError(f"missing execution cost for symbols: {missing}")
    return _finite_float(symbol_a, symbol_cost_bps[symbol_a]) + _finite_float(
        symbol_b,
        symbol_cost_bps[symbol_b],
    )


def summarize_backtest_metrics(trades: Sequence[BacktestTradeResult]) -> BacktestMetrics:
    """Summarize simulated trades into cost-aware Sprint 8 metrics."""

    if not trades:
        return BacktestMetrics(
            trade_count=0,
            gross_pnl_bps=0.0,
            cost_bps=0.0,
            net_pnl_bps=0.0,
            hit_rate=math.nan,
            max_drawdown_bps=0.0,
            turnover_notional=0.0,
            net_pnl_quote=0.0,
        )
    gross = float(sum(trade.gross_pnl_bps for trade in trades))
    cost = float(sum(trade.cost_bps for trade in trades))
    net = float(sum(trade.net_pnl_bps for trade in trades))
    hit_rate = sum(trade.net_pnl_bps > 0.0 for trade in trades) / len(trades)
    turnover = float(sum(trade.target_notional for trade in trades))
    net_quote = float(sum(trade.net_pnl_quote for trade in trades))
    return BacktestMetrics(
        trade_count=len(trades),
        gross_pnl_bps=gross,
        cost_bps=cost,
        net_pnl_bps=net,
        hit_rate=hit_rate,
        max_drawdown_bps=_max_drawdown_bps([trade.net_pnl_bps for trade in trades]),
        turnover_notional=turnover,
        net_pnl_quote=net_quote,
    )


def _default_contract_path() -> Path:
    return Path(__file__).resolve().parents[2] / "project_control" / "SPRINT8_UNIVERSE.json"


def _sorted_unique_times(
    bars_or_times: pd.DataFrame | Iterable[int],
    *,
    time_column: str,
) -> tuple[int, ...]:
    if isinstance(bars_or_times, pd.DataFrame):
        if time_column not in bars_or_times.columns:
            raise WalkForwardSplitError(f"missing time column: {time_column}")
        raw_times = bars_or_times[time_column]
    else:
        raw_times = pd.Series(list(bars_or_times), dtype="float64")
    numeric = pd.to_numeric(raw_times, errors="coerce").replace([np.inf, -np.inf], np.nan)
    numeric = numeric.dropna().astype("int64")
    times = tuple(int(value) for value in sorted(numeric.unique()))
    if not times:
        raise WalkForwardSplitError("walk-forward split requires at least one finite time")
    return times


def _pair_frame(bars: pd.DataFrame, pair: str) -> pd.DataFrame:
    required = {"symbol", "open_time", "log_price"}
    missing = required.difference(bars.columns)
    if missing:
        raise OfflineSignalIntentError(f"bars missing required columns: {sorted(missing)}")
    symbol_a, symbol_b = pair_symbols(pair)
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
    joined = left.merge(right, on="open_time", how="inner", sort=True).dropna()
    return joined.reset_index(drop=True)


def _signal_id(pair: str, created_at: int, direction: str) -> str:
    return f"S8-{pair.replace('/', '-')}-{int(created_at)}-{direction}"


def _max_drawdown_bps(net_pnl_bps: Sequence[float]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in net_pnl_bps:
        cumulative += float(value)
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
    return float(max_drawdown)


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _positive_float(name: str, value: float) -> float:
    numeric = _finite_float(name, value)
    if numeric <= 0.0:
        raise ValueError(f"{name} must be positive")
    return numeric


def _finite_float(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    return numeric
