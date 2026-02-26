"""Unit tests for the top-level `tp task <task_id>` command."""

# pylint: disable=redefined-outer-name

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.task_command import app
from todopro_cli.models import Task

runner = CliRunner()


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    return Task(
        id="task-abc123",
        content="Write unit tests",
        description="Cover the new task command",
        project_id=None,
        due_date=None,
        priority=1,
        is_completed=False,
        labels=[],
        contexts=[],
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def mock_task_service(mock_task):
    """Patch TaskService and strategy context for all task_command tests."""
    service_mock = MagicMock()
    service_mock.get_task = AsyncMock(return_value=mock_task)

    strategy_mock = MagicMock()
    strategy_mock.task_repository = MagicMock()

    with (
        patch(
            "todopro_cli.commands.task_command.get_storage_strategy_context",
            return_value=strategy_mock,
        ),
        patch(
            "todopro_cli.commands.task_command.TaskService",
            return_value=service_mock,
        ),
        patch(
            "todopro_cli.commands.decorators.get_config_service",
            return_value=MagicMock(
                config=MagicMock(
                    get_current_context=MagicMock(return_value=MagicMock(type="local"))
                )
            ),
        ),
    ):
        yield service_mock


class TestTaskCommandHelp:
    """Structural tests — no network/auth needed."""

    def test_help_exits_zero(self):
        """--help should succeed."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_contains_description(self):
        """Help text should describe the command."""
        result = runner.invoke(app, ["--help"])
        assert "Get task details" in result.stdout

    def test_help_mentions_id_argument(self):
        """Help text should mention the task_id argument."""
        result = runner.invoke(app, ["--help"])
        assert "task_id" in result.stdout.lower() or "TASK_ID" in result.stdout

    def test_missing_task_id_exits_nonzero(self):
        """Invoking without a task_id should exit with an error."""
        result = runner.invoke(app, [])
        assert result.exit_code != 0


class TestTaskCommandSuccess:
    """Functional tests for the happy path."""

    @patch("todopro_cli.commands.task_command.resolve_task_id")
    def test_get_task_by_suffix(self, mock_resolve, mock_task_service, mock_task):
        """tp task <suffix> should resolve and display the task."""
        mock_resolve.return_value = AsyncMock(return_value="task-abc123")()

        result = runner.invoke(app, ["abc123"])

        assert result.exit_code == 0
        mock_task_service.get_task.assert_called_once()

    @patch("todopro_cli.commands.task_command.resolve_task_id")
    def test_get_task_by_full_id(self, mock_resolve, mock_task_service, mock_task):
        """tp task <full-id> should work with a full UUID-style ID."""
        mock_resolve.return_value = AsyncMock(return_value="task-abc123")()

        result = runner.invoke(app, ["task-abc123"])

        assert result.exit_code == 0

    @patch("todopro_cli.commands.task_command.resolve_task_id")
    def test_output_json_flag(self, mock_resolve, mock_task_service, mock_task):
        """tp task <id> --output json should pass json format."""
        mock_resolve.return_value = AsyncMock(return_value="task-abc123")()

        result = runner.invoke(app, ["abc123", "--output", "json"])

        assert result.exit_code == 0
