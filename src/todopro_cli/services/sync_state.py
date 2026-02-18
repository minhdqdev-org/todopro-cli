"""Sync state manager for tracking synchronization timestamps.

Manages last sync times per context to enable incremental sync operations.
State is persisted in ~/.todopro/sync-state.yaml.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SyncState:
    """Manages sync state persistence."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize sync state manager.

        Args:
            config_dir: Optional config directory path. Defaults to ~/.todopro
        """
        if config_dir is None:
            config_dir = Path.home() / ".todopro"

        self.config_dir = Path(config_dir)
        self.state_file = self.config_dir / "sync-state.json"
        self._state: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load sync state from file."""
        if not self.state_file.exists():
            self._state = {"last_sync": {}}
            return

        try:
            with open(self.state_file, encoding="utf-8") as f:
                self._state = json.load(f) or {"last_sync": {}}

            # Ensure last_sync key exists
            if "last_sync" not in self._state:
                self._state["last_sync"] = {}
        except Exception:
            # If file is corrupted, start fresh
            self._state = {"last_sync": {}}

    def _save(self) -> None:
        """Save sync state to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def get_last_sync(self, context_key: str) -> datetime | None:
        """Get last sync timestamp for a context.

        Args:
            context_key: Context identifier (e.g., "local:work -> remote:api")

        Returns:
            Last sync datetime or None if never synced
        """
        timestamp_str = self._state["last_sync"].get(context_key)
        if timestamp_str is None:
            return None

        if isinstance(timestamp_str, datetime):
            # Ensure aware datetime with UTC
            if timestamp_str.tzinfo is None:
                return timestamp_str.replace(tzinfo=UTC)
            return timestamp_str

        # Parse ISO format string and return as aware UTC
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        # Ensure it has UTC timezone
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    def set_last_sync(
        self, context_key: str, timestamp: datetime | None = None
    ) -> None:
        """Set last sync timestamp for a context.

        Args:
            context_key: Context identifier
            timestamp: Sync timestamp. Defaults to current time.
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)

        # Make naive if aware for consistent storage
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)

        # Store as ISO format string
        self._state["last_sync"][context_key] = timestamp.isoformat() + "Z"
        self._save()

    def clear_last_sync(self, context_key: str) -> None:
        """Clear last sync timestamp for a context.

        Args:
            context_key: Context identifier
        """
        if context_key in self._state["last_sync"]:
            del self._state["last_sync"][context_key]
            self._save()

    def get_all_sync_times(self) -> dict[str, datetime | None]:
        """Get all sync timestamps.

        Returns:
            Dictionary mapping context keys to last sync times (naive UTC)
        """
        result: dict[str, datetime | None] = {}
        for key, value in self._state["last_sync"].items():
            if value is None:
                result[key] = None
            elif isinstance(value, datetime):
                # Make naive if aware
                if value.tzinfo is not None:
                    result[key] = value.replace(tzinfo=None)
                else:
                    result[key] = value
            else:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                result[key] = dt.replace(tzinfo=None)
        return result

    @staticmethod
    def make_context_key(
        source_context: str, target_context: str, direction: str
    ) -> str:
        """Create a context key for sync state tracking.

        Args:
            source_context: Source context name
            target_context: Target context name
            direction: "pull" or "push"

        Returns:
            Context key string
        """
        return f"{source_context} -> {target_context} ({direction})"
