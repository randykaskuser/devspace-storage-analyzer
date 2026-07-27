import json
import subprocess
import os
from PySide6.QtCore import QThread, Signal
from core.global_cache_cleaner import scan_global_caches
from core.repo_cleaner import get_dir_size
from core.windows_cleaner import scan_windows_storage

class BackgroundAggregatorThread(QThread):
    finished = Signal(dict)
    
    def run(self):
        stats = {
            "global_caches": [],
            "docker_df": [],
            "wsl_distros": [],
            "windows_storage": [],
            "total_recoverable": 0
        }
        
        # 1. Scan Global Caches
        caches = scan_global_caches()
        stats["global_caches"] = caches
        for c in caches:
            stats["total_recoverable"] += c.get("size_bytes", 0)
            
        # 2. Docker DF
        try:
            # We run `docker system df --format json`
            result = subprocess.run(["docker", "system", "df", "--format", "{{json .}}"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                docker_data = []
                for line in lines:
                    if line.strip():
                        docker_data.append(json.loads(line))
                stats["docker_df"] = docker_data
        except Exception:
            pass
            
        # 3. WSL Distros
        try:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            packages_dir = os.path.join(local_appdata, "Packages")
            
            if os.path.exists(packages_dir):
                for pkg in os.listdir(packages_dir):
                    vhdx_path = os.path.join(packages_dir, pkg, "LocalState", "ext4.vhdx")
                    if os.path.exists(vhdx_path):
                        size = os.path.getsize(vhdx_path)
                        distro_name = pkg.split('_')[0]
                        if "Canonical" in pkg: distro_name = "Ubuntu"
                        elif "Debian" in pkg: distro_name = "Debian"
                        elif "SUSE" in pkg: distro_name = "SUSE"
                        
                        stats["wsl_distros"].append({
                            "name": distro_name,
                            "size_bytes": size,
                            "path": vhdx_path
                        })
                        stats["total_recoverable"] += size
        except Exception:
            pass
            
        # 4. Windows Storage
        try:
            win_storage = scan_windows_storage()
            stats["windows_storage"] = win_storage
            for w in win_storage:
                stats["total_recoverable"] += w.get("size_bytes", 0)
        except Exception:
            pass
            
        self.finished.emit(stats)
