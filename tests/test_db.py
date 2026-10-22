"""Tests for core.db.DevSpaceDB profile-dir resolution.

Regression tests for the macOS bug: the profile dir was built from the
Windows-only USERPROFILE env var, so on macOS stats/history landed in a
CWD-relative `.devspace` folder. The profile dir must always resolve to
~/.devspace via the platform-correct home directory.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.db
from core.db import DevSpaceDB
from core.system_info import get_home_dir


def test_profile_dir_is_absolute_under_home():
    db = DevSpaceDB()
    assert os.path.isabs(db.profile_dir)
    assert db.profile_dir == os.path.join(get_home_dir(), ".devspace")


def test_profile_dir_independent_of_userprofile(monkeypatch):
    """USERPROFILE (Windows-only) must not influence the profile dir."""
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Nobody")
    db = DevSpaceDB()
    assert db.profile_dir == os.path.join(get_home_dir(), ".devspace")
    assert "Nobody" not in db.profile_dir


def test_profile_files_created_under_home(monkeypatch, tmp_path):
    """stats.json/history.json are created inside the resolved profile dir,
    never in the current working directory (the old macOS bug)."""
    monkeypatch.setattr(core.db, "get_home_dir", lambda: str(tmp_path))
    monkeypatch.setattr(core.db.os, "getcwd", lambda: str(tmp_path / "launch-dir"))
    db = DevSpaceDB()
    assert db.profile_dir == str(tmp_path / ".devspace")
    assert os.path.isfile(db.stats_file)
    assert os.path.isfile(db.history_file)
    assert not (tmp_path / "launch-dir" / ".devspace").exists()


def test_stats_roundtrip_in_isolated_home(monkeypatch, tmp_path):
    """log_cleanup -> get_stats/get_history works in a redirected home."""
    monkeypatch.setattr(core.db, "get_home_dir", lambda: str(tmp_path))
    db = DevSpaceDB()
    db.log_cleanup("npm cache", 1024)
    stats = db.get_stats()
    assert stats["lifetime_freed_bytes"] == 1024
    history = db.get_history()
    assert history and history[0]["item"] == "npm cache"
    assert history[0]["bytes_freed"] == 1024
