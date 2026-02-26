"""Comprehensive unit tests for todopro_cli.services.log_service.LogService.

Strategy
--------
* Redirect every file operation to *tmp_path* by patching
  ``LogService.get_log_directory`` at the class level.
* Work around a known timezone-mixing issue in the module (datetime.now(UTC)
  is compared/subtracted against naive datetimes after tzinfo stripping).
  We patch ``todopro_cli.services.log_service.datetime`` so that
  ``datetime.now(...)`` always returns a fixed, *naive* datetime, making all
  arithmetic consistent.  ``datetime.fromisoformat`` is forwarded to the real
  implementation via ``side_effect``.
* Test entries are written with "naive + Z" timestamps
  (e.g. ``"2024-01-15T12:00:00Z"``) so that the ``.replace("Z", "+00:00")``
  round-trip produces a valid ISO string, and ``.replace(tzinfo=None)``
  yields a naive datetime that is directly comparable with the patched ``now``.
"""

from __future__ import annotations

import json
from datetime import datetime as _real_datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from todopro_cli.services.log_service import LogService


# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

# Fixed "current time" used by the patched datetime.  All relative timestamps
# in test entries are calculated from this moment.
FIXED_NOW = _real_datetime(2024, 1, 15, 12, 0, 0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(dt: _real_datetime) -> str:
    """Format a naive datetime as the 'naive+Z' timestamp format used in logs."""
    return dt.isoformat() + "Z"


def _write_entry(
    log_file: Path,
    *,
    command: str = "test_cmd",
    error: str = "something failed",
    dt: _real_datetime | None = None,
    acknowledged: bool = False,
    context: dict[str, Any] | None = None,
    retries: int = 0,
) -> dict[str, Any]:
    """Write a single JSONL entry directly to *log_file* and return it."""
    if dt is None:
        dt = FIXED_NOW
    entry: dict[str, Any] = {
        "timestamp": _ts(dt),
        "command": command,
        "error": error,
        "retries": retries,
        "context": context or {},
    }
    if acknowledged:
        entry["acknowledged"] = True
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def log_dir(tmp_path: Path, mocker) -> Path:
    """Redirect LogService file I/O to a temporary directory."""
    _log_dir = tmp_path / "logs"
    _log_dir.mkdir()
    mocker.patch.object(LogService, "get_log_directory", return_value=_log_dir)
    return _log_dir


@pytest.fixture()
def log_file(log_dir: Path) -> Path:
    """Return the errors.jsonl path inside the redirected log directory."""
    return log_dir / "errors.jsonl"


@pytest.fixture()
def patched_dt(mocker):
    """Patch ``datetime`` in log_service so that ``now(...)`` is always FIXED_NOW.

    This avoids the aware-vs-naive TypeError that exists in the production code
    when ``datetime.now(UTC)`` (aware) is compared with
    ``entry_time.replace(tzinfo=None)`` (naive).
    """
    mock_dt = mocker.MagicMock(name="datetime_class")
    # Any call to datetime.now(...) returns the fixed naive datetime
    mock_dt.now.return_value = FIXED_NOW
    # Forward fromisoformat to the real implementation
    mock_dt.fromisoformat.side_effect = _real_datetime.fromisoformat
    mocker.patch("todopro_cli.services.log_service.datetime", mock_dt)
    return FIXED_NOW


# ---------------------------------------------------------------------------
# Tests: get_log_directory
# ---------------------------------------------------------------------------


class TestGetLogDirectory:
    """Test OS-appropriate path selection and directory creation."""

    def test_linux_path_contains_local_share(self, tmp_path, mocker):
        mocker.patch("platform.system", return_value="Linux")
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        result = LogService.get_log_directory()
        assert ".local" in str(result) or "share" in str(result) or "logs" in str(result)

    def test_macos_path_contains_library_logs(self, tmp_path, mocker):
        mocker.patch("platform.system", return_value="Darwin")
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        result = LogService.get_log_directory()
        assert "Library" in str(result) or "Logs" in str(result)

    def test_windows_path_contains_appdata(self, tmp_path, mocker):
        mocker.patch("platform.system", return_value="Windows")
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        result = LogService.get_log_directory()
        assert "AppData" in str(result) or "Roaming" in str(result) or "todopro" in str(result)

    def test_unknown_os_uses_fallback_path(self, tmp_path, mocker):
        mocker.patch("platform.system", return_value="FreeBSD")
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        result = LogService.get_log_directory()
        assert "todopro" in str(result) or "logs" in str(result)

    def test_directory_is_created_if_missing(self, tmp_path, mocker):
        mocker.patch("platform.system", return_value="Linux")
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        result = LogService.get_log_directory()
        assert result.is_dir()

    def test_returns_path_object(self, tmp_path, mocker):
        mocker.patch("platform.system", return_value="Linux")
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        result = LogService.get_log_directory()
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# Tests: get_error_log_path
# ---------------------------------------------------------------------------


class TestGetErrorLogPath:
    """Test path construction for the error log file."""

    def test_returns_path_object(self, log_dir):
        path = LogService.get_error_log_path()
        assert isinstance(path, Path)

    def test_filename_is_errors_jsonl(self, log_dir):
        path = LogService.get_error_log_path()
        assert path.name == "errors.jsonl"

    def test_parent_is_log_directory(self, log_dir):
        path = LogService.get_error_log_path()
        assert path.parent == log_dir


# ---------------------------------------------------------------------------
# Tests: log_error
# ---------------------------------------------------------------------------


class TestLogError:
    """Test error entry writing."""

    def test_creates_log_file(self, log_dir, log_file):
        assert not log_file.exists()
        LogService.log_error("add", "network timeout")
        assert log_file.exists()

    def test_writes_valid_json_line(self, log_dir, log_file):
        LogService.log_error("complete", "task not found")
        line = log_file.read_text(encoding="utf-8").strip()
        entry = json.loads(line)
        assert isinstance(entry, dict)

    def test_entry_contains_command(self, log_dir, log_file):
        LogService.log_error("complete", "error msg")
        entry = json.loads(log_file.read_text())
        assert entry["command"] == "complete"

    def test_entry_contains_error_message(self, log_dir, log_file):
        LogService.log_error("add", "something went wrong")
        entry = json.loads(log_file.read_text())
        assert entry["error"] == "something went wrong"

    def test_entry_contains_timestamp_key(self, log_dir, log_file):
        LogService.log_error("list", "failed")
        entry = json.loads(log_file.read_text())
        assert "timestamp" in entry
        assert isinstance(entry["timestamp"], str)
        assert len(entry["timestamp"]) > 0

    def test_entry_default_retries_is_zero(self, log_dir, log_file):
        LogService.log_error("sync", "error")
        entry = json.loads(log_file.read_text())
        assert entry["retries"] == 0

    def test_entry_with_retries(self, log_dir, log_file):
        LogService.log_error("sync", "timeout", retries=3)
        entry = json.loads(log_file.read_text())
        assert entry["retries"] == 3

    def test_entry_with_context(self, log_dir, log_file):
        ctx = {"task_id": "abc-123", "profile": "work"}
        LogService.log_error("complete", "error", context=ctx)
        entry = json.loads(log_file.read_text())
        assert entry["context"] == ctx

    def test_entry_default_context_is_empty_dict(self, log_dir, log_file):
        LogService.log_error("list", "error")
        entry = json.loads(log_file.read_text())
        assert entry["context"] == {}

    def test_multiple_calls_append_lines(self, log_dir, log_file):
        LogService.log_error("cmd1", "err1")
        LogService.log_error("cmd2", "err2")
        LogService.log_error("cmd3", "err3")
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

    def test_appended_entries_are_independent_json(self, log_dir, log_file):
        LogService.log_error("cmd1", "error one")
        LogService.log_error("cmd2", "error two")
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(line) for line in lines]
        assert entries[0]["command"] == "cmd1"
        assert entries[1]["command"] == "cmd2"


