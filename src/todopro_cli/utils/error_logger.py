"""Error logging utilities for TodoPro CLI."""

import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def get_error_log_path() -> Path:
    """Get path to error log file."""
    log_dir = get_log_directory()
    return log_dir / "errors.jsonl"


def log_error(
    command: str,
    error: str,
    context: Optional[Dict[str, Any]] = None,
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
    log_file = get_error_log_path()
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "command": command,
        "error": error,
        "retries": retries,
        "context": context or {},
    }
    
    # Append to JSONL file
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        # Silently fail if we can't write to log file
        pass


def get_recent_errors(limit: int = 10, since_hours: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get recent errors from the log file.
    
    Args:
        limit: Maximum number of errors to return
        since_hours: Only return errors from the last N hours
        
    Returns:
        List of error entries
    """
    log_file = get_error_log_path()
    
    if not log_file.exists():
        return []
    
    errors = []
    cutoff_time = None
    
    if since_hours:
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=since_hours)
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # Filter by time if specified
                    if cutoff_time:
                        entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                        if entry_time.replace(tzinfo=None) < cutoff_time:
                            continue
                    
                    errors.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Return most recent errors first
        errors.reverse()
        return errors[:limit]
    
    except Exception:
        return []


def get_unread_errors() -> List[Dict[str, Any]]:
    """
    Get errors that haven't been acknowledged.
    
    Returns errors from the last 24 hours that don't have an 'acknowledged' flag.
    """
    errors = get_recent_errors(limit=50, since_hours=24)
    return [e for e in errors if not e.get("acknowledged", False)]


def mark_errors_as_read() -> int:
    """
    Mark all current errors as read by setting acknowledged flag.
    
    Returns:
        Number of errors marked as read
    """
    log_file = get_error_log_path()
    
    if not log_file.exists():
        return 0
    
    try:
        # Read all entries
        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Only mark recent errors (last 24 hours)
                    entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                    age_hours = (datetime.utcnow() - entry_time.replace(tzinfo=None)).total_seconds() / 3600
                    
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
    
    except Exception:
        return 0


def clear_old_errors(days: int = 30) -> int:
    """
    Remove errors older than specified days.
    
    Args:
        days: Remove errors older than this many days
        
    Returns:
        Number of errors removed
    """
    log_file = get_error_log_path()
    
    if not log_file.exists():
        return 0
    
    try:
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Read and filter entries
        kept_entries = []
        removed_count = 0
        
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                    
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
    
    except Exception:
        return 0
