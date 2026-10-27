import os
from pathlib import Path

from core.repo_cleaner import is_broad_scan_root


def test_filesystem_root_is_broad():
    assert is_broad_scan_root(os.path.abspath(os.sep)) is True


def test_home_directory_is_broad():
    assert is_broad_scan_root(str(Path.home())) is True


def test_home_with_trailing_separator_is_broad():
    assert is_broad_scan_root(str(Path.home()) + os.sep) is True


def test_folder_directly_under_home_is_not_broad():
    assert is_broad_scan_root(str(Path.home() / "Development")) is False


def test_plain_dev_folder_is_not_broad(tmp_path):
    assert is_broad_scan_root(str(tmp_path / "Development")) is False


def test_relative_path_is_not_broad():
    assert is_broad_scan_root("Development") is False


def test_empty_path_is_not_broad():
    assert is_broad_scan_root("") is False
