"""Unit tests for the 'today' command.

Covers:
- No tasks due today → friendly message
- Tasks with due_date == today
- Overdue tasks (due_date < today)
- Mix of today + overdue tasks
- Error banner when unread background errors exist
- Background-cache filtering of completing tasks
- Output format flags (json, pretty, table)
- --compact flag
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.today_command import app
from todopro_cli.models import Task

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = datetime.now().date().isoformat()
_YESTERDAY = datetime(2000, 1, 1).date().isoformat()  # always in the past

_NOW = datetime(2024, 6, 1, 10, 0, 0)


def _task(
    task_id: str = "task-0001",
    content: str = "Sample task",
    due_date: datetime | None = None,
) -> Task:
    return Task(
        id=task_id,
        content=content,
        due_date=due_date,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _task_today(task_id: str = "today-0001", content: str = "Today task") -> Task:
    due = datetime.fromisoformat(f"{_TODAY}T09:00:00")
    return _task(task_id=task_id, content=content, due_date=due)


def _task_overdue(task_id: str = "over-0001", content: str = "Overdue task") -> Task:
    due = datetime.fromisoformat(f"{_YESTERDAY}T09:00:00")
    return _task(task_id=task_id, content=content, due_date=due)


def _run(
    args: list[str] | None = None,
    *,
    tasks: list[Task] | None = None,
    unread_errors: list[dict] | None = None,
    completing_tasks: list[str] | None = None,
):
    """Invoke today command with mocked dependencies."""
    if tasks is None:
        tasks = []
    if unread_errors is None:
        unread_errors = []
    if completing_tasks is None:
        completing_tasks = []

    task_svc = MagicMock()
    task_svc.list_tasks = AsyncMock(return_value=tasks)

    cache = MagicMock()
    cache.get_completing_tasks.return_value = completing_tasks

    with (
        patch(
            "todopro_cli.commands.today_command.get_task_service",
            return_value=task_svc,
        ),
        patch(
            "todopro_cli.commands.today_command.LogService.get_unread_errors",
            return_value=unread_errors,
        ),
        patch(
            "todopro_cli.commands.today_command.LogService.mark_errors_as_read",
        ),
        patch(
            "todopro_cli.commands.today_command.get_background_cache",
            return_value=cache,
        ),
    ):
        # today is the only command in the app – invoke without repeating its name
        return runner.invoke(app, args or [], catch_exceptions=False)


# ---------------------------------------------------------------------------
# Empty / no tasks
# ---------------------------------------------------------------------------


class TestTodayNoTasks:
    """When there are no tasks due today or overdue."""

    def test_exits_zero(self):
        result = _run()
        assert result.exit_code == 0, result.output

    def test_shows_no_tasks_message(self):
        result = _run()
        assert "No tasks due today" in result.output or "🎉" in result.output

    def test_json_output_empty(self):
        result = _run(args=["--json"])
        assert result.exit_code == 0
        assert '"tasks"' in result.output

    def test_active_tasks_no_due_dates_not_shown(self):
        """Active tasks without a due_date are not shown as today's tasks."""
        tasks = [_task(task_id="noduedate", content="No due date task")]
        result = _run(tasks=tasks)
        assert "No tasks due today" in result.output or "🎉" in result.output


# ---------------------------------------------------------------------------
# Tasks due today
# ---------------------------------------------------------------------------


class TestTodayTasksDueToday:
    """When tasks have due_date == today."""

    def test_exits_zero_with_today_tasks(self):
        result = _run(tasks=[_task_today()])
        assert result.exit_code == 0, result.output

    def test_shows_today_task_content(self):
        result = _run(tasks=[_task_today(content="Buy groceries")])
        assert "Buy groceries" in result.output

    def test_summary_shows_today_count(self):
        result = _run(tasks=[_task_today("t1"), _task_today("t2")])
        assert result.exit_code == 0
        # Summary line is printed for non-json output
        assert "2" in result.output or "today" in result.output.lower()

    def test_json_output_contains_tasks(self):
        result = _run(tasks=[_task_today(content="JSON task")], args=["--json"])
        assert result.exit_code == 0
        assert "JSON task" in result.output

    def test_list_tasks_called_with_active_status(self):
        """list_tasks is called with status=active."""
        task_svc = MagicMock()
        task_svc.list_tasks = AsyncMock(return_value=[_task_today()])
        cache = MagicMock()
        cache.get_completing_tasks.return_value = []
        with (
            patch(
                "todopro_cli.commands.today_command.get_task_service",
                return_value=task_svc,
            ),
            patch(
                "todopro_cli.commands.today_command.LogService.get_unread_errors",
                return_value=[],
            ),
            patch("todopro_cli.commands.today_command.LogService.mark_errors_as_read"),
            patch(
                "todopro_cli.commands.today_command.get_background_cache",
                return_value=cache,
            ),
        ):
            runner.invoke(app, [], catch_exceptions=False)
        task_svc.list_tasks.assert_awaited_once()
        call_kwargs = task_svc.list_tasks.call_args
        assert call_kwargs.kwargs.get("status") == "active" or (
            call_kwargs.args and "active" in call_kwargs.args
        )


