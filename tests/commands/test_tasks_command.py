"""Unit tests for tasks command."""

# pylint: disable=redefined-outer-name

import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.tasks_command import app
from todopro_cli.models.core import Task
from todopro_cli.services.config_service import ConfigService

runner = CliRunner()


@pytest.fixture
def config_service():
    """Fixture for ConfigService with temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("platformdirs.user_config_dir", return_value=tmpdir):
            with patch("platformdirs.user_data_dir", return_value=tmpdir):
                yield ConfigService()


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    return Task(
        id="task-123",
        content="Test task",
        description="Test description",
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
def mock_task_service():
    """Mock TaskService for testing."""
    # Create service mock
    service_mock = MagicMock()
    service_mock.list_tasks = AsyncMock()
    service_mock.get_task = AsyncMock()
    service_mock.add_task = AsyncMock()
    service_mock.update_task = AsyncMock()
    service_mock.delete_task = AsyncMock()
    service_mock.complete_task = AsyncMock()
    service_mock.bulk_complete_tasks = AsyncMock()

    strategy_mock = MagicMock()
    strategy_mock.task_repository = MagicMock()

    with (
        patch(
            "todopro_cli.commands.tasks_command.get_storage_strategy_context",
            return_value=strategy_mock,
        ),
        patch(
            "todopro_cli.commands.tasks_command.get_task_service",
            return_value=service_mock,
        ),
        patch(
            "todopro_cli.commands.tasks_command.TaskService", return_value=service_mock
        ),
    ):
        yield service_mock


class TestListCommand:
    """Tests for list command."""

    @patch("todopro_cli.commands.tasks_command.get_background_cache")
    def test_list_tasks_success(self, mock_cache, mock_task_service, mock_task):
        """Test listing tasks successfully."""
        mock_task_service.list_tasks.return_value = [mock_task]
        mock_cache.return_value.get_completing_tasks.return_value = []

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_task_service.list_tasks.assert_called_once()

    @patch("todopro_cli.commands.tasks_command.get_background_cache")
    def test_list_with_filters(self, mock_cache, mock_task_service, mock_task):
        """Test listing tasks with filters."""
        mock_task_service.list_tasks.return_value = [mock_task]
        mock_cache.return_value.get_completing_tasks.return_value = []

        result = runner.invoke(app, ["list", "--status", "active", "--priority", "1"])

        assert result.exit_code == 0
        mock_task_service.list_tasks.assert_called_once()
        call_kwargs = mock_task_service.list_tasks.call_args.kwargs
        assert call_kwargs["status"] == "active"
        assert call_kwargs["priority"] == 1


class TestGetCommand:
    """Tests for get command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_get_task_success(self, mock_resolve, mock_task_service, mock_task):
        """Test getting a task successfully."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.get_task.return_value = mock_task

        result = runner.invoke(app, ["get", "123"])

        assert result.exit_code == 0
        mock_task_service.get_task.assert_called_once()


class TestCreateCommand:
    """Tests for create command."""

    def test_create_task_minimal(self, mock_task_service, mock_task):
        """Test creating a task with minimal parameters."""
        mock_task_service.add_task.return_value = mock_task

        result = runner.invoke(app, ["create", "New task"])

        assert result.exit_code == 0
        mock_task_service.add_task.assert_called_once()
        call_kwargs = mock_task_service.add_task.call_args.kwargs
        assert call_kwargs["content"] == "New task"

    def test_create_task_with_options(self, mock_task_service, mock_task):
        """Test creating a task with all options."""
        mock_task_service.add_task.return_value = mock_task

        result = runner.invoke(
            app,
            [
                "create",
                "New task",
                "--description",
                "Task description",
                "--priority",
                "2",
                "--labels",
                "urgent,work",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_task_service.add_task.call_args.kwargs
        assert call_kwargs["content"] == "New task"
        assert call_kwargs["description"] == "Task description"
        assert call_kwargs["priority"] == 2
        assert call_kwargs["labels"] == ["urgent", "work"]


class TestUpdateCommand:
    """Tests for update command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_update_task_success(self, mock_resolve, mock_task_service, mock_task):
        """Test updating a task."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.update_task.return_value = mock_task

        result = runner.invoke(app, ["update", "123", "--content", "Updated content"])

        assert result.exit_code == 0
        mock_task_service.update_task.assert_called_once()

    def test_update_task_no_updates(self):
        """Test updating task with no parameters fails."""
        result = runner.invoke(app, ["update", "123"])

        assert result.exit_code == 1
        assert "No updates specified" in result.stdout


class TestDeleteCommand:
    """Tests for delete command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_delete_task_with_yes_flag(self, mock_resolve, mock_task_service):
        """Test deleting a task with --yes flag."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.delete_task.return_value = True

        result = runner.invoke(app, ["delete", "123", "--yes"])

        assert result.exit_code == 0
        mock_task_service.delete_task.assert_called_once()

    def test_delete_task_cancelled(self, mock_task_service):
        """Test deleting a task and cancelling."""
        result = runner.invoke(app, ["delete", "123"], input="n\n")

        assert result.exit_code == 0
        mock_task_service.delete_task.assert_not_called()


class TestReopenCommand:
    """Tests for reopen command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_reopen_task(self, mock_resolve, mock_task_service, mock_task):
        """Test reopening a completed task."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.update_task.return_value = mock_task

        result = runner.invoke(app, ["reopen", "123"])

        assert result.exit_code == 0
        mock_task_service.update_task.assert_called_once()
        call_kwargs = mock_task_service.update_task.call_args.kwargs
        assert call_kwargs["is_completed"] is False


class TestRescheduleCommand:
    """Tests for reschedule command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_reschedule_single_task(self, mock_resolve, mock_task_service, mock_task):
        """Test rescheduling a single task."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.update_task.return_value = mock_task

        result = runner.invoke(app, ["reschedule", "123", "--date", "2024-12-31"])

        assert result.exit_code == 0
        mock_task_service.update_task.assert_called_once()

    def test_reschedule_overdue_none(self, mock_task_service):
        """Test rescheduling overdue tasks when none exist."""
        mock_task_service.list_tasks.return_value = []

        result = runner.invoke(app, ["reschedule"])

        assert result.exit_code == 0
        assert "No overdue tasks" in result.stdout or "🎉" in result.stdout
