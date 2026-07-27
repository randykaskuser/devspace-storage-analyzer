import os
import shutil
import ctypes
from typing import Dict, Any, List
from core.trash import hard_delete_directory_contents
from core.repo_cleaner import get_dir_size

WINDOWS_CACHES = [
    {
        "category": "Temporary",
        "name": "User Temp",
        "path": os.environ.get("TEMP", r"C:\Temp"),
        "safety": "🟢 Safe",
        "desc": "Temporary files created by your applications and installers."
    },
    {
        "category": "Temporary",
        "name": "Windows Temp",
        "path": r"C:\Windows\Temp",
        "safety": "🟢 Safe",
        "desc": "System-wide temporary files (may require admin privileges to fully clean)."
    },
    {
        "category": "Windows",
        "name": "Delivery Optimization",
        "path": r"C:\Windows\SoftwareDistribution\DeliveryOptimization",
        "safety": "🟢 Safe",
        "desc": "Cache for Windows updates shared over the local network."
    },
    {
        "category": "Windows",
        "name": "Windows Update Cache",
        "path": r"C:\Windows\SoftwareDistribution\Download",
        "safety": "🟡 Moderate",
        "desc": "Downloaded update files. Safe to clear if no updates are currently running."
    },
    {
        "category": "GPU",
        "name": "DirectX Shader Cache",
        "path": os.path.join(os.environ.get("LOCALAPPDATA", ""), "D3DSCache"),
        "safety": "🟢 Safe",
        "desc": "Compiled DirectX shaders."
    },
    {
        "category": "GPU",
        "name": "NVIDIA DXCache",
        "path": os.path.join(os.environ.get("LOCALAPPDATA", ""), "NVIDIA", "DXCache"),
        "safety": "🟢 Safe",
        "desc": "Compiled NVIDIA DirectX shaders."
    },
    {
        "category": "GPU",
        "name": "NVIDIA GLCache",
        "path": os.path.join(os.environ.get("LOCALAPPDATA", ""), "NVIDIA", "GLCache"),
        "safety": "🟢 Safe",
        "desc": "Compiled NVIDIA OpenGL shaders."
    },
    {
        "category": "GPU",
        "name": "AMD Shader Cache",
        "path": os.path.join(os.environ.get("LOCALAPPDATA", ""), "AMD", "DxCache"),
        "safety": "🟢 Safe",
        "desc": "Compiled AMD shaders."
    }
]

def scan_windows_storage() -> List[Dict[str, Any]]:
    """Scans developer-relevant Windows storage caches."""
    results = []
    
    # 1. Standard Folder Caches
    for cache in WINDOWS_CACHES:
        path = cache["path"]
        size = get_dir_size(path) if os.path.exists(path) else 0
        if size > 0:
            results.append({
                "category": cache["category"],
                "name": cache["name"],
                "path": path,
                "size_bytes": size,
                "safety": cache["safety"],
                "desc": cache["desc"],
                "type": "folder"
            })
            
    # 2. Recycle Bin (Special handling)
    try:
        # Check size of recycle bin (simplistic check for C drive, ideally requires Shell API)
        rb_path = r"C:\$Recycle.Bin"
        rb_size = get_dir_size(rb_path) if os.path.exists(rb_path) else 0
        if rb_size > 0:
            results.append({
                "category": "Misc",
                "name": "Recycle Bin",
                "path": "RecycleBin",
                "size_bytes": rb_size,
                "safety": "🟢 Safe",
                "desc": "Deleted files waiting to be permanently removed.",
                "type": "recycle_bin"
            })
    except Exception:
        pass
        
    return results

def empty_recycle_bin() -> bool:
    """Empties the Windows Recycle Bin using ctypes."""
    try:
        SHEmptyRecycleBin = ctypes.windll.shell32.SHEmptyRecycleBinW
        # Flags: SHERB_NOCONFIRMATION = 1, SHERB_NOPROGRESSUI = 2, SHERB_NOSOUND = 4
        result = SHEmptyRecycleBin(None, None, 7)
        return result == 0
    except Exception:
        return False
