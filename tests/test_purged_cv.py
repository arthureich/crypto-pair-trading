"""Tests for src/research/purged_cv.py (TASK-ML-001 validation harness).

The module treats decision/label times as opaque int64 values, so these
tests use small integer time units for readability; scale is irrelevant.
The central test is `test_purge_excludes_a_past_sample_whose_label_reaches_into_the_test_fold`,
which proves the harness prevents the overlapping-label leakage that a
naive "train on everything in the past" split would allow.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.research.purged_cv import (
    PurgedCvError,
    purged_walk_forward_splits,
)


def test_produces_requested_number_of_chronological_non_overlapping_folds() -> None:
    # 12 distinct decision times, hold horizon = 1 step, embargo = 1 step.
    decision = np.arange(12, dtype=np.int64)
    label_end = decision + 1
    splits = purged_walk_forward_splits(decision, label_end, n_splits=3, embargo_ms=1)

    assert [s.fold_index for s in splits] == [1, 2, 3]
    # Blocks are [0,1,2] (train-only), [3,4,5], [6,7,8], [9,10,11].
    assert [(s.test_start_time_ms, s.test_end_time_ms) for s in splits] == [(3, 5), (6, 8), (9, 11)]
    # Test spans are strictly increasing and non-overlapping.
    for earlier, later in zip(splits, splits[1:], strict=False):
        assert earlier.test_end_time_ms < later.test_start_time_ms


def test_train_is_strictly_in_the_past_of_each_test_fold() -> None:
    decision = np.arange(12, dtype=np.int64)
    label_end = decision + 1
    splits = purged_walk_forward_splits(decision, label_end, n_splits=3, embargo_ms=1)

    for split in splits:
        # Every training sample must fully resolve before the fold begins.
        assert np.all(label_end[split.train_index] < split.test_start_time_ms)
        # No training decision time falls inside the test span.
        assert np.all(decision[split.train_index] < split.test_start_time_ms)


def test_train_index_membership_is_exactly_the_purged_past() -> None:
    decision = np.arange(12, dtype=np.int64)
    label_end = decision + 1
    splits = purged_walk_forward_splits(decision, label_end, n_splits=3, embargo_ms=1)

    # fold 1: test_start=3, threshold = 3 - 1 = 2, so label_end < 2 -> only sample 0.
    assert splits[0].train_index.tolist() == [0]
    assert splits[0].test_index.tolist() == [3, 4, 5]
    # fold 2: test_start=6, threshold=5 -> label_end(i)=i+1 < 5 -> i in 0..3.
    assert splits[1].train_index.tolist() == [0, 1, 2, 3]
    # fold 3: test_start=9, threshold=8 -> i+1 < 8 -> i in 0..6.
    assert splits[2].train_index.tolist() == [0, 1, 2, 3, 4, 5, 6]


def test_all_samples_sharing_a_decision_time_stay_in_one_fold() -> None:
    # Two legs per decision time (duplicated t), as in one funding-carry rebalance.
    base = np.repeat(np.arange(6, dtype=np.int64), 2)
    label_end = base + 1
    splits = purged_walk_forward_splits(base, label_end, n_splits=2, embargo_ms=0)

    for split in splits:
        train_times = set(base[split.train_index].tolist())
        test_times = set(base[split.test_index].tolist())
        # A decision time is never partly in train and partly in test.
        assert train_times.isdisjoint(test_times)


def test_purge_excludes_a_past_sample_whose_label_reaches_into_the_test_fold() -> None:
    # Isolate the purge from the embargo (embargo=0). Test fold covers times {2,3}.
    # decision  label_end  meaning
    #    0          1       short hold, resolves before the fold  -> TRAIN
    #    0          2       same t, longer hold that TOUCHES test_start -> PURGED
    #    1          5       hold spans deep into the test fold          -> PURGED
    #    2          3       in the test fold                            -> TEST
    #    3          4       in the test fold                            -> TEST
    decision = np.array([0, 0, 1, 2, 3], dtype=np.int64)
    label_end = np.array([1, 2, 5, 3, 4], dtype=np.int64)
    (split,) = purged_walk_forward_splits(decision, label_end, n_splits=1, embargo_ms=0)

    assert split.test_start_time_ms == 2
    # Sample 1 and 2 sit in the past by decision time (0 and 1 < 2), so a naive
    # "train on the past" rule would include them -- the purge must not.
    assert 0 in split.train_index.tolist()
    assert 1 not in split.train_index.tolist()
    assert 2 not in split.train_index.tolist()
    # Test-fold samples never leak into train.
    assert split.test_index.tolist() == [3, 4]
    assert split.train_index.tolist() == [0]


def test_embargo_removes_a_sample_the_pure_purge_would_have_kept() -> None:
    # 4 distinct times [0,1,2,3] split into 2 blocks -> train-only {0,1},
    # test {2,3}, test_start=2. Samples with label_end==1 are kept by the pure
    # purge (1 < 2) but removed by an embargo of 1 (1 is not < 2 - 1).
    decision = np.array([0, 0, 1, 2, 3], dtype=np.int64)
    label_end = np.array([0, 1, 1, 3, 4], dtype=np.int64)

    (no_embargo,) = purged_walk_forward_splits(decision, label_end, n_splits=1, embargo_ms=0)
    (with_embargo,) = purged_walk_forward_splits(decision, label_end, n_splits=1, embargo_ms=1)

    assert no_embargo.train_index.tolist() == [0, 1, 2]
    assert with_embargo.train_index.tolist() == [0]


def test_fails_closed_on_mismatched_lengths() -> None:
    with pytest.raises(PurgedCvError, match="equal length"):
        purged_walk_forward_splits(
            np.array([0, 1, 2], dtype=np.int64),
            np.array([1, 2], dtype=np.int64),
            n_splits=1,
            embargo_ms=0,
        )


def test_fails_closed_when_label_ends_before_decision() -> None:
    with pytest.raises(PurgedCvError, match=">= decision"):
        purged_walk_forward_splits(
            np.array([0, 5, 2], dtype=np.int64),
            np.array([1, 4, 3], dtype=np.int64),  # 4 < 5
            n_splits=1,
            embargo_ms=0,
        )


def test_fails_closed_on_non_finite_times() -> None:
    with pytest.raises(PurgedCvError, match="finite"):
        purged_walk_forward_splits(
            np.array([0.0, 1.0, np.nan], dtype=float),
            np.array([1.0, 2.0, 3.0], dtype=float),
            n_splits=1,
            embargo_ms=0,
        )


def test_fails_closed_on_non_integer_float_times() -> None:
    with pytest.raises(PurgedCvError, match="integer-valued"):
        purged_walk_forward_splits(
            np.array([0.0, 1.5, 2.0], dtype=float),
            np.array([1.0, 2.0, 3.0], dtype=float),
            n_splits=1,
            embargo_ms=0,
        )


def test_fails_closed_when_too_few_distinct_times_for_requested_splits() -> None:
    # 3 distinct times cannot form 3 folds (needs n_splits + 1 = 4 blocks).
    with pytest.raises(PurgedCvError, match="distinct decision times"):
        purged_walk_forward_splits(
            np.array([0, 1, 2], dtype=np.int64),
            np.array([1, 2, 3], dtype=np.int64),
            n_splits=3,
            embargo_ms=0,
        )


def test_fails_closed_when_purge_empties_the_train_set() -> None:
    # Test block {1}, test_start=1; both samples resolve at/after 1 -> train empty.
    with pytest.raises(PurgedCvError, match="empty train set"):
        purged_walk_forward_splits(
            np.array([0, 1], dtype=np.int64),
            np.array([1, 2], dtype=np.int64),
            n_splits=1,
            embargo_ms=0,
        )


@pytest.mark.parametrize("bad_n_splits", [0, -1])
def test_fails_closed_on_invalid_n_splits(bad_n_splits: int) -> None:
    with pytest.raises(PurgedCvError, match="n_splits"):
        purged_walk_forward_splits(
            np.arange(6, dtype=np.int64),
            np.arange(6, dtype=np.int64) + 1,
            n_splits=bad_n_splits,
            embargo_ms=0,
        )


def test_fails_closed_on_negative_embargo() -> None:
    with pytest.raises(PurgedCvError, match="embargo_ms"):
        purged_walk_forward_splits(
            np.arange(6, dtype=np.int64),
            np.arange(6, dtype=np.int64) + 1,
            n_splits=1,
            embargo_ms=-1,
        )
