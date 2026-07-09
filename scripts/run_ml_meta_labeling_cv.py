#!/usr/bin/env python3
"""TASK-ML-001 development run: XGBoost meta-labeling CV model/threshold selection.

Per `docs/pre_registers/TASK-ML-001.md` and `project_control/DECISIONS.md`
ADR-0026. Selects the XGBoost hyperparameters and probability threshold on
the purged/embargoed CV folds of the EXISTING window (2023-06/2026-05).

IMPORTANT: this produces NO promotion verdict. The pre-registered
PROMOTE/NAO_PROMOVE gate is BLOCKED until a genuinely new OOS holdout
(>=500 resolved rebalances after 2026-05-31, ~mid-Nov 2026) exists. This
run only develops/selects the model+threshold; it cannot promote.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.funding_carry import FundingCarryConfig  # noqa: E402
from src.research.meta_model_selection import (  # noqa: E402
    CvSelectionResult,
    select_meta_model_via_cv,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/ml_meta_labeling_cv_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/ml_meta_labeling_cv_selection.md"

HOUR_MS = 3_600_000
EMBARGO_MS = 8 * HOUR_MS  # one hold horizon, per the pre-registration
N_SPLITS = 5
MIN_KEPT_REBALANCES = 100  # CV-fold floor (distinct from the final gate's 500 on new OOS)
PRIMARY_K = 5
SEED = 20260709

# Pre-registered 24-cell grid (TASK-ML-001), frozen before any fit.
GRID_MAX_DEPTH = (2, 3, 4)
GRID_N_ESTIMATORS = (100, 300)
GRID_LEARNING_RATE = (0.03, 0.10)
GRID_MIN_CHILD_WEIGHT = (5, 20)
# Threshold candidates swept on the CV folds (selection only, not a gate).
THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)


class _BalancedXGB:
    """XGBoost wrapper that sets scale_pos_weight from each fold's own train y."""

    def __init__(self, **hyperparams: float | int) -> None:
        self.hyperparams = hyperparams
        self.model: XGBClassifier | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> _BalancedXGB:
        positives = float(np.sum(y == 1))
        negatives = float(np.sum(y == 0))
        scale_pos_weight = (negatives / positives) if positives > 0 else 1.0
        self.model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=SEED,
            n_jobs=4,
            scale_pos_weight=scale_pos_weight,
            **self.hyperparams,
        )
        self.model.fit(x, y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        assert self.model is not None
        return self.model.predict_proba(x)


def _factory(**hyperparams: float | int) -> _BalancedXGB:
    return _BalancedXGB(**hyperparams)


def _grid() -> list[dict[str, float | int]]:
    return [
        {
            "max_depth": max_depth,
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "min_child_weight": min_child_weight,
        }
        for max_depth, n_estimators, learning_rate, min_child_weight in itertools.product(
            GRID_MAX_DEPTH, GRID_N_ESTIMATORS, GRID_LEARNING_RATE, GRID_MIN_CHILD_WEIGHT
        )
    ]


def main() -> int:
    bars = pd.read_csv(
        BARS_CSV, usecols=["symbol", "open_time", "log_price", "quote_volume", "funding_rate_asof"]
    )
    config = FundingCarryConfig(k=PRIMARY_K)

    def _progress(done: int, total: int, combo: dict[str, float | int]) -> None:
        print(f"[{done}/{total}] finished combo {combo}", file=sys.stderr, flush=True)

    print(
        f"Grid: {len(_grid())} combos x {N_SPLITS} folds x {len(THRESHOLDS)} thresholds. "
        "Building panel + feature matrix (one pass), then CV...",
        file=sys.stderr,
        flush=True,
    )
    result = select_meta_model_via_cv(
        bars,
        config,
        model_factory=_factory,
        hyperparameter_grid=_grid(),
        thresholds=THRESHOLDS,
        n_splits=N_SPLITS,
        embargo_ms=EMBARGO_MS,
        min_kept_rebalances=MIN_KEPT_REBALANCES,
        progress=_progress,
    )

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "task": "TASK-ML-001",
        "phase": "DEVELOPMENT: CV selection only; NO verdict (gate blocked until new OOS)",
        "primary_k": PRIMARY_K,
        "n_splits": N_SPLITS,
        "embargo_ms": EMBARGO_MS,
        "min_kept_rebalances": MIN_KEPT_REBALANCES,
        "thresholds": list(THRESHOLDS),
        "grid_size": len(_grid()),
        "seed": SEED,
        "result": asdict(result),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload, result)

    print(
        f"Best hyperparams: {result.best_hyperparams}, threshold={result.best_threshold}, "
        f"mean fold filtered PF={result.mean_filtered_profit_factor:.4f} "
        f"(n_panel_rows={result.n_panel_rows})",
        file=sys.stderr,
    )
    print("NO PROMOTION VERDICT -- gate blocked until new OOS (ADR-0026).", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(payload: dict, result: CvSelectionResult) -> None:
    lines = [
        "# TASK-ML-001 -- Meta-Labeling CV Model/Threshold Selection (development)",
        "",
        "Per `docs/pre_registers/TASK-ML-001.md` / ADR-0026. **This is a "
        "development run: no promotion verdict.** The pre-registered "
        "PROMOTE/NAO_PROMOVE gate stays BLOCKED until a genuinely new OOS "
        "holdout (>=500 resolved rebalances after 2026-05-31) exists.",
        "",
        f"Window: existing (bars `{payload['bars_csv']}`). Primary signal: "
        f"funding carry incremental K={payload['primary_k']} (unaltered). "
        f"Purged/embargoed CV: {payload['n_splits']} folds, embargo "
        f"{payload['embargo_ms'] // HOUR_MS}h. Grid: {payload['grid_size']} cells. "
        f"Threshold candidates: {payload['thresholds']}.",
        "",
        "## Selected (on CV folds only)",
        "",
        f"- Hyperparameters: `{result.best_hyperparams}`",
        f"- Threshold: {result.best_threshold}",
        f"- Mean fold filtered profit factor: {result.mean_filtered_profit_factor:.4f}",
        f"- Panel rows (entries): {result.n_panel_rows}",
        "",
        "## Per-fold detail (winning candidate)",
        "",
        "| Fold | Filtered PF | Filtered net PnL (bps) | Kept rebalances | Baseline PF |",
        "|---:|---:|---:|---:|---:|",
    ]
    for metric in result.per_fold:
        lines.append(
            f"| {metric.fold_index} | {metric.filtered_profit_factor:.4f} | "
            f"{metric.filtered_net_pnl_bps:.2f} | {metric.kept_rebalances} | "
            f"{metric.baseline_profit_factor:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "The mean fold filtered PF above is an in-development CV estimate on "
            "the SAME window the K=5 near-miss (1.0904) was observed on. It is "
            "NOT evidence of edge and does NOT clear any gate. The only "
            "admissible verdict comes from the untouched new-OOS holdout, per "
            "ADR-0026's four-condition gate (filtered PF >= 1.10; net PnL > 0; "
            ">= 500 kept rebalances; filtered PF exceeds the unfiltered K=5 "
            "baseline by >= +0.02).",
            "",
        ]
    )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool | str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
