"""First automated tests for the repo.

Covers the safety guards in core.trash.hard_delete_directory_contents:
refusals must never touch the target, and legitimate cache dirs must be
cleaned exactly as before.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.trash import hard_delete_directory_contents, is_safe_deletion_target


def _make_tree(root: Path) -> None:
    (root / "file.txt").write_text("data")
    (root / "subdir").mkdir()
    (root / "subdir" / "nested.txt").write_text("nested")


def _snapshot(root: Path) -> set:
    return {p.relative_to(root) for p in root.rglob("*")}


def test_deletes_normal_contents_and_keeps_root(tmp_path):
    """Behaviour for legitimate cache dirs is unchanged."""
    target = tmp_path / "cache"
    target.mkdir()
    _make_tree(target)

    s, f = hard_delete_directory_contents(str(target))

    assert (s, f) == (2, 0)  # two top-level items: file.txt and subdir/
    assert target.exists()  # the root dir itself is kept
    assert list(target.iterdir()) == []


def test_refuses_filesystem_root(tmp_path):
    root = os.path.abspath(os.sep)
    assert not is_safe_deletion_target(root)
    assert hard_delete_directory_contents(root) == (0, 1)


def test_refuses_home_directory():
    home = str(Path.home())
    assert not is_safe_deletion_target(home)
    assert hard_delete_directory_contents(home) == (0, 1)


def test_refuses_protected_system_dir():
    candidate = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or "/usr"
    if not os.path.isdir(candidate):
        pytest.skip("no protected system dir found on this platform")
    assert not is_safe_deletion_target(candidate)
    before = _snapshot(Path(candidate))
    assert hard_delete_directory_contents(candidate) == (0, 1)
    assert _snapshot(Path(candidate)) == before  # untouched


def test_refuses_shallow_path():
    # e.g. "/tmp" or a "C:\\Temp" fallback: real dirs, but too shallow to be
    # a legitimate cache target.
    candidate = os.path.join(os.path.abspath(os.sep), "tmp")
    if not os.path.isdir(candidate):
        pytest.skip("no shallow real dir on this platform")
    assert not is_safe_deletion_target(candidate)
    before = _snapshot(Path(candidate))
    assert hard_delete_directory_contents(candidate) == (0, 1)
    assert _snapshot(Path(candidate)) == before  # untouched


def test_refuses_relative_path(tmp_path, monkeypatch):
    # Regression: a relative path (e.g. LOCALAPPDATA unset -> "Yarn\\Cache")
    # must never delete a CWD-relative directory.
    monkeypatch.chdir(tmp_path)
    victim = tmp_path / "D3DSCache"
    victim.mkdir()
    (victim / "x.bin").write_text("x")

    assert not is_safe_deletion_target("D3DSCache")
    assert hard_delete_directory_contents("D3DSCache") == (0, 1)
    assert (victim / "x.bin").exists()  # untouched


def test_accepts_depth_two_safe_dir():
    # Boundary check: a real, non-protected dir exactly 2 components deep
    # (the C:\Windows\Temp case on Windows) must stay cleanable.
    # "/tmp" itself is depth 1 (refused); a dir inside it is depth 2 (allowed).
    tmp_anchor = os.path.join(os.path.abspath(os.sep), "tmp")
    if not os.path.isdir(tmp_anchor):
        pytest.skip("no /tmp-style dir on this platform")
    probe = os.path.join(tmp_anchor, ".ssguard-depth2-probe")
    try:
        os.makedirs(probe, exist_ok=True)
    except OSError:
        pytest.skip("cannot create dir under /tmp on this machine")
    try:
        assert is_safe_deletion_target(probe)
        (Path(probe) / "x.txt").write_text("x")
        s, f = hard_delete_directory_contents(probe)
        assert (s, f) == (1, 0)
        assert list(Path(probe).iterdir()) == []
    finally:
        import shutil
        shutil.rmtree(probe, ignore_errors=True)


def test_refuses_nonexistent_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    assert not is_safe_deletion_target(str(missing))
    assert hard_delete_directory_contents(str(missing)) == (0, 1)


def test_symlink_child_removes_link_only(tmp_path):
    if os.name == "nt":
        pytest.skip("symlink creation needs extra privileges on Windows")
    target = tmp_path / "cache"
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("do not delete")
    (target / "link").symlink_to(outside, target_is_directory=True)

    s, f = hard_delete_directory_contents(str(target))

    assert f == 0
    assert secret.exists()  # the link target is untouched
    assert not os.path.lexists(target / "link")  # only the link was removed


def test_symlinked_root_cleans_intended_contents(tmp_path):
    # A symlinked root (e.g. ~/.npm -> another drive) resolves first; the
    # resolved target is guarded and its contents cleaned, the link survives.
    if os.name == "nt":
        pytest.skip("symlink creation needs extra privileges on Windows")
    real = tmp_path / "real-cache"
    real.mkdir()
    (real / "a.txt").write_text("a")
    link = tmp_path / "cache-link"
    link.symlink_to(real, target_is_directory=True)

    s, f = hard_delete_directory_contents(str(link))

    assert (s, f) == (1, 0)
    assert list(real.iterdir()) == []
    assert link.is_symlink()
