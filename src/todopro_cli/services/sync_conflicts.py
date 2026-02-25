"""Sync conflict tracker for logging and managing sync conflicts.

Tracks conflicts that occur during synchronization operations when
local and remote data have diverged.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SyncConflict:
    """Represents a single sync conflict."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        local_data: dict[str, Any],
        remote_data: dict[str, Any],
        resolution: str,
    ):
        """Initialize a sync conflict.

        Args:
            resource_type: Type of resource (task, project, label, etc.)
            resource_id: UUID of the conflicting resource
            local_data: Local version data
            remote_data: Remote version data
            resolution: How conflict was resolved (local_wins, remote_wins, skipped)
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.local_data = local_data
        self.remote_data = remote_data
        self.resolution = resolution
        from datetime import timezone

        self.detected_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def to_dict(self) -> dict[str, Any]:
        """Convert conflict to dictionary.

        Returns:
            Dictionary representation of conflict
        """
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "local_data": self.local_data,
            "remote_data": self.remote_data,
            "resolution": self.resolution,
            "detected_at": self.detected_at.isoformat() + "Z",
        }


class SyncConflictTracker:
    """Manages sync conflict logging and persistence."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize conflict tracker.

        Args:
            config_dir: Optional config directory path. Defaults to ~/.todopro
        """
        if config_dir is None:
            config_dir = Path.home() / ".todopro"

        self.config_dir = Path(config_dir)
        self.conflicts_file = self.config_dir / "sync-conflicts.json"
        self._conflicts: list[SyncConflict] = []

    def add_conflict(self, conflict: SyncConflict) -> None:
        """Add a conflict to the tracker.

        Args:
            conflict: SyncConflict instance to track
        """
        self._conflicts.append(conflict)

    def save(self) -> None:
        """Save conflicts to file."""
        if not self._conflicts:
            return

        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing conflicts if any
        existing_conflicts = []
        if self.conflicts_file.exists():
            try:
                with open(self.conflicts_file, "r") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_conflicts = existing_data
            except Exception:
                pass  # Start fresh if file is corrupted

        # Append new conflicts
        all_conflicts = existing_conflicts + [c.to_dict() for c in self._conflicts]

        # Save to file
        with open(self.conflicts_file, "w") as f:
            json.dump(all_conflicts, f, indent=2)

    def get_conflicts(self) -> list[SyncConflict]:
        """Get all tracked conflicts for current session.

        Returns:
            List of SyncConflict objects
        """
        return self._conflicts.copy()

    def clear(self) -> None:
        """Clear tracked conflicts from memory."""
        self._conflicts.clear()

    def count(self) -> int:
        """Get count of conflicts.

        Returns:
            Number of conflicts tracked
        """
        return len(self._conflicts)

    def has_conflicts(self) -> bool:
        """Check if any conflicts were tracked.

        Returns:
            True if conflicts exist, False otherwise
        """
        return len(self._conflicts) > 0

    @staticmethod
    def compare_timestamps(
        local_updated_at: str | None,
        remote_updated_at: str | None,
    ) -> str:
        """Compare two timestamps to determine which is newer.

        Args:
            local_updated_at: Local update timestamp (ISO format)
            remote_updated_at: Remote update timestamp (ISO format)

        Returns:
            "local" if local is newer, "remote" if remote is newer, "equal" if same
        """
        if local_updated_at is None and remote_updated_at is None:
            return "equal"
        if local_updated_at is None:
            return "remote"
        if remote_updated_at is None:
            return "local"

        try:
            local_dt = datetime.fromisoformat(local_updated_at.replace("Z", "+00:00"))
            remote_dt = datetime.fromisoformat(remote_updated_at.replace("Z", "+00:00"))

            if local_dt > remote_dt:
                return "local"
            elif remote_dt > local_dt:
                return "remote"
            else:
                return "equal"
        except Exception:
            return "equal"
