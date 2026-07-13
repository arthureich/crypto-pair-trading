"""TASK-TSM-004: meta-labeling filter for the vol-targeted TSM (ADR-0031, Line 4).

Meta-labeling (Lopez de Prado): the TSM is the PRIMARY model (sets each leg's
direction); a SECONDARY classifier predicts P(leg profitable over the hold) and
drops low-probability legs (survivors renormalized to unit gross by the backtest
`keep_mask`). Minimal degrees of freedom on purpose (the ML-001 mirage lesson):
ONE frozen model (GradientBoostingClassifier, fixed hyperparameters), ONE frozen
threshold (0.5), six frozen causal features, purged+embargoed walk-forward CV.

Development phase only: promotion is OOS-gated. All features are causal (known at
the rebalance decision time t); the label is the only forward-looking term and
the CV purges/embargoes the hold horizon so overlapping labels cannot leak.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from src.research.purged_cv import purged_walk_forward_splits
from src.research.tsm_trend import TsmTrendConfig

FEATURE_NAMES = ("strength", "vol", "trailing", "aggregate_strength", "btc_trailing", "xs_rank")
KEEP_THRESHOLD = 0.5  # frozen, knob-free
BTC_SYMBOL = "BTCUSDT"
_MS_PER_HOUR = 3_600_000
_GB_N_ESTIMATORS = 100
_GB_MAX_DEPTH = 3
_GB_RANDOM_STATE = 0
_MIN_FOLD_OBS = 2


class TsmMetaLabelingError(ValueError):
    """Raised when meta-labeling inputs are invalid."""


@dataclass(frozen=True, slots=True)
class FoldMetric:
    fold_index: int
    n_test: int
    kept_fraction: float
    base_mean_leg_pnl: float
    filtered_mean_leg_pnl: float
    base_precision: float  # fraction of ALL legs that were profitable
    filtered_precision: float  # fraction of KEPT legs that were profitable


@dataclass(frozen=True, slots=True)
class MetaLabelingCvResult:
    keep_mask: pd.DataFrame  # rebalance_time x symbol, 1/0 (1 for non-OOF/train legs)
    oof_start_time_ms: int  # first out-of-fold rebalance time (for fair comparison)
    fold_metrics: tuple[FoldMetric, ...]


def build_leg_panel(bars: pd.DataFrame, config: TsmTrendConfig) -> pd.DataFrame:
    """Per-(rebalance, symbol) causal features + binary profitability label."""

    required = {"symbol", "open_time", "log_price"}
    if not required.issubset(bars.columns):
        missing = sorted(required - set(bars.columns))
        raise TsmMetaLabelingError(f"missing required columns: {missing}")

    price = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    vol = price.diff().shift(1).rolling(config.vol_window_hours).std()
    trailing = price - price.shift(config.lookback_hours)

    rows = price.index[:: config.hold_hours]
    price_r, trailing_r, vol_r = price.loc[rows], trailing.loc[rows], vol.loc[rows]
    forward_r = price_r.shift(-1) - price_r

    strength = (trailing_r / vol_r).abs()
    aggregate = strength.mean(axis=1, skipna=True)
    xs_rank = strength.rank(axis=1)  # cross-sectional conviction rank per rebalance
    btc_trailing = (
        trailing_r[BTC_SYMBOL] if BTC_SYMBOL in trailing_r.columns else pd.Series(index=rows)
    )
    leg_pnl = np.sign(trailing_r) * forward_r  # >0 when the trend called the leg right

    wide = {
        "strength": strength,
        "vol": vol_r,
        "trailing": trailing_r,
        "xs_rank": xs_rank,
        "leg_pnl": leg_pnl,
    }
    long = {name: _stack(frame) for name, frame in wide.items()}
    panel = pd.concat(long, axis=1).reset_index()
    panel.columns = ["rebalance_time", "symbol", *wide.keys()]
    panel["aggregate_strength"] = panel["rebalance_time"].map(aggregate)
    panel["btc_trailing"] = panel["rebalance_time"].map(btc_trailing)

    panel = panel.dropna(subset=[*FEATURE_NAMES, "leg_pnl"]).reset_index(drop=True)
    panel = panel[panel["leg_pnl"] != 0.0]  # ties carry no label signal
    panel["label"] = (panel["leg_pnl"] > 0.0).astype(int)
    panel["decision_time_ms"] = panel["rebalance_time"].astype("int64")
    panel["label_end_ms"] = panel["decision_time_ms"] + config.hold_hours * _MS_PER_HOUR
    return panel


def _stack(frame: pd.DataFrame) -> pd.Series:
    return frame.stack(future_stack=True)


def run_meta_labeled_cv(
    panel: pd.DataFrame, config: TsmTrendConfig, n_splits: int = 5
) -> MetaLabelingCvResult:
    """Purged+embargoed walk-forward CV; out-of-fold P(profit) -> keep mask."""

    if panel.empty:
        raise TsmMetaLabelingError("empty leg panel")
    features = panel[list(FEATURE_NAMES)].to_numpy(dtype=float)
    labels = panel["label"].to_numpy(dtype=int)
    leg_pnl = panel["leg_pnl"].to_numpy(dtype=float)
    decision = panel["decision_time_ms"].to_numpy()
    label_end = panel["label_end_ms"].to_numpy()
    embargo_ms = config.hold_hours * _MS_PER_HOUR

    splits = purged_walk_forward_splits(
        decision, label_end, n_splits=n_splits, embargo_ms=embargo_ms
    )
    oof_pred = np.full(len(labels), np.nan)
    fold_metrics: list[FoldMetric] = []
    for sp in splits:
        train, test = sp.train_index, sp.test_index
        if len(test) < _MIN_FOLD_OBS or len(np.unique(labels[train])) < 2:  # noqa: PLR2004
            continue
        model = GradientBoostingClassifier(
            n_estimators=_GB_N_ESTIMATORS, max_depth=_GB_MAX_DEPTH, random_state=_GB_RANDOM_STATE
        )
        model.fit(features[train], labels[train])
        proba = model.predict_proba(features[test])[:, 1]
        oof_pred[test] = proba
        fold_metrics.append(_fold_metric(sp.fold_index, proba, labels[test], leg_pnl[test]))

    keep = oof_pred >= KEEP_THRESHOLD
    scored = ~np.isnan(oof_pred)
    oof_start = int(decision[scored].min()) if scored.any() else int(decision.max()) + 1
    mask = _keep_mask(panel, keep, scored, oof_start)
    return MetaLabelingCvResult(mask, oof_start, tuple(fold_metrics))


def _fold_metric(
    fold_index: int, proba: np.ndarray, labels: np.ndarray, leg_pnl: np.ndarray
) -> FoldMetric:
    keep = proba >= KEEP_THRESHOLD
    n_keep = int(keep.sum())
    return FoldMetric(
        fold_index=fold_index,
        n_test=int(len(labels)),
        kept_fraction=float(keep.mean()),
        base_mean_leg_pnl=float(leg_pnl.mean()),
        filtered_mean_leg_pnl=float(leg_pnl[keep].mean()) if n_keep else float("nan"),
        base_precision=float(labels.mean()),
        filtered_precision=float(labels[keep].mean()) if n_keep else float("nan"),
    )


def _keep_mask(
    panel: pd.DataFrame, keep: np.ndarray, scored: np.ndarray, oof_start: int
) -> pd.DataFrame:
    """Wide (rebalance_time x symbol) 1/0 mask; train-only (unscored) legs -> 1.

    Legs before the first out-of-fold rebalance have no prediction and are left
    untouched (mask 1) so the base and filtered books coincide there; the fair
    comparison restricts to rebalance_time >= oof_start.
    """

    keep_val = np.where(scored, keep.astype(float), 1.0)
    wide = (
        pd.DataFrame(
            {
                "rebalance_time": panel["rebalance_time"],
                "symbol": panel["symbol"],
                "keep": keep_val,
            }
        )
        .pivot(index="rebalance_time", columns="symbol", values="keep")
        .sort_index()
    )
    return wide
