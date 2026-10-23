"""Tests for core.duplicate_finder — the byte-identical grouping engine.

No PySide6 involved: the grouping logic is pure stdlib so it runs headless.
The only UI-adjacent behaviour, trash_duplicates, is tested against a
monkeypatched core.trash.safe_delete — no real Trash touched.
"""

import os

import pytest

from core import duplicate_finder
from core import trash


def _write(path, data: bytes):
    path = str(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def _groups_by_content(groups):
    """Map each group to its file content (for readable assertions)."""
    out = {}
    for g in groups:
        with open(g["paths"][0], "rb") as fh:
            out[fh.read()] = sorted(g["paths"])
    return out


def test_groups_identical_files(tmp_path):
    _write(tmp_path / "a.bin", b"hello" * 100)
    _write(tmp_path / "sub" / "b.bin", b"hello" * 100)
    _write(tmp_path / "unique.bin", b"something else entirely!!")
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    assert errors == []
    by_content = _groups_by_content(groups)
    assert len(by_content) == 1
    dup_paths = by_content[b"hello" * 100]
    assert len(dup_paths) == 2


def test_same_size_different_content_not_grouped(tmp_path):
    _write(tmp_path / "a.bin", b"AAAA" * 64)
    _write(tmp_path / "b.bin", b"BBBB" * 64)
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    assert groups == []
    assert errors == []


def test_empty_files_skipped_by_default(tmp_path):
    _write(tmp_path / "e1", b"")
    _write(tmp_path / "e2", b"")
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    assert groups == []
    assert errors == []


def test_min_size_zero_includes_empty_files(tmp_path):
    _write(tmp_path / "e1", b"")
    _write(tmp_path / "e2", b"")
    groups, errors = duplicate_finder.find_duplicates(
        [str(tmp_path)], min_size=0)
    assert len(groups) == 1
    assert len(groups[0]["paths"]) == 2
    assert errors == []


def test_groups_sorted_by_reclaimable_bytes_desc(tmp_path):
    big = b"X" * 10_000
    small = b"y" * 100
    _write(tmp_path / "big1", big)
    _write(tmp_path / "big2", big)
    _write(tmp_path / "s1", small)
    _write(tmp_path / "s2", small)
    _write(tmp_path / "s3", small)
    groups, _ = duplicate_finder.find_duplicates([str(tmp_path)])
    assert len(groups) == 2
    # big group reclaims 10_000, small group reclaims 200 → big first
    assert groups[0]["size"] == 10_000
    assert groups[1]["size"] == 100


def test_group_reclaimable_bytes():
    group = {"size": 500, "sha256": "x", "paths": ["a", "b", "c"]}
    assert duplicate_finder.group_reclaimable_bytes(group) == 1000


def test_symlinked_directories_not_followed(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    _write(real / "dup1", b"data" * 50)
    _write(real / "dup2", b"data" * 50)
    os.symlink(str(real), str(tmp_path / "linkdir"))
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    # The real dir yields one 2-file group; the symlink must not add a
    # phantom second group or double the paths.
    assert len(groups) == 1
    assert len(groups[0]["paths"]) == 2
    assert errors == []


def test_symlinked_files_not_grouped(tmp_path):
    _write(tmp_path / "orig", b"target-data" * 40)
    os.symlink(str(tmp_path / "orig"), str(tmp_path / "linkfile"))
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    assert groups == []
    assert errors == []


def test_hardlinks_collapse_to_one_entry(tmp_path):
    _write(tmp_path / "orig", b"shared-bytes" * 60)
    os.link(str(tmp_path / "orig"), str(tmp_path / "hardlink"))
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    # Same inode twice is the SAME file, not a duplicate pair.
    assert groups == []
    assert errors == []


def test_unreadable_file_reported_not_raised(tmp_path, monkeypatch):
    # chmod-based unreadability is meaningless when running as root, so
    # force the failure at the hashing layer instead: deterministic on any
    # user, and it exercises the same "collect error, keep scanning" path.
    _write(tmp_path / "ok1", b"same" * 30)
    _write(tmp_path / "ok2", b"same" * 30)
    _write(tmp_path / "bad", b"same" * 30)

    real_hash = duplicate_finder._sha256_of

    def flaky_hash(path):
        if path.endswith("bad"):
            raise OSError("permission denied (simulated)")
        return real_hash(path)

    monkeypatch.setattr(duplicate_finder, "_sha256_of", flaky_hash)
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    # One unreadable path must not abort the scan of the readable pair.
    assert any("unreadable" in e for e in errors)
    assert len(groups) == 1
    assert len(groups[0]["paths"]) == 2


def test_refuses_relative_and_missing_roots(tmp_path):
    groups, errors = duplicate_finder.find_duplicates(
        ["relative/path", str(tmp_path / "does-not-exist")])
    assert groups == []
    assert len(errors) == 2


def test_empty_root_yields_no_groups(tmp_path):
    groups, errors = duplicate_finder.find_duplicates([str(tmp_path)])
    assert groups == []
    assert errors == []


def test_on_progress_called_during_walk(tmp_path):
    for i in range(300):
        _write(tmp_path / f"f{i}", b"z" * 10)
    seen = []
    duplicate_finder.find_duplicates(
        [str(tmp_path)], on_progress=lambda n: seen.append(n))
    assert seen, "progress callback was never invoked"
    assert seen == sorted(seen)


def test_trash_duplicates_routes_through_safe_delete(tmp_path, monkeypatch):
    calls = []

    def fake_safe_delete(path):
        calls.append(path)
        return True

    monkeypatch.setattr(trash, "safe_delete", fake_safe_delete)
    _write(tmp_path / "a", b"1" * 10)
    _write(tmp_path / "b", b"1" * 10)
    trashed, failed = duplicate_finder.trash_duplicates(
        [str(tmp_path / "a"), str(tmp_path / "b")])
    assert (trashed, failed) == (2, 0)
    assert sorted(calls) == sorted([str(tmp_path / "a"), str(tmp_path / "b")])


def test_trash_duplicates_counts_failures(tmp_path, monkeypatch):
    def fake_safe_delete(path):
        return "good" in path

    monkeypatch.setattr(trash, "safe_delete", fake_safe_delete)
    trashed, failed = duplicate_finder.trash_duplicates(
        ["/x/good1", "/x/bad1"])
    assert (trashed, failed) == (1, 1)


def test_trash_duplicates_survives_exceptions(tmp_path, monkeypatch):
    def boom(path):
        raise RuntimeError("trash exploded")

    monkeypatch.setattr(trash, "safe_delete", boom)
    trashed, failed = duplicate_finder.trash_duplicates(["/x/any"])
    assert (trashed, failed) == (0, 1)
