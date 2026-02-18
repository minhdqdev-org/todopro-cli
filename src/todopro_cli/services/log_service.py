"""Service for handling application logs, especially error logs."""

import json
import platform
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class LogService:
    """Service for handling application logs, especially error logs."""

    @staticmethod
    def get_log_directory() -> Path:
        """Get OS-appropriate log directory."""
        system = platform.system()

        if system == "Linux":
            # Linux: ~/.local/share/todopro/logs/
            base_dir = Path.home() / ".local" / "share" / "todopro" / "logs"
        elif system == "Darwin":
            # macOS: ~/Library/Logs/todopro/
            base_dir = Path.home() / "Library" / "Logs" / "todopro"
        elif system == "Windows":
            # Windows: %APPDATA%/todopro/logs/
            appdata = Path.home() / "AppData" / "Roaming"
            base_dir = appdata / "todopro" / "logs"
        else:
            # Fallback
            base_dir = Path.home() / ".todopro" / "logs"

        # Create directory if it doesn't exist
        base_dir.mkdir(parents=True, exist_ok=True)

        return base_dir

    @staticmethod
    def get_error_log_path() -> Path:
        """Get path to error log file."""
        log_dir = LogService.get_log_directory()
        return log_dir / "errors.jsonl"

    @staticmethod
    def get_recent_errors(
        limit: int = 10, since_hours: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Get recent errors from the log file.

        Args:
            limit: Maximum number of errors to return
            since_hours: Only return errors from the last N hours

        Returns:
            List of error entries
        """
        log_file = LogService.get_error_log_path()

        if not log_file.exists():
            return []

        errors = []
        cutoff_time = None

        if since_hours:
            cutoff_time = datetime.now(UTC) - timedelta(hours=since_hours)

        with open(log_file, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Filter by time if specified
                    if cutoff_time:
                        entry_time = datetime.fromisoformat(
                            entry["timestamp"].replace("Z", "+00:00")
                        )
                        if entry_time.replace(tzinfo=None) < cutoff_time:
                            continue

                    errors.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue

        # Return most recent errors first
        errors.reverse()
        return errors[:limit]

    @staticmethod
    def get_unread_errors() -> list[dict[str, Any]]:
        """
        Get errors that haven't been acknowledged.

        Returns errors from the last 24 hours that don't have an 'acknowledged' flag.
        """
        errors = LogService.get_recent_errors(limit=50, since_hours=24)
        return [e for e in errors if not e.get("acknowledged", False)]

    @staticmethod
    def log_error(
        command: str,
        error: str,
        context: dict[str, Any] | None = None,
        retries: int = 0,
    ) -> None:
        """
        Log an error to the error log file.

        Args:
            command: The command that failed (e.g., "complete", "add")
            error: The error message
            context: Additional context (task_id, profile, etc.)
            retries: Number of retries attempted
        """
        log_file = LogService.get_error_log_path()

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "command": command,
            "error": error,
            "retries": retries,
            "context": context or {},
        }

        # Append to JSONL file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    @staticmethod
    def mark_errors_as_read() -> int:
        """
        Mark all current errors as read by setting acknowledged flag.

        Returns:
            Number of errors marked as read
        """
        log_file = LogService.get_error_log_path()

        if not log_file.exists():
            return 0

        # Read all entries
        entries = []
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Only mark recent errors (last 24 hours)
                    entry_time = datetime.fromisoformat(
                        entry["timestamp"].replace("Z", "+00:00")
                    )
                    age_hours = (
                        datetime.now(UTC) - entry_time.replace(tzinfo=None)
                    ).total_seconds() / 3600

                    if age_hours <= 24 and not entry.get("acknowledged"):
                        entry["acknowledged"] = True

                    entries.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue

        # Write back
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        return len([e for e in entries if e.get("acknowledged")])

    @staticmethod
    def clear_old_errors(days: int = 30) -> int:
        """
        Remove errors older than specified days.

        Args:
            days: Remove errors older than this many days

        Returns:
            Number of errors removed
        """
        log_file = LogService.get_error_log_path()

        if not log_file.exists():
            return 0

        cutoff_time = datetime.now(UTC) - timedelta(days=days)

        # Read and filter entries
        kept_entries = []
        removed_count = 0

        with open(log_file, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(
                        entry["timestamp"].replace("Z", "+00:00")
                    )

                    if entry_time.replace(tzinfo=None) >= cutoff_time:
                        kept_entries.append(entry)
                    else:
                        removed_count += 1
                except (json.JSONDecodeError, KeyError):
                    continue

        # Write back kept entries
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in kept_entries:
                f.write(json.dumps(entry) + "\n")

        return removed_count
