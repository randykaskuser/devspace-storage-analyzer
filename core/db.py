import os
import json
from datetime import datetime

from core.system_info import get_home_dir

class DevSpaceDB:
    def __init__(self):
        # USERPROFILE is Windows-only; on macOS/Linux it is unset, which used
        # to make this a CWD-relative ".devspace" folder. get_home_dir() is
        # platform-correct (Path.home()) on every OS.
        self.profile_dir = os.path.join(get_home_dir(), ".devspace")
        self.stats_file = os.path.join(self.profile_dir, "stats.json")
        self.history_file = os.path.join(self.profile_dir, "history.json")
        self.settings_file = os.path.join(self.profile_dir, "settings.json")
        self._ensure_dirs()
        self._ensure_files()
        
    def _ensure_dirs(self):
        os.makedirs(self.profile_dir, exist_ok=True)
        
    def _ensure_files(self):
        if not os.path.exists(self.stats_file):
            default_stats = {
                "lifetime_freed_bytes": 0,
                "largest_cleanup_bytes": 0,
                "cleanup_sessions": 0,
                "first_installed": datetime.now().strftime("%Y-%m-%d")
            }
            self._write_json(self.stats_file, default_stats)
            
        if not os.path.exists(self.history_file):
            self._write_json(self.history_file, [])

        if not os.path.exists(self.settings_file):
            self._write_json(self.settings_file, {})
            
    def _read_json(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {} if filepath == self.stats_file else []
            
    def _write_json(self, filepath, data):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass
            
    def get_stats(self):
        return self._read_json(self.stats_file)
        
    def get_history(self):
        return self._read_json(self.history_file)
        
    def log_cleanup(self, item_name, bytes_freed):
        """Logs a single item cleanup and updates lifetime stats."""
        if bytes_freed <= 0: return
        
        # 1. Update History
        history = self.get_history()
        today = datetime.now().strftime("%Y-%m-%d")
        
        log_entry = {
            "date": today,
            "timestamp": datetime.now().isoformat(),
            "item": item_name,
            "bytes_freed": bytes_freed
        }
        history.insert(0, log_entry) # Prepend
        
        # Keep only last 1000 entries
        if len(history) > 1000:
            history = history[:1000]
            
        self._write_json(self.history_file, history)
        
        # 2. Update Stats
        stats = self.get_stats()
        stats["lifetime_freed_bytes"] = stats.get("lifetime_freed_bytes", 0) + bytes_freed
        
        if bytes_freed > stats.get("largest_cleanup_bytes", 0):
            stats["largest_cleanup_bytes"] = bytes_freed
            
        self._write_json(self.stats_file, stats)
        
    def increment_session(self):
        stats = self.get_stats()
        stats["cleanup_sessions"] = stats.get("cleanup_sessions", 0) + 1
        self._write_json(self.stats_file, stats)

    def get_workspace_dirs(self):
        """Workspace folders saved from the Workspaces tab.

        Loaded verbatim: entries are kept even if the folder is missing
        right now (a drive may be temporarily unmounted), and only
        string entries survive, so a hand-edited or corrupt file can
        never hand the scanner a non-path. A missing or corrupt
        settings file reads as no saved folders — the same empty
        state the tab had before this feature existed.
        """
        data = self._read_json(self.settings_file)
        if not isinstance(data, dict):
            return []
        dirs = data.get("workspace_dirs", [])
        if not isinstance(dirs, list):
            return []
        return [d for d in dirs if isinstance(d, str)]

    def set_workspace_dirs(self, dirs):
        """Persist the Workspaces tab's folder list."""
        data = self._read_json(self.settings_file)
        if not isinstance(data, dict):
            data = {}
        data["workspace_dirs"] = list(dirs)
        self._write_json(self.settings_file, data)

    def get_duplicates_root(self):
        """Last folder scanned from the Duplicates tab.

        Loaded verbatim and kept even if the folder is missing right
        now (a drive may be temporarily unmounted); only a string
        survives, so a hand-edited or corrupt file can never hand the
        scanner a non-path. A missing or corrupt settings file reads
        as no saved folder — the same empty state the tab had before
        this feature existed. A missing folder is refused gracefully
        by core.duplicate_finder (recorded in ``errors``, scan
        continues), so a stale saved root degrades to an empty
        result, never a crash.
        """
        data = self._read_json(self.settings_file)
        if not isinstance(data, dict):
            return ""
        root = data.get("duplicates_root", "")
        return root if isinstance(root, str) else ""

    def set_duplicates_root(self, root):
        """Persist the Duplicates tab's scanned folder."""
        data = self._read_json(self.settings_file)
        if not isinstance(data, dict):
            data = {}
        data["duplicates_root"] = root
        self._write_json(self.settings_file, data)

# Global singleton
db = DevSpaceDB()
