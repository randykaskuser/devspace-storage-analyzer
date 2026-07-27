import os
import shutil
from pathlib import Path
from core.repo_cleaner import get_dir_size
from core.trash import hard_delete_directory_contents

# Define known global cache paths and their safety ratings
# Safety Rating: Safe, Moderate, Careful
from core.system_info import get_home_dir, get_local_appdata_dir, is_mac

def get_global_caches() -> dict:
    home = get_home_dir()
    local_appdata = get_local_appdata_dir()
    
    caches = {
        "NPM Cache": { "path": os.path.join(home, ".npm"), "safety": "🟢 Safe" },
        "Rustup Downloads": { "path": os.path.join(home, ".rustup", "downloads"), "safety": "🟢 Safe" },
        "Maven Repository": { "path": os.path.join(home, ".m2"), "safety": "🟡 Moderate" },
        "Gradle Caches": { "path": os.path.join(home, ".gradle", "caches"), "safety": "🟡 Moderate" },
        "Nuget Packages": { "path": os.path.join(home, ".nuget", "packages"), "safety": "🟡 Moderate" },
    }

    if is_mac():
        caches.update({
            "Yarn Cache": { "path": os.path.join(local_appdata, "Yarn"), "safety": "🟢 Safe" },
            "PNPM Store": { "path": os.path.join(local_appdata, "pnpm"), "safety": "🟢 Safe" }, # Varies but often local app data or home
            "Pip Cache": { "path": os.path.join(local_appdata, "pip"), "safety": "🟢 Safe" },
            "UV Cache": { "path": os.path.join(local_appdata, "uv"), "safety": "🟢 Safe" },
            "Cargo Registry": { "path": os.path.join(home, ".cargo", "registry", "cache"), "safety": "🟠 Rebuild Required" },
            "Electron Cache": { "path": os.path.join(local_appdata, "Electron"), "safety": "🟡 Review (If Unused)" },
            "Playwright Browsers": { "path": os.path.join(local_appdata, "ms-playwright"), "safety": "🟡 Review (If Unused)" },
        })
    else:
        caches.update({
            "NPM Cache (Windows)": { "path": os.path.join(local_appdata, "npm-cache"), "safety": "🟢 Safe" },
            "Yarn Cache": { "path": os.path.join(local_appdata, "Yarn", "Cache"), "safety": "🟢 Safe" },
            "PNPM Store": { "path": os.path.join(local_appdata, "pnpm", "store"), "safety": "🟢 Safe" },
            "PNPM Cache": { "path": os.path.join(local_appdata, "pnpm-cache"), "safety": "🟢 Safe" },
            "Pip Cache": { "path": os.path.join(local_appdata, "pip", "cache"), "safety": "🟢 Safe" },
            "UV Cache": { "path": os.path.join(local_appdata, "uv", "cache"), "safety": "🟢 Safe" },
            "Cargo Registry": { "path": os.path.join(home, ".cargo", "registry", "cache"), "safety": "🟠 Rebuild Required" },
            "Flutter Pub Cache": { "path": os.path.join(local_appdata, "Pub", "Cache"), "safety": "🟢 Safe" },
            "Go Build Cache": { "path": os.path.join(local_appdata, "go-build"), "safety": "🟠 Rebuild Required" },
            "Electron Cache": { "path": os.path.join(local_appdata, "electron", "Cache"), "safety": "🟡 Review (If Unused)" },
            "Playwright Browsers": { "path": os.path.join(local_appdata, "ms-playwright"), "safety": "🟡 Review (If Unused)" },
            "Android Studio NDKs (Old)": { "path": os.path.join(local_appdata, "Android", "Sdk", "ndk"), "safety": "🟡 Moderate" }
        })
    
    return caches

def scan_global_caches() -> list[dict]:
    """
    Scans for known global developer caches in the user profile.
    """
    found_caches = []
        
    caches = get_global_caches()
    for name, info in caches.items():
        full_path = info["path"]
        safety = info["safety"]
        if os.path.exists(full_path) and os.path.isdir(full_path):
            size = get_dir_size(full_path)
            if size > 0:
                found_caches.append({
                    "name": name,
                    "path": full_path,
                    "safety": safety,
                    "size_bytes": size
                })
                
    return sorted(found_caches, key=lambda x: x["size_bytes"], reverse=True)
