import os
import sys
import ctypes
import shutil

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_admin() -> bool:
    """Checks if the application is running with administrative privileges."""
    try:
        return os.getuid() == 0
    except AttributeError:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

def get_disk_usage(path: str = "C:\\") -> tuple:
    """Returns (total, used, free) disk space in bytes for the given path."""
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
