"""Background task cache for optimistic UI updates."""

import json
import time
from pathlib import Path

from platformdirs import user_cache_dir

CACHE_DIR = Path(user_cache_dir("todopro"))
PROCESSING_CACHE_FILE = CACHE_DIR / "processing_tasks.json"
SUFFIX_MAPPING_FILE = CACHE_DIR / "suffix_mapping.json"
CACHE_TTL = 30  # 30 seconds
SUFFIX_MAPPING_TTL = 300  # 5 minutes for suffix mappings


class BackgroundTaskCache:
    """Cache for tasks being processed in background."""

    def __init__(self):
        self.cache_file = PROCESSING_CACHE_FILE
        self.cache_dir = CACHE_DIR

    def _load_cache(self) -> dict[str, float]:
        """Load cache from file.

        Returns:
            Dict mapping task_id to timestamp
        """
        if not self.cache_file.exists():
            return {}

        try:
            return json.loads(self.cache_file.read_text())
        except Exception:
            return {}

    def _save_cache(self, cache: dict[str, float]) -> None:
        """Save cache to file."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(cache, indent=2))
        except Exception:
            pass

    def _clean_expired(self, cache: dict[str, float]) -> dict[str, float]:
        """Remove expired entries from cache.

        Args:
            cache: Current cache dict

        Returns:
            Cleaned cache dict
        """
        now = time.time()
        return {
            task_id: timestamp
            for task_id, timestamp in cache.items()
            if now - timestamp < CACHE_TTL
        }

    def add_completing_task(self, task_id: str) -> None:
        """Add a task to the completing cache.

        Args:
            task_id: ID of the task being completed
        """
        cache = self._load_cache()
        cache = self._clean_expired(cache)
        cache[task_id] = time.time()
        self._save_cache(cache)

    def add_completing_tasks(self, task_ids: list[str]) -> None:
        """Add multiple tasks to the completing cache.

        Args:
            task_ids: List of task IDs being completed
        """
        cache = self._load_cache()
        cache = self._clean_expired(cache)
        now = time.time()
        for task_id in task_ids:
            cache[task_id] = now
        self._save_cache(cache)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the cache.

        Args:
            task_id: ID of the task to remove
        """
        cache = self._load_cache()
        if task_id in cache:
            del cache[task_id]
            self._save_cache(cache)

    def is_being_completed(self, task_id: str) -> bool:
        """Check if a task is being completed in background.

        Args:
            task_id: ID of the task to check

        Returns:
            True if task is in completing cache
        """
        cache = self._load_cache()
        cache = self._clean_expired(cache)
        return task_id in cache

    def get_completing_tasks(self) -> list[str]:
        """Get list of task IDs being completed.

        Returns:
            List of task IDs
        """
        cache = self._load_cache()
        cache = self._clean_expired(cache)
        # Save cleaned cache back to disk
        self._save_cache(cache)
        return list(cache.keys())

    def clear_expired(self) -> None:
        """Clear expired entries from cache."""
        cache = self._load_cache()
        cleaned = self._clean_expired(cache)
        if len(cleaned) < len(cache):
            self._save_cache(cleaned)

    def clear_all(self) -> None:
        """Clear all entries from cache."""
        if self.cache_file.exists():
            from contextlib import suppress

            with suppress(Exception):
                self.cache_file.unlink()


# Singleton instance
_cache_instance = None


def get_background_cache() -> BackgroundTaskCache:
    """Get singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = BackgroundTaskCache()
    return _cache_instance


def save_suffix_mapping(suffix_map: dict[str, str]) -> None:
    """Save suffix to full task ID mapping.

    Args:
        suffix_map: Dict mapping suffix -> full_task_id
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": time.time(),
            "mapping": suffix_map,
        }
        SUFFIX_MAPPING_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def get_suffix_mapping() -> dict[str, str]:
    """Get cached suffix to task ID mapping.

    Returns:
        Dict mapping suffix -> full_task_id, or empty dict if expired/missing
    """
    if not SUFFIX_MAPPING_FILE.exists():
        return {}

    try:
        data = json.loads(SUFFIX_MAPPING_FILE.read_text())
        timestamp = data.get("timestamp", 0)
        mapping = data.get("mapping", {})

        # Check if expired
        if time.time() - timestamp > SUFFIX_MAPPING_TTL:
            return {}

        return mapping
    except Exception:
        return {}
