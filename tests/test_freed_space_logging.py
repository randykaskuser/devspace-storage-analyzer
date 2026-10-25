"""Tests for Finding D: freed-space logging must never overstate deletions.

The old delete threads counted an item as freed whenever any child was
removed (``s > 0 or f == 0``), so a partially failed deletion still
logged the full pre-scan size to history and inflated the success dialog.
The rule now: only a result with zero failures counts as freed, and a
partial result is reported as failed instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.trash import hard_delete_directory_contents, is_fully_deleted


def test_fully_deleted_requires_zero_failures():
    assert is_fully_deleted(5, 0) is True


def test_partial_deletion_is_not_freed():
    # 9 of 10 children removed: honest answer is "not freed".
    assert is_fully_deleted(9, 1) is False


def test_empty_directory_counts_as_freed():
    # Nothing was in it, nothing is left in it, scanned size is zero.
    assert is_fully_deleted(0, 0) is True


def test_refused_target_is_not_freed():
    # hard_delete returns (0, 1) for a refused target; never log it.
    assert is_fully_deleted(0, 1) is False


def test_real_deletion_reports_fully_deleted(tmp_path):
    target = tmp_path / "cache"
    target.mkdir()
    (target / "a.txt").write_text("x")
    (target / "b").mkdir()
    (target / "b" / "c.txt").write_text("y")

    s, f = hard_delete_directory_contents(str(target))

    assert (s, f) == (2, 0)
    assert is_fully_deleted(s, f) is True
    assert list(target.iterdir()) == []
