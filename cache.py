import os
import json
from datetime import datetime, timedelta

class JsonCache:
    def __init__(self, base_dir=None, expiry_minutes=1440):
        # Default: tmp/outlook-cache inside repo directory
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "tmp", "outlook-cache")
        self.cache_dir = base_dir
        self.expiry = timedelta(minutes=expiry_minutes)

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_file(self, key: str):
        """Return full path for cache file based on key."""
        safe_key = key.replace(" ", "_")
        return os.path.join(self.cache_dir, f"{safe_key}.json")

    def load(self, key: str):
        """Return cached data if valid, else None."""
        cache_path = self._cache_file(key)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

        timestamp_str = data.get("timestamp")
        if not timestamp_str:
            return None

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return None

        if datetime.now() - timestamp < self.expiry:
            return data.get("events")
        return None

    def save(self, key: str, events):
        """Save events to cache with timestamp."""
        cache_path = self._cache_file(key)
        data = {
            "timestamp": datetime.now().isoformat(),
            "events": events
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