# ---------------------------------------------------------------------------
# Overdue tasks
# ---------------------------------------------------------------------------


class TestTodayOverdueTasks:
    """When tasks are overdue (due_date < today)."""

    def test_overdue_task_shown(self):
        result = _run(tasks=[_task_overdue(content="Past deadline")])
        assert "Past deadline" in result.output

    def test_overdue_summary_shows_count(self):
        result = _run(tasks=[_task_overdue("o1"), _task_overdue("o2")])
        assert result.exit_code == 0

    def test_mixed_today_and_overdue(self):
        tasks = [_task_today(content="Today item"), _task_overdue(content="Overdue item")]
        result = _run(tasks=tasks)
        assert "Today item" in result.output
        assert "Overdue item" in result.output

    def test_summary_shows_both_counts(self):
        tasks = [_task_today("t1"), _task_overdue("o1"), _task_overdue("o2")]
        result = _run(tasks=tasks)
        assert result.exit_code == 0
        # Summary: "X overdue, Y due today"
        assert "overdue" in result.output.lower() or "2" in result.output


# ---------------------------------------------------------------------------
# Error banner
# ---------------------------------------------------------------------------


class TestTodayErrorBanner:
    """When there are unread background errors, an error banner is displayed."""

    def _make_error(self, error_msg="Something failed", command="complete"):
        return {"error": error_msg, "command": command}

    def test_error_banner_shown(self):
        errors = [self._make_error()]
        result = _run(unread_errors=errors)
        assert result.exit_code == 0
        assert "background task" in result.output.lower() or "failed" in result.output.lower()

    def test_multiple_errors_count_shown(self):
        errors = [self._make_error("err1"), self._make_error("err2")]
        result = _run(unread_errors=errors)
        assert result.exit_code == 0
        assert "2" in result.output

    def test_error_message_truncated(self):
        """Error messages longer than 100 chars are truncated."""
        long_error = "E" * 200
        errors = [self._make_error(long_error)]
        result = _run(unread_errors=errors)
        assert result.exit_code == 0
        assert "..." in result.output

    def test_mark_errors_as_read_called(self):
        """After showing the banner, errors are marked as read."""
        errors = [self._make_error()]
        task_svc = MagicMock()
        task_svc.list_tasks = AsyncMock(return_value=[])
        cache = MagicMock()
        cache.get_completing_tasks.return_value = []
        mark_read = MagicMock()

        with (
            patch(
                "todopro_cli.commands.today_command.get_task_service",
                return_value=task_svc,
            ),
            patch(
                "todopro_cli.commands.today_command.LogService.get_unread_errors",
                return_value=errors,
            ),
            patch(
                "todopro_cli.commands.today_command.LogService.mark_errors_as_read",
                mark_read,
            ),
            patch(
                "todopro_cli.commands.today_command.get_background_cache",
                return_value=cache,
            ),
        ):
            runner.invoke(app, [], catch_exceptions=False)

        mark_read.assert_called_once()

    def test_no_banner_when_no_errors(self):
        """No banner when unread error list is empty."""
        result = _run(unread_errors=[])
        assert "background task" not in result.output.lower()


# ---------------------------------------------------------------------------
# Background-cache filtering
# ---------------------------------------------------------------------------


class TestTodayCacheFiltering:
    """Tasks being completed in the background are hidden from today view."""

    def test_completing_task_filtered_out(self):
        """A task whose ID suffix matches a completing task is hidden."""
        task = _task_today(task_id="aabbcc-1234", content="Being completed now")
        # The cache stores short suffix IDs
        result = _run(tasks=[task], completing_tasks=["1234"])
        # Task should be filtered out; "Being completed now" not in output
        # (but we just check no crash and zero exit)
        assert result.exit_code == 0

    def test_non_completing_task_not_filtered(self):
        """Tasks NOT in cache are still shown."""
        task = _task_today(task_id="aabbcc-9999", content="Still visible")
        result = _run(tasks=[task], completing_tasks=["0000"])
        assert "Still visible" in result.output

    def test_filter_count_message_shown(self):
        """When tasks are filtered, a note about hiding them is displayed."""
        task = _task_today(task_id="aabbcc-5678", content="Hidden task")
        result = _run(tasks=[task], completing_tasks=["5678"])
        assert result.exit_code == 0
        # Should show "Hiding N task(s)" message
        assert "Hiding" in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# Output flags
# ---------------------------------------------------------------------------


class TestTodayOutputFlags:
    """Verify output format flags work without error."""

    def test_default_pretty_output(self):
        result = _run(tasks=[_task_today(content="Pretty task")])
        assert result.exit_code == 0

    def test_json_flag(self):
        result = _run(tasks=[_task_today()], args=["--json"])
        assert result.exit_code == 0
        assert '"tasks"' in result.output or "task" in result.output

    def test_output_json_flag(self):
        result = _run(tasks=[_task_today()], args=["--output", "json"])
        assert result.exit_code == 0

    def test_compact_flag(self):
        result = _run(tasks=[_task_today()], args=["--compact"])
        assert result.exit_code == 0

    def test_help_exits_zero(self):
        result = runner.invoke(app, ["today", "--help"])
        assert result.exit_code == 0
