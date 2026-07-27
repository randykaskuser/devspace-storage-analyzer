import os
import sys
import ctypes
import shutil
import platform
from pathlib import Path

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_mac() -> bool:
    return platform.system() == "Darwin"

def is_windows() -> bool:
    return platform.system() == "Windows"

def get_home_dir() -> str:
    return str(Path.home())

def get_local_appdata_dir() -> str:
    if is_mac():
        return os.path.join(get_home_dir(), "Library", "Caches")
    return os.environ.get("LOCALAPPDATA", "")

def get_appdata_dir() -> str:
    if is_mac():
        return os.path.join(get_home_dir(), "Library", "Application Support")
    return os.environ.get("APPDATA", "")

def is_admin() -> bool:
    """Checks if the application is running with administrative privileges."""
    try:
        if is_windows():
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False

def get_system_drive_path() -> str:
    return "/" if is_mac() else "C:\\"

def get_disk_usage(path: str = None) -> tuple:
    """Returns (total, used, free) disk space in bytes for the given path."""
    if not path:
        path = get_system_drive_path()
    try:
        total, used, free = shutil.disk_usage(path)
        return total, used, free
    except Exception:
        return 0, 0, 0

def format_size(size_bytes: int) -> str:
    """Formats bytes into human-readable string."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {units[i]}"
