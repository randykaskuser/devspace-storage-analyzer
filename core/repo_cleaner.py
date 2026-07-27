import os
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, List

TARGET_DIRS = {
    "node_modules": "NodeJS",
    ".next": "NextJS",
    ".nuxt": "NuxtJS",
    ".svelte-kit": "Svelte",
    ".turbo": "Turbo",
    ".venv": "Python",
    "venv": "Python",
    "__pycache__": "Python",
    ".pytest_cache": "Python",
    ".mypy_cache": "Python",
    ".ruff_cache": "Python",
    "target": "Rust/C++",
    "bin": "C#/.NET",
    "obj": "C#/.NET",
    ".vs": "Visual Studio",
    ".gradle": "Gradle",
    "build": "General Build",
    ".dart_tool": "Flutter"
}

def get_dir_size(path: str) -> int:
    """Returns the total size of a directory in bytes (highly optimized for Windows)."""
    total_size = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    total_size += get_dir_size(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    total_size += entry.stat(follow_symlinks=False).st_size
    except Exception:
        pass
    return total_size

def get_last_modified_time(repo_path: str) -> float:
    """Gets the timestamp of the most recently modified file in the root directory."""
    latest = 0
    try:
        for entry in os.scandir(repo_path):
            if entry.is_file() and not entry.name.startswith('.'):
                mtime = entry.stat().st_mtime
                if mtime > latest:
                    latest = mtime
    except Exception:
        pass
    return latest if latest > 0 else time.time()

def get_git_info(repo_path: str) -> Dict[str, Any]:
    """Gets the last commit date and branch name if the directory is a git repo."""
    try:
        # Check if git is installed and it's a valid repo
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "-1", "--format=%ct|%cr|%D"],
            capture_output=True, text=True, timeout=2,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|', 2)
            timestamp = int(parts[0])
            rel_time = parts[1]
            branch = parts[2].split(',')[0] if len(parts) > 2 else ""
            
            # Calculate days ago
            days_ago = (time.time() - timestamp) / 86400
            
            return {
                "is_repo": True,
                "timestamp": timestamp,
                "rel_time": rel_time,
                "days_ago": days_ago,
                "branch": branch
            }
    except Exception:
        pass
        
    return {"is_repo": False, "days_ago": 999, "rel_time": "Unknown", "branch": ""}

def identify_ecosystem(repo_path: str) -> str:
    """Identifies the ecosystem based on config files present."""
    if os.path.exists(os.path.join(repo_path, "package.json")):
        return "NodeJS"
    if os.path.exists(os.path.join(repo_path, "Cargo.toml")):
        return "Rust"
    if os.path.exists(os.path.join(repo_path, "requirements.txt")) or os.path.exists(os.path.join(repo_path, "pyproject.toml")):
        return "Python"
    if os.path.exists(os.path.join(repo_path, "build.gradle")) or os.path.exists(os.path.join(repo_path, "build.gradle.kts")):
        return "Java/Kotlin"
    if os.path.exists(os.path.join(repo_path, "pubspec.yaml")):
        return "Flutter"
    
    # Try finding .csproj
    for f in os.listdir(repo_path):
        if f.endswith(".csproj"):
            return "C#/.NET"
            
    return "Unknown Ecosystem"

def scan_repos(root_dirs: List[str]) -> List[Dict[str, Any]]:
    """
    Scans for development projects and identifies massive caches.
    Groups results by Project Repository.
    """
    projects = {}
    
    for root_dir in root_dirs:
        if not os.path.exists(root_dir):
            continue
            
        for dirpath, dirnames, _ in os.walk(root_dir):
            if '.git' in dirnames:
                dirnames.remove('.git')
                
            dirs_to_remove = []
            
            for d in dirnames:
                if d in TARGET_DIRS:
                    full_path = os.path.join(dirpath, d)
                    size = get_dir_size(full_path)
                    
                    if size > 0:
                        if dirpath not in projects:
                            eco = identify_ecosystem(dirpath)
                            git = get_git_info(dirpath)
                            
                            # Calculate Activity Score
                            mod_time = get_last_modified_time(dirpath)
                            mod_days_ago = (time.time() - mod_time) / 86400
                            
                            score = 100
                            if git["is_repo"]:
                                score -= min(50, git["days_ago"] / 7) # Up to 50 pts lost for 1 year old commits
                            else:
                                score -= 40 # Penalty for no repo
                                
                            score -= min(50, mod_days_ago / 3) # Up to 50 pts lost for old file modifications
                            
                            score = max(0, int(score))
                            
                            # Status Badges
                            if score > 80:
                                safety = "🔴 Active Project"
                            elif score > 50:
                                safety = "🟠 Rebuild Required"
                            elif score > 20:
                                safety = "🟡 Review"
                            else:
                                safety = "🟢 Safe (Archive Candidate)"
                                
                            projects[dirpath] = {
                                "project_name": os.path.basename(dirpath),
                                "project_path": dirpath,
                                "ecosystem": eco,
                                "git_info": git,
                                "activity_score": score,
                                "safety": safety,
                                "total_cache_size": 0,
                                "caches": []
                            }
                            
                        projects[dirpath]["caches"].append({
                            "name": d,
                            "path": full_path,
                            "size": size,
                            "type": TARGET_DIRS[d]
                        })
                        projects[dirpath]["total_cache_size"] += size
                    
                    dirs_to_remove.append(d)
                    
            for d in dirs_to_remove:
                dirnames.remove(d)
                
    # Flatten projects dictionary into a list
    result = list(projects.values())
    return sorted(result, key=lambda x: x['total_cache_size'], reverse=True)