# ---------------------------------------------------------------------------
# Tests: get_recent_errors
# ---------------------------------------------------------------------------


class TestGetRecentErrors:
    """Tests for the get_recent_errors() static method."""

    def test_returns_empty_list_when_no_file(self, log_dir):
        result = LogService.get_recent_errors()
        assert result == []

    def test_returns_empty_list_for_empty_file(self, log_dir, log_file):
        log_file.write_text("", encoding="utf-8")
        result = LogService.get_recent_errors()
        assert result == []

    def test_returns_entries_from_file(self, log_dir, log_file):
        _write_entry(log_file, command="add", error="err1")
        _write_entry(log_file, command="list", error="err2")
        result = LogService.get_recent_errors()
        assert len(result) == 2

    def test_entries_are_dicts(self, log_dir, log_file):
        _write_entry(log_file)
        result = LogService.get_recent_errors()
        assert all(isinstance(e, dict) for e in result)

    def test_respects_limit(self, log_dir, log_file):
        for i in range(10):
            _write_entry(log_file, command=f"cmd{i}", error=f"err{i}")
        result = LogService.get_recent_errors(limit=3)
        assert len(result) == 3

    def test_default_limit_is_ten(self, log_dir, log_file):
        for i in range(15):
            _write_entry(log_file, command=f"cmd{i}", error=f"err{i}")
        result = LogService.get_recent_errors()
        assert len(result) == 10

    def test_returns_most_recent_first(self, log_dir, log_file):
        """Entries should be reversed (newest first) after reading."""
        _write_entry(log_file, command="first")
        _write_entry(log_file, command="second")
        _write_entry(log_file, command="third")
        result = LogService.get_recent_errors()
        # File is written top-to-bottom; after reverse the last becomes first
        assert result[0]["command"] == "third"
        assert result[-1]["command"] == "first"

    def test_skips_malformed_json_lines(self, log_dir, log_file):
        log_file.write_text(
            'not-json\n'
            '{"timestamp":"2024-01-01T00:00:00Z","command":"ok","error":"e","retries":0,"context":{}}\n'
            'also-not-json\n',
            encoding="utf-8",
        )
        result = LogService.get_recent_errors()
        assert len(result) == 1
        assert result[0]["command"] == "ok"

    def test_skips_empty_lines(self, log_dir, log_file):
        _write_entry(log_file, command="valid")
        log_file.write_text(
            log_file.read_text() + "\n\n",  # append blank lines
            encoding="utf-8",
        )
        result = LogService.get_recent_errors()
        assert len(result) == 1

    def test_since_hours_filters_old_entries(self, log_dir, log_file, patched_dt):
        """Entries older than ``since_hours`` are excluded."""
        recent_dt = FIXED_NOW - timedelta(minutes=30)   # 0.5 h ago → inside window
        old_dt = FIXED_NOW - timedelta(hours=3)          # 3 h ago   → outside window

        _write_entry(log_file, command="recent", dt=recent_dt)
        _write_entry(log_file, command="old", dt=old_dt)

        result = LogService.get_recent_errors(since_hours=1)
        commands = [e["command"] for e in result]
        assert "recent" in commands
        assert "old" not in commands

    def test_since_hours_includes_boundary_entry(self, log_dir, log_file, patched_dt):
        """An entry within the window is included."""
        inside_dt = FIXED_NOW - timedelta(minutes=59)
        _write_entry(log_file, command="inside", dt=inside_dt)
        result = LogService.get_recent_errors(since_hours=1)
        assert len(result) == 1

    def test_since_hours_none_returns_all_entries(self, log_dir, log_file):
        for i in range(5):
            _write_entry(log_file, command=f"cmd{i}")
        result = LogService.get_recent_errors(since_hours=None)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# Tests: get_unread_errors
