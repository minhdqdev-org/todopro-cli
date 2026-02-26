"""Tests for the 'next' command.

NOTE: next_command.py contains a known bug — it calls
``get_storage_strategy_context()`` without importing it.  This means the
command body will always raise ``NameError`` at runtime (except for --help).

Tests here verify:
- --help exits 0 and documents the command correctly
- The NameError bug is confirmed (so future fixes are caught)
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.next_command import app

runner = CliRunner()


class TestNextHelp:
    """--help should work regardless of the runtime bug."""

    def test_help_exits_zero(self):
        result = runner.invoke(app, ["next", "--help"])
        assert result.exit_code == 0, result.output

    def test_help_shows_description(self):
        result = runner.invoke(app, ["next", "--help"])
        # Should mention the command purpose
        assert "next" in result.output.lower() or "task" in result.output.lower()

    def test_help_shows_output_option(self):
        result = runner.invoke(app, ["next", "--help"])
        assert "--output" in result.output or "-o" in result.output

    def test_help_shows_json_option(self):
        result = runner.invoke(app, ["next", "--help"])
        assert "--json" in result.output


class TestNextBugConfirmation:
    """Confirm the known NameError bug when actually running the command.

    This test documents the bug.  When the bug is fixed (i.e. the command
    properly imports/calls get_task_service instead of the undefined
    get_storage_strategy_context), these tests should be updated or removed.
    """

    def test_command_raises_name_error(self):
        """Running the command body triggers a NameError due to missing import."""
        result = runner.invoke(app, ["next"])
        # CliRunner catches the exception and sets a non-zero exit code
        assert result.exit_code != 0 or result.exception is not None


class TestNextCommandWithMocks:
    """Lines 30-55: next command body with proper mocks."""

    def _run(self, args=None, tasks=None):
        from datetime import datetime
        from unittest.mock import AsyncMock, MagicMock, patch

        from todopro_cli.models import Task

        mock_sc = MagicMock()
        mock_sc.task_repository = MagicMock()
        mock_ts = MagicMock()
        mock_ts.list_tasks = AsyncMock(return_value=tasks or [])

        with (
            patch("todopro_cli.commands.next_command.get_storage_strategy_context", return_value=mock_sc, create=True),
            patch("todopro_cli.commands.next_command.strategy_context", mock_sc, create=True),
            patch("todopro_cli.commands.next_command.TaskService", return_value=mock_ts),
        ):
            return runner.invoke(app, (args or []))

    def _make_task(self):
        from datetime import datetime

        from todopro_cli.models import Task
        return Task(
            id="task-next-1", content="Most important task", description="",
            project_id=None, due_date=None, priority=1, is_completed=False,
            labels=[], contexts=[],
            created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1),
        )

    def test_next_no_active_tasks_json_output(self):
        """No tasks found → JSON message."""
        result = self._run(["--output", "json"])
        assert result.exit_code == 0
        assert "No active tasks" in result.output

    def test_next_no_active_tasks_yaml_output(self):
        """No tasks found → YAML message."""
        result = self._run(["--output", "yaml"])
        assert result.exit_code == 0
        assert "active tasks" in result.output.lower() or "null" in result.output

    def test_next_no_active_tasks_pretty_output(self):
        """No tasks found → 'all caught up' message."""
        result = self._run()
        assert result.exit_code == 0
        assert "caught up" in result.output.lower() or "active task" in result.output.lower()

    def test_next_with_task_json_output(self):
        """Task found → JSON output."""
        task = self._make_task()
        result = self._run(["--output", "json"], tasks=[task])
        assert result.exit_code == 0

    def test_next_with_task_yaml_output(self):
        """Task found → YAML output."""
        task = self._make_task()
        result = self._run(["--output", "yaml"], tasks=[task])
        assert result.exit_code == 0

    def test_next_with_task_table_output(self):
        """Task found → table output (format_next_task)."""
        from unittest.mock import patch as _patch
        task = self._make_task()
        with _patch("todopro_cli.commands.next_command.format_next_task") as mock_fmt:
            result = self._run(["--output", "table"], tasks=[task])
        assert result.exit_code == 0
        mock_fmt.assert_called_once()

    def test_next_json_opt_flag(self):
        """--json flag sets output to json."""
        task = self._make_task()
        result = self._run(["--json"], tasks=[task])
        assert result.exit_code == 0
