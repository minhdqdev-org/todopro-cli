"""Unit tests for reopen_command (reopen completed tasks).

Note: this app compiles to a single TyperCommand named 'reopen', so we
invoke it WITHOUT the subcommand name prefix (e.g. ``["task-001"]``).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.reopen_command import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(content="Fix the login bug", task_id="task-001"):
    task = MagicMock()
    task.id = task_id
    task.content = content
    return task


def _invoke_reopen(task_id_arg, task=None, resolved_id=None):
    """Invoke the reopen command with mocked services.

    ``task_id_arg`` is the raw CLI string passed as TASK_ID.
    """
    mock_task = task or _make_task()
    rid = resolved_id or mock_task.id

    mock_service = MagicMock()
    mock_service.reopen_task = AsyncMock(return_value=mock_task)

    with patch(
        "todopro_cli.commands.reopen_command.get_task_service",
        return_value=mock_service,
    ):
        with patch(
            "todopro_cli.commands.reopen_command.resolve_task_id",
            new_callable=AsyncMock,
            return_value=rid,
        ):
            return runner.invoke(app, [task_id_arg])


# ---------------------------------------------------------------------------
# reopen task tests
# ---------------------------------------------------------------------------


class TestReopenTask:
    """Tests for the reopen task command."""

    def test_reopen_task_success(self):
        result = _invoke_reopen("task-001")
        assert result.exit_code == 0

    def test_reopen_task_shows_reopened_message(self):
        result = _invoke_reopen("task-001")
        assert "Reopened" in result.output or "reopened" in result.output.lower()

    def test_reopen_task_shows_content(self):
        task = _make_task("Write unit tests", "task-099")
        result = _invoke_reopen("task-099", task=task)
        assert result.exit_code == 0
        assert "Write unit tests" in result.output

    def test_reopen_task_truncates_long_content(self):
        long_content = "A" * 80
        task = _make_task(long_content, "task-long")
        result = _invoke_reopen("task-long", task=task)
        assert result.exit_code == 0
        # Content should be truncated to ≤60 chars visible + "..."
        assert "..." in result.output

    def test_reopen_task_content_exactly_60_chars_not_truncated(self):
        content_60 = "B" * 60
        task = _make_task(content_60, "task-60")
        result = _invoke_reopen("task-60", task=task)
        assert result.exit_code == 0
        assert "..." not in result.output

    def test_reopen_task_content_none_shows_placeholder(self):
        task = _make_task(None, "task-none")
        task.content = None
        result = _invoke_reopen("task-none", task=task)
        assert result.exit_code == 0
        assert "No title" in result.output

    def test_reopen_task_calls_reopen_task_service(self):
        mock_task = _make_task()
        mock_service = MagicMock()
        mock_service.reopen_task = AsyncMock(return_value=mock_task)

        with patch(
            "todopro_cli.commands.reopen_command.get_task_service",
            return_value=mock_service,
        ):
            with patch(
                "todopro_cli.commands.reopen_command.resolve_task_id",
                new_callable=AsyncMock,
                return_value="task-resolved",
            ):
                runner.invoke(app, ["task-001"])
        mock_service.reopen_task.assert_awaited_once_with("task-resolved")

    def test_reopen_task_resolves_id(self):
        mock_task = _make_task()
        mock_service = MagicMock()
        mock_service.reopen_task = AsyncMock(return_value=mock_task)
        resolve_mock = AsyncMock(return_value="task-resolved-uuid")

        with patch(
            "todopro_cli.commands.reopen_command.get_task_service",
            return_value=mock_service,
        ):
            with patch(
                "todopro_cli.commands.reopen_command.resolve_task_id",
                resolve_mock,
            ):
                runner.invoke(app, ["task-short"])
        resolve_mock.assert_awaited_once_with(mock_service, "task-short")

    def test_reopen_task_service_error_exits_nonzero(self):
        mock_service = MagicMock()
        mock_service.reopen_task = AsyncMock(side_effect=Exception("Task not found"))

        with patch(
            "todopro_cli.commands.reopen_command.get_task_service",
            return_value=mock_service,
        ):
            with patch(
                "todopro_cli.commands.reopen_command.resolve_task_id",
                new_callable=AsyncMock,
                return_value="task-001",
            ):
                result = runner.invoke(app, ["task-001"])
        assert result.exit_code != 0

    def test_reopen_task_missing_id_exits_nonzero(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0

    def test_reopen_task_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "TASK_ID" in result.output or "task" in result.output.lower()


# ---------------------------------------------------------------------------
# CLI structure
# ---------------------------------------------------------------------------


class TestReopenCommandStructure:
    """Tests for overall reopen command structure."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_app_accepts_task_id(self):
        """Verify TASK_ID argument is listed in help."""
        result = runner.invoke(app, ["--help"])
        assert "TASK_ID" in result.output or "task" in result.output.lower()
