"""Purged + embargoed walk-forward cross-validation splits (ML harness).

Implements the validation harness pre-registered in
`docs/pre_registers/TASK-ML-001.md` (see `project_control/DECISIONS.md`
ADR-0026): the meta-labeling filter over funding-carry legs uses samples
whose labels resolve over a hold horizon, so a naive chronological split
would leak -- a training leg whose hold window overlaps the test period
has its label partly determined by data inside the test period.

This module produces ONLY index splits; it fits no model and imports no
ML library. Keeping the leakage-prevention logic in a pure, deterministic
function is deliberate: it is the one piece that must be provably correct,
so it is unit-tested in isolation from any XGBoost/threshold-selection
code that consumes it.

Design (Lopez de Prado, walk-forward variant):
  - Test folds are contiguous chronological blocks over the UNIQUE
    decision times, so all samples sharing a decision time (e.g. every
    leg of one funding-carry rebalance) always land in the same fold and
    are never split across a train/test boundary.
  - Training for fold k keeps only samples fully resolved before the
    fold begins, minus an embargo: `label_end_time < test_start - embargo`.
    Because `label_end = decision + hold_horizon`, this single condition
    enforces walk-forward (train strictly in the past), purges any
    training sample whose label window reaches into the test period, and
    adds the embargo gap on top of the hold horizon.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "PurgedCvError",
    "PurgedSplit",
    "purged_walk_forward_splits",
]


class PurgedCvError(ValueError):
    """Raised when purged CV split inputs are invalid or infeasible."""


@dataclass(frozen=True, slots=True)
class PurgedSplit:
    """One walk-forward fold: positional indices into the sample arrays."""

    fold_index: int
    test_start_time_ms: int
    test_end_time_ms: int
    train_index: np.ndarray
    test_index: np.ndarray


def _as_int64_times(values: object, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1:
        raise PurgedCvError(f"{name} must be one-dimensional")
    if array.size == 0:
        raise PurgedCvError(f"{name} must not be empty")
    if np.issubdtype(array.dtype, np.floating):
        if not np.all(np.isfinite(array)):
            raise PurgedCvError(f"{name} must be finite (no NaN/inf)")
        if not np.all(array == np.floor(array)):
            raise PurgedCvError(f"{name} must be integer-valued epoch milliseconds")
    elif not np.issubdtype(array.dtype, np.integer):
        raise PurgedCvError(f"{name} must be integer epoch milliseconds")
    return array.astype(np.int64, copy=False)


def purged_walk_forward_splits(
    decision_times_ms: object,
    label_end_times_ms: object,
    *,
    n_splits: int,
    embargo_ms: int,
) -> list[PurgedSplit]:
    """Build purged, embargoed, walk-forward CV folds.

    Args:
        decision_times_ms: epoch-ms time at which each sample's features
            are known (``t``). One entry per sample.
        label_end_times_ms: epoch-ms time at which each sample's label
            finishes resolving (``t + hold_horizon``). One entry per
            sample; must be ``>= decision_times_ms`` element-wise.
        n_splits: number of test folds. The timeline of unique decision
            times is cut into ``n_splits + 1`` contiguous blocks; the
            first block is train-only, each remaining block is one test
            fold, so every fold has some past to train on.
        embargo_ms: extra gap, beyond the hold horizon, between the end
            of a training sample's label window and the start of the test
            fold. Pre-registered as one hold horizon (8h) for TASK-ML-001.

    Returns:
        ``n_splits`` folds in chronological order. Fails closed (raises)
        rather than returning a fold with an empty train or test set.
    """

    if not isinstance(n_splits, int) or n_splits < 1:
        raise PurgedCvError("n_splits must be an integer >= 1")
    if not isinstance(embargo_ms, int) or embargo_ms < 0:
        raise PurgedCvError("embargo_ms must be an integer >= 0")

    decision = _as_int64_times(decision_times_ms, "decision_times_ms")
    label_end = _as_int64_times(label_end_times_ms, "label_end_times_ms")
    if decision.shape != label_end.shape:
        raise PurgedCvError("decision_times_ms and label_end_times_ms must have equal length")
    if np.any(label_end < decision):
        raise PurgedCvError("label_end_times_ms must be >= decision_times_ms element-wise")

    unique_times = np.unique(decision)
    n_blocks = n_splits + 1
    if unique_times.size < n_blocks:
        raise PurgedCvError(
            f"need at least {n_blocks} distinct decision times for {n_splits} folds, "
            f"got {unique_times.size}"
        )

    time_blocks = np.array_split(unique_times, n_blocks)
    embargo = np.int64(embargo_ms)

    splits: list[PurgedSplit] = []
    for fold_index, block in enumerate(time_blocks[1:], start=1):
        test_start = np.int64(block[0])
        test_end = np.int64(block[-1])
        test_mask = (decision >= test_start) & (decision <= test_end)
        train_mask = label_end < (test_start - embargo)

        test_index = np.flatnonzero(test_mask)
        train_index = np.flatnonzero(train_mask)
        if test_index.size == 0:
            raise PurgedCvError(f"fold {fold_index} has an empty test set")
        if train_index.size == 0:
            raise PurgedCvError(
                f"fold {fold_index} has an empty train set after purge/embargo; "
                "use fewer splits or a smaller embargo"
            )

        splits.append(
            PurgedSplit(
                fold_index=fold_index,
                test_start_time_ms=int(test_start),
                test_end_time_ms=int(test_end),
                train_index=train_index,
                test_index=test_index,
            )
        )

    return splits