# ---------------------------------------------------------------------------


class TestGetUnreadErrors:
    """Tests for get_unread_errors().

    ``get_unread_errors()`` calls ``get_recent_errors(since_hours=24)``
    internally, which triggers timestamp parsing and the aware/naive
    comparison.  All tests here therefore require the ``patched_dt`` fixture.
    """

    def test_returns_empty_list_when_no_file(self, log_dir, patched_dt):
        assert LogService.get_unread_errors() == []

    def test_returns_unacknowledged_entries(self, log_dir, log_file, patched_dt):
        _write_entry(log_file, command="unread1", acknowledged=False)
        _write_entry(log_file, command="unread2", acknowledged=False)
        result = LogService.get_unread_errors()
        assert len(result) == 2

    def test_excludes_acknowledged_entries(self, log_dir, log_file, patched_dt):
        _write_entry(log_file, command="acked", acknowledged=True)
        _write_entry(log_file, command="unread", acknowledged=False)
        result = LogService.get_unread_errors()
        commands = [e["command"] for e in result]
        assert "unread" in commands
        assert "acked" not in commands

    def test_returns_empty_when_all_acknowledged(self, log_dir, log_file, patched_dt):
        _write_entry(log_file, acknowledged=True)
        _write_entry(log_file, acknowledged=True)
        assert LogService.get_unread_errors() == []

    def test_entries_without_acknowledged_key_are_unread(
        self, log_dir, log_file, patched_dt
    ):
        """Entries missing the 'acknowledged' key default to unread."""
        entry = {
            "timestamp": _ts(FIXED_NOW),
            "command": "cmd",
            "error": "err",
            "retries": 0,
            "context": {},
        }
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        result = LogService.get_unread_errors()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Tests: mark_errors_as_read
# ---------------------------------------------------------------------------


