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
# Below this, the control is (rank-)collinear with feature/target and the
# partial correlation is undefined (absorbs the floating-point residual).
_COLLINEAR_RESIDUAL_EPS = 1e-12

__all__ = [
    "DEFAULT_MAGNITUDE_THRESHOLD",
    "InformationContentError",
    "InformationContentResult",
    "SubPeriodCorrelation",
    "evaluate_information_content",
    "partial_spearman_rho",
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


def partial_spearman_rho(
    feature: pd.Series, target: pd.Series, control: pd.Series
) -> tuple[float, int]:
    """First-order partial Spearman correlation of feature vs target, netting out control.

    Answers "does the feature relate to the target BEYOND what the control
    already explains?" via the standard partial-correlation formula on
    Spearman coefficients:

        rho(f,t|c) = (r_ft - r_fc * r_tc) / sqrt((1 - r_fc^2)(1 - r_tc^2))

    All three series are aligned and NaN-dropped jointly. Returns NaN when
    there are too few joint observations, or when the control is (rank-)
    perfectly collinear with the feature or target (denominator zero) --
    i.e. no independent variation is measurable.
    """

    joint = pd.DataFrame(
        {
            "feature": feature.to_numpy(),
            "target": target.to_numpy(),
            "control": control.to_numpy(),
        }
    ).dropna()
    n = len(joint)
    if n < _MIN_OBSERVATIONS_FOR_CORRELATION:
        return float("nan"), n
    ranks = joint.rank()
    r_ft = ranks["feature"].corr(ranks["target"])
    r_fc = ranks["feature"].corr(ranks["control"])
    r_tc = ranks["target"].corr(ranks["control"])
    if any(value is None or not math.isfinite(value) for value in (r_ft, r_fc, r_tc)):
        return float("nan"), n
    # Near-collinear control (rank corr with feature or target ~= +/-1) leaves
    # no independent variation -> partial is undefined. Tolerance absorbs the
    # floating-point residual on exactly-collinear ranks.
    residual = (1.0 - r_fc**2) * (1.0 - r_tc**2)
    if residual <= _COLLINEAR_RESIDUAL_EPS:
        return float("nan"), n
    return float((r_ft - r_fc * r_tc) / math.sqrt(residual)), n


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
