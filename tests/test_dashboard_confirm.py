"""Tests for the Dashboard "Clean Recommended" confirmation text.

The dialog copy is the user-visible contract of the confirmation: it must
name what will be deleted, state that the deletion is permanent, and
total the sizes. The Qt wiring itself (QMessageBox in dashboard_tab.py)
cannot run here (no PySide6 in this environment); it is syntax-checked
with py_compile instead, as with the other tab files.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.clean_confirmation import format_clean_confirmation


def test_single_item_names_cache_size_and_permanence():
    text = format_clean_confirmation([{"name": "NPM Cache", "size": 1024}])
    assert "Permanently delete 1 safe global cache" in text
    assert "NPM Cache" in text
    assert "1.00 KB" in text
    assert "Recycle Bin/Trash" in text
    assert "cannot be restored" in text


def test_multiple_items_list_every_cache_and_total():
    items = [
        {"name": "NPM Cache", "size": 1024},
        {"name": "Pip Cache", "size": 2048},
    ]
    text = format_clean_confirmation(items)
    assert "2 safe global caches" in text
    assert "3.00 KB total" in text
    assert "NPM Cache" in text
    assert "Pip Cache" in text


def test_zero_size_cache_still_listed():
    text = format_clean_confirmation([{"name": "Empty Cache", "size": 0}])
    assert "Empty Cache" in text
    assert "0 B total" in text