class TestMarkErrorsAsRead:
    """Tests for mark_errors_as_read()."""

    def test_returns_zero_when_no_file(self, log_dir):
        assert LogService.mark_errors_as_read() == 0

    def test_marks_recent_entries_acknowledged(self, log_dir, log_file, patched_dt):
        """Entries within the last 24 hours are marked acknowledged."""
        recent_dt = FIXED_NOW - timedelta(hours=1)
        _write_entry(log_file, command="recent", dt=recent_dt, acknowledged=False)

        count = LogService.mark_errors_as_read()
        assert count >= 1

        # Verify the file now contains acknowledged=True
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(ln) for ln in lines if ln.strip()]
        recent_entries = [e for e in entries if e["command"] == "recent"]
        assert all(e.get("acknowledged") is True for e in recent_entries)

    def test_does_not_remark_already_acknowledged_entries(
        self, log_dir, log_file, patched_dt
    ):
        recent_dt = FIXED_NOW - timedelta(hours=2)
        _write_entry(log_file, dt=recent_dt, acknowledged=True)
        LogService.mark_errors_as_read()
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(ln) for ln in lines if ln.strip()]
        assert entries[0].get("acknowledged") is True

    def test_old_entries_are_not_marked(self, log_dir, log_file, patched_dt):
        """Entries older than 24 hours should NOT be acknowledged."""
        old_dt = FIXED_NOW - timedelta(hours=25)
        _write_entry(log_file, command="old", dt=old_dt, acknowledged=False)

        LogService.mark_errors_as_read()

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(ln) for ln in lines if ln.strip()]
        old_entries = [e for e in entries if e["command"] == "old"]
        assert all(not e.get("acknowledged") for e in old_entries)

    def test_returns_count_of_acknowledged_entries(
        self, log_dir, log_file, patched_dt
    ):
        recent_dt = FIXED_NOW - timedelta(hours=1)
        _write_entry(log_file, command="r1", dt=recent_dt)
        _write_entry(log_file, command="r2", dt=recent_dt)
        count = LogService.mark_errors_as_read()
        assert count == 2

    def test_rewrites_all_entries_preserving_fields(
        self, log_dir, log_file, patched_dt
    ):
        recent_dt = FIXED_NOW - timedelta(hours=1)
        ctx = {"task_id": "xyz"}
        _write_entry(log_file, command="test", error="boom", context=ctx, dt=recent_dt)

        LogService.mark_errors_as_read()

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entry = json.loads(lines[0])
        assert entry["command"] == "test"
        assert entry["error"] == "boom"
        assert entry["context"] == ctx


