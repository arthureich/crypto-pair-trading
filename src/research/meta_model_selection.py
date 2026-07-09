"""Purged-CV model/threshold selection for the TASK-ML-001 meta-labeling filter.

Development-phase orchestration per `docs/pre_registers/TASK-ML-001.md`
(ADR-0026). Selects the XGBoost hyperparameters and the probability
threshold ON the purged/embargoed CV folds of the EXISTING window. It does
NOT compute a promotion verdict: the pre-registered promote/reject gate is
blocked until a genuinely new OOS holdout exists (~mid-Nov 2026).

Per the locked design decision (2026-07-09), each fold's filtered strategy
is evaluated only over that fold's own time span, bootstrapping the book
fresh at the fold start -- so the cost stays tractable while preserving
walk-forward semantics. Predictions come from features computed on the
FULL history (causal warm-up intact); only the backtest is restricted to
the span.

The model is dependency-injected via ``model_factory`` so this core is
unit-testable without XGBoost; the script wires the real XGBoost factory.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pandas as pd

from src.research.funding_carry import (
    HOUR_MS,
    FundingCarryConfig,
    _build_indexed_frame_and_rebalance_times,
    run_incremental_funding_carry_backtest,
    summarize_funding_carry_backtest,
)
from src.research.meta_labeling import (
    FEATURE_NAMES,
    _build_feature_frames,
    build_leg_interval_panel,
    filter_leg_interval_results,
)
from src.research.purged_cv import purged_walk_forward_splits

# model_factory(**hyperparams) -> estimator with .fit(X, y) and .predict_proba(X).
ModelFactory = Callable[..., object]


class MetaModelSelectionError(ValueError):
    """Raised when CV model-selection inputs are invalid or infeasible."""


@dataclass(frozen=True, slots=True)
class ThresholdFoldMetric:
    fold_index: int
    threshold: float
    filtered_profit_factor: float
    filtered_net_pnl_bps: float
    kept_rebalances: int
    baseline_profit_factor: float


@dataclass(frozen=True, slots=True)
class CvSelectionResult:
    best_hyperparams: dict[str, float | int]
    best_threshold: float
    mean_filtered_profit_factor: float
    n_folds: int
    n_panel_rows: int
    per_fold: tuple[ThresholdFoldMetric, ...]


def select_meta_model_via_cv(
    bars: pd.DataFrame,
    config: FundingCarryConfig,
    *,
    model_factory: ModelFactory,
    hyperparameter_grid: Sequence[dict[str, float | int]],
    thresholds: Sequence[float],
    n_splits: int,
    embargo_ms: int,
    min_kept_rebalances: int,
    progress: Callable[[int, int, dict[str, float | int]], None] | None = None,
) -> CvSelectionResult:
    """Select hyperparameters + threshold maximizing mean fold filtered PF.

    A (hyperparameter, threshold) candidate is eligible only if EVERY fold
    keeps at least ``min_kept_rebalances`` rebalances (no winning by trading
    almost nothing) and every fold's filtered profit factor is finite.
    """

    if not hyperparameter_grid:
        raise MetaModelSelectionError("hyperparameter_grid must not be empty")
    if not thresholds:
        raise MetaModelSelectionError("thresholds must not be empty")

    panel = build_leg_interval_panel(bars, config)
    if panel.empty:
        raise MetaModelSelectionError("leg-interval panel is empty (no post-warm-up rows)")

    feature_matrix = _stack_feature_matrix(_build_feature_frames(bars))
    folds = purged_walk_forward_splits(
        panel["decision_time_ms"].to_numpy(),
        panel["label_end_time_ms"].to_numpy(),
        n_splits=n_splits,
        embargo_ms=embargo_ms,
    )
    interval_ms = config.rebalance_interval_hours * HOUR_MS
    fold_spans = [_fold_span(bars, fold, interval_ms, config) for fold in folds]

    best: CvSelectionResult | None = None
    for combo_index, combo in enumerate(hyperparameter_grid, start=1):
        by_threshold: dict[float, list[ThresholdFoldMetric]] = {t: [] for t in thresholds}
        for fold, span in zip(folds, fold_spans, strict=True):
            canonical, indexed, baseline_pf = span
            train_rows = panel.iloc[fold.train_index]
            model = model_factory(**combo)
            model.fit(train_rows[list(FEATURE_NAMES)].to_numpy(), train_rows["label"].to_numpy())
            proba = model.predict_proba(feature_matrix.to_numpy())[:, 1]
            pred_lookup = {
                (int(time_ms), symbol): float(p)
                for (time_ms, symbol), p in zip(feature_matrix.index, proba, strict=True)
            }
            for threshold in thresholds:
                summary = summarize_funding_carry_backtest(
                    filter_leg_interval_results(
                        canonical, indexed, interval_ms, config, _model_gate(pred_lookup, threshold)
                    ),
                    config,
                )
                by_threshold[threshold].append(
                    ThresholdFoldMetric(
                        fold_index=fold.fold_index,
                        threshold=threshold,
                        filtered_profit_factor=summary.profit_factor,
                        filtered_net_pnl_bps=summary.net_pnl_bps,
                        kept_rebalances=summary.resolved_count,
                        baseline_profit_factor=baseline_pf,
                    )
                )

        for threshold, metrics in by_threshold.items():
            if any(m.kept_rebalances < min_kept_rebalances for m in metrics):
                continue
            if any(not math.isfinite(m.filtered_profit_factor) for m in metrics):
                continue
            mean_pf = sum(m.filtered_profit_factor for m in metrics) / len(metrics)
            if best is None or mean_pf > best.mean_filtered_profit_factor:
                best = CvSelectionResult(
                    best_hyperparams=dict(combo),
                    best_threshold=threshold,
                    mean_filtered_profit_factor=mean_pf,
                    n_folds=len(folds),
                    n_panel_rows=len(panel),
                    per_fold=tuple(metrics),
                )

        if progress is not None:
            progress(combo_index, len(hyperparameter_grid), combo)

    if best is None:
        raise MetaModelSelectionError(
            "no (hyperparameter, threshold) candidate kept >= "
            f"{min_kept_rebalances} rebalances in every fold with finite PF"
        )
    return best


def _fold_span(
    bars: pd.DataFrame,
    fold: object,
    interval_ms: int,
    config: FundingCarryConfig,
) -> tuple[tuple, pd.DataFrame, float]:
    """Run the canonical policy ONCE on the fold's span; reuse for every gate.

    Returns the canonical held-set sequence, the indexed frame, and the
    unfiltered baseline profit factor for the span. The (expensive) canonical
    run happens once per fold, not once per (hyperparameter, threshold).
    """

    start = fold.test_start_time_ms  # type: ignore[attr-defined]
    end = fold.test_end_time_ms + interval_ms  # type: ignore[attr-defined]
    span_bars = bars[(bars["open_time"] >= start) & (bars["open_time"] <= end)]
    canonical = run_incremental_funding_carry_backtest(span_bars, config)
    indexed, _, _ = _build_indexed_frame_and_rebalance_times(span_bars, config)
    baseline = summarize_funding_carry_backtest(canonical, config)
    return canonical, indexed, baseline.profit_factor


def _stack_feature_matrix(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    columns = {name: frames[name].stack(future_stack=True) for name in FEATURE_NAMES}
    matrix = pd.DataFrame(columns).dropna()
    matrix.index = matrix.index.set_names(["open_time", "symbol"])
    return matrix


def _model_gate(
    pred_lookup: dict[tuple[int, str], float], threshold: float
) -> Callable[[str, str, int], bool]:
    def gate(symbol: str, side: str, decision_time_ms: int) -> bool:  # noqa: ARG001
        probability = pred_lookup.get((decision_time_ms, symbol))
        # Undefined features (warm-up) cannot be scored -> cannot be vetoed.
        return True if probability is None else probability >= threshold

    return gate
