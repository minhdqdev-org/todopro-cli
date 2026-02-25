"""Unit tests for skip_command (skip a recurring task instance)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.skip_command import app

runner = CliRunner()


class TestSkipCommand:
    """Tests for 'todopro skip <task-id>'."""

    def test_skip_help(self):
        """skip --help should describe the command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "recurring" in result.stdout.lower() or "skip" in result.stdout.lower()

    def test_skip_task_success(self):
        """skip should call TasksAPI.skip_task and show success."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        skip_result = {"id": "task-abc", "next_due": "2025-07-01"}
        mock_api = MagicMock()
        mock_api.skip_task = AsyncMock(return_value=skip_result)
        with patch(
            "todopro_cli.commands.skip_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.skip_command.TasksAPI", return_value=mock_api
            ):
                result = runner.invoke(app, ["task-abc"])
        assert result.exit_code == 0
        mock_api.skip_task.assert_awaited_once_with("task-abc")
        assert "task-abc" in result.stdout

    def test_skip_task_calls_close(self):
        """skip should always close the API client."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.skip_task = AsyncMock(return_value={})
        with patch(
            "todopro_cli.commands.skip_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.skip_command.TasksAPI", return_value=mock_api
            ):
                runner.invoke(app, ["task-xyz"])
        mock_client.close.assert_awaited_once()

    def test_skip_task_no_result_body(self):
        """skip should succeed even if the API returns an empty body."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.skip_task = AsyncMock(return_value=None)
        with patch(
            "todopro_cli.commands.skip_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.skip_command.TasksAPI", return_value=mock_api
            ):
                result = runner.invoke(app, ["task-no-body"])
        assert result.exit_code == 0

    def test_skip_requires_task_id(self):
        """skip without arguments should exit non-zero."""
        result = runner.invoke(app, [])
        assert result.exit_code != 0
