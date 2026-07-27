import os
import shutil
from pathlib import Path
from core.repo_cleaner import get_dir_size
from core.trash import hard_delete_directory_contents

# Define known global cache paths and their safety ratings
# Safety Rating: Safe, Moderate, Careful
GLOBAL_CACHES = {
    "NPM Cache": { "path": ".npm", "safety": "🟢 Safe" },
    "NPM Cache (Windows)": { "path": r"AppData\Local\npm-cache", "safety": "🟢 Safe" },
    "Yarn Cache": { "path": r"AppData\Local\Yarn\Cache", "safety": "🟢 Safe" },
    "PNPM Store": { "path": r"AppData\Local\pnpm\store", "safety": "🟢 Safe" },
    "PNPM Cache": { "path": r"AppData\Local\pnpm-cache", "safety": "🟢 Safe" },
    "Pip Cache": { "path": r"AppData\Local\pip\cache", "safety": "🟢 Safe" },
    "UV Cache": { "path": r"AppData\Local\uv\cache", "safety": "🟢 Safe" },
    "Cargo Registry": { "path": r".cargo\registry\cache", "safety": "🟠 Rebuild Required" },
    "Rustup Downloads": { "path": r".rustup\downloads", "safety": "🟢 Safe" },
    "Maven Repository": { "path": ".m2", "safety": "🟡 Moderate" },
    "Gradle Caches": { "path": r".gradle\caches", "safety": "🟡 Moderate" },
    "Flutter Pub Cache": { "path": r"AppData\Local\Pub\Cache", "safety": "🟢 Safe" },
    "Nuget Packages": { "path": r".nuget\packages", "safety": "🟡 Moderate" },
    "Go Build Cache": { "path": r"AppData\Local\go-build", "safety": "🟠 Rebuild Required" },
    "Electron Cache": { "path": r"AppData\Local\electron\Cache", "safety": "🟡 Review (If Unused)" },
    "Playwright Browsers": { "path": r"AppData\Local\ms-playwright", "safety": "🟡 Review (If Unused)" },
    "Android Studio NDKs (Old)": { "path": r"AppData\Local\Android\Sdk\ndk", "safety": "🟡 Moderate" }
}

def scan_global_caches() -> list[dict]:
    """
    Scans for known global developer caches in the user profile.
    """
    user_profile = os.environ.get("USERPROFILE", "")
    found_caches = []
    
    if not user_profile:
        return []
        
    for name, info in GLOBAL_CACHES.items():
        rel_path = info["path"]
        safety = info["safety"]
        full_path = os.path.join(user_profile, rel_path)
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
