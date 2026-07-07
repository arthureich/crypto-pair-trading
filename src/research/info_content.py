"""Generic causal information-content diagnostic (Research Phase II infrastructure).

Implements the methodology pre-registered in
`docs/pre_registers/TASK-ALT-001.md` (see `project_control/DECISIONS.md`
ADR-0019): given a causal feature and a forward-return target, measure
whether the feature shows a stable, non-trivial Spearman rank
correlation with the target across non-overlapping chronological
sub-periods. This is a pure diagnostic, not a strategy backtest -- no
economic gate, no pass/fail on PnL/cost/drawdown. Reusable across every
Research Phase II family (F, G, ...), not re-implemented per family.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

DEFAULT_MAGNITUDE_THRESHOLD = 0.03
_MIN_OBSERVATIONS_FOR_CORRELATION = 2

__all__ = [
    "DEFAULT_MAGNITUDE_THRESHOLD",
    "InformationContentError",
    "InformationContentResult",
    "SubPeriodCorrelation",
    "evaluate_information_content",
    "spearman_rho",
]


class InformationContentError(ValueError):
    """Raised when information-content diagnostic inputs are invalid."""


@dataclass(frozen=True, slots=True)
class SubPeriodCorrelation:
    period_label: str
    start_time_ms: int
    end_time_ms: int
    n_obs: int
    spearman_rho: float


@dataclass(frozen=True, slots=True)
class InformationContentResult:
    feature_name: str
    full_sample_rho: float
    full_sample_n: int
    sub_periods: tuple[SubPeriodCorrelation, ...]
    sign_consistent: bool
    magnitude_threshold: float
    has_information: bool


def spearman_rho(feature: pd.Series, target: pd.Series) -> tuple[float, int]:
    """Spearman rank correlation between aligned, NaN-dropped series."""

    paired = pd.DataFrame({"feature": feature.to_numpy(), "target": target.to_numpy()}).dropna()
    n = len(paired)
    if n < _MIN_OBSERVATIONS_FOR_CORRELATION:
        return float("nan"), n
    rho = paired["feature"].corr(paired["target"], method="spearman")
    return float(rho) if rho is not None else float("nan"), n


def evaluate_information_content(
    panel: pd.DataFrame,
    feature_name: str,
    period_boundaries_ms: tuple[int, ...],
    period_labels: tuple[str, ...],
    magnitude_threshold: float = DEFAULT_MAGNITUDE_THRESHOLD,
) -> InformationContentResult:
    """``panel`` must have columns ``open_time``, ``feature``, ``target``.

    ``period_boundaries_ms`` has ``len(period_labels) + 1`` edges,
    fixed BEFORE running any diagnostic -- never re-partitioned after
    seeing partial results.
    """

    missing = [c for c in ("open_time", "feature", "target") if c not in panel.columns]
    if missing:
        raise InformationContentError(f"missing required columns: {missing}")
    if len(period_boundaries_ms) != len(period_labels) + 1:
        raise InformationContentError(
            "period_boundaries_ms must have exactly len(period_labels) + 1 edges"
        )
    if not math.isfinite(magnitude_threshold) or magnitude_threshold < 0:
        raise InformationContentError("magnitude_threshold must be finite and non-negative")

    full_rho, full_n = spearman_rho(panel["feature"], panel["target"])

    sub_periods: list[SubPeriodCorrelation] = []
    for i, label in enumerate(period_labels):
        start, end = period_boundaries_ms[i], period_boundaries_ms[i + 1]
        mask = (panel["open_time"] >= start) & (panel["open_time"] < end)
        rho, n = spearman_rho(panel.loc[mask, "feature"], panel.loc[mask, "target"])
        sub_periods.append(SubPeriodCorrelation(label, start, end, n, rho))

    signs = [_sign(p.spearman_rho) for p in sub_periods]
    full_sign = _sign(full_rho)
    sign_consistent = (
        full_sign is not None
        and all(s is not None for s in signs)
        and len({full_sign, *signs}) == 1
    )

    has_information = (
        not math.isnan(full_rho) and abs(full_rho) >= magnitude_threshold and sign_consistent
    )

    return InformationContentResult(
        feature_name=feature_name,
        full_sample_rho=full_rho,
        full_sample_n=full_n,
        sub_periods=tuple(sub_periods),
        sign_consistent=sign_consistent,
        magnitude_threshold=magnitude_threshold,
        has_information=has_information,
    )


def _sign(value: float) -> float | None:
    if value is None or math.isnan(value):
        return None
    return math.copysign(1.0, value)
