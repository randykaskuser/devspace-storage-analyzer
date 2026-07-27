import os
import json
from datetime import datetime

class DevSpaceDB:
    def __init__(self):
        self.profile_dir = os.path.join(os.environ.get("USERPROFILE", ""), ".devspace")
        self.stats_file = os.path.join(self.profile_dir, "stats.json")
        self.history_file = os.path.join(self.profile_dir, "history.json")
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

# Global singleton
db = DevSpaceDB()