# ---------------------------------------------------------------------------
# Tests: clear_old_errors
# ---------------------------------------------------------------------------


class TestClearOldErrors:
    """Tests for clear_old_errors()."""

    def test_returns_zero_when_no_file(self, log_dir):
        assert LogService.clear_old_errors() == 0

    def test_removes_entries_older_than_days(self, log_dir, log_file, patched_dt):
        old_dt = FIXED_NOW - timedelta(days=31)
        recent_dt = FIXED_NOW - timedelta(days=1)
        _write_entry(log_file, command="old", dt=old_dt)
        _write_entry(log_file, command="recent", dt=recent_dt)

        removed = LogService.clear_old_errors(days=30)
        assert removed == 1

    def test_keeps_entries_within_retention_window(
        self, log_dir, log_file, patched_dt
    ):
        recent_dt = FIXED_NOW - timedelta(days=5)
        _write_entry(log_file, command="keep", dt=recent_dt)

        LogService.clear_old_errors(days=30)

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(ln) for ln in lines if ln.strip()]
        assert any(e["command"] == "keep" for e in entries)

    def test_returns_count_of_removed_entries(self, log_dir, log_file, patched_dt):
        old_dt = FIXED_NOW - timedelta(days=60)
        _write_entry(log_file, command="old1", dt=old_dt)
        _write_entry(log_file, command="old2", dt=old_dt)
        removed = LogService.clear_old_errors(days=30)
        assert removed == 2

    def test_returns_zero_when_all_entries_are_recent(
        self, log_dir, log_file, patched_dt
    ):
        recent_dt = FIXED_NOW - timedelta(days=1)
        _write_entry(log_file, dt=recent_dt)
        removed = LogService.clear_old_errors(days=30)
        assert removed == 0

    def test_custom_days_parameter(self, log_dir, log_file, patched_dt):
        """Verify the ``days`` parameter is respected."""
        old_dt = FIXED_NOW - timedelta(days=8)
        recent_dt = FIXED_NOW - timedelta(days=2)
        _write_entry(log_file, command="old7", dt=old_dt)
        _write_entry(log_file, command="recent2", dt=recent_dt)

        # With days=7: entry from 8 days ago should be removed
        removed = LogService.clear_old_errors(days=7)
        assert removed == 1

    def test_file_contains_only_kept_entries_after_clear(
        self, log_dir, log_file, patched_dt
    ):
        old_dt = FIXED_NOW - timedelta(days=40)
        recent_dt = FIXED_NOW - timedelta(days=2)
        _write_entry(log_file, command="old", dt=old_dt)
        _write_entry(log_file, command="keep", dt=recent_dt)

        LogService.clear_old_errors(days=30)

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(ln) for ln in lines if ln.strip()]
        assert len(entries) == 1
        assert entries[0]["command"] == "keep"

    def test_skips_malformed_json_lines_silently(self, log_dir, log_file, patched_dt):
        """Malformed JSON is silently discarded; valid entries are kept."""
        recent_dt = FIXED_NOW - timedelta(days=1)
        # Write one valid entry then an invalid line
        _write_entry(log_file, command="valid", dt=recent_dt)
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write("this-is-not-json\n")

        removed = LogService.clear_old_errors(days=30)
        # The bad line is silently dropped; the valid entry is kept → removed=0
        assert removed == 0
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(ln) for ln in lines if ln.strip()]
        assert entries[0]["command"] == "valid"
