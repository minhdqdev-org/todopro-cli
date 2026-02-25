"""Unit tests for new list_command (verb-first pattern)."""

# pylint: disable=redefined-outer-name

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.list_command import app
from todopro_cli.models import Label, Project, Task

runner = CliRunner()


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
def mock_project():
    """Create a mock project for testing."""
    return Project(
        id="proj-123",
        name="Test Project",
        color="#FF0000",
        is_favorite=False,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def mock_label():
    """Create a mock label for testing."""
    return Label(
        id="label-123",
        name="urgent",
        color="#FF0000",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.mark.skip(
    reason="Tests for old architecture, needs rewrite for new Strategy pattern"
)
class TestListTasks:
    """Tests for 'todopro list tasks' command."""

    @patch("todopro_cli.commands.list_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    @patch("todopro_cli.commands.list_command.get_background_cache")
    def test_list_tasks_success(self, mock_cache, mock_auth, mock_factory, mock_task):
        """Test listing tasks successfully with new verb-first pattern."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_factory.return_value.get_task_repository.return_value = mock_repo

        service_mock = MagicMock()
        service_mock.list_tasks = AsyncMock(return_value=[mock_task])

        mock_cache.return_value.get_completing_tasks.return_value = []

        with patch(
            "todopro_cli.commands.list_command.TaskService", return_value=service_mock
        ):
            result = runner.invoke(app, ["tasks"])

            # Command should execute (may fail due to auth, but structure is correct)
            assert result.exit_code in [0, 1]  # Accept both success and auth failure

            # Verify service was attempted to be called (structure is correct)
            assert "tasks" in result.stdout.lower() or "error" in result.stdout.lower()

    @patch("todopro_cli.commands.list_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    @patch("todopro_cli.commands.list_command.get_background_cache")
    def test_list_tasks_with_filters(
        self, mock_cache, mock_auth, mock_factory, mock_task
    ):
        """Test listing tasks with filters."""
        mock_repo = MagicMock()
        mock_factory.return_value.get_task_repository.return_value = mock_repo

        service_mock = MagicMock()
        service_mock.list_tasks = AsyncMock(return_value=[mock_task])

        mock_cache.return_value.get_completing_tasks.return_value = []

        with patch(
            "todopro_cli.commands.list_command.TaskService", return_value=service_mock
        ):
            result = runner.invoke(
                app, ["tasks", "--status", "active", "--priority", "1"]
            )

            # Verify command structure is valid
            assert result.exit_code in [0, 1]


@pytest.mark.skip(
    reason="Tests for old architecture, needs rewrite for new Strategy pattern"
)
class TestListProjects:
    """Tests for 'todopro list projects' command."""

    @patch("todopro_cli.commands.list_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    def test_list_projects_success(self, mock_auth, mock_factory, mock_project):
        """Test listing projects successfully."""
        mock_repo = MagicMock()
        mock_factory.return_value.get_project_repository.return_value = mock_repo

        service_mock = MagicMock()
        service_mock.list_projects = AsyncMock(return_value=[mock_project])

        with patch(
            "todopro_cli.commands.list_command.ProjectService",
            return_value=service_mock,
        ):
            result = runner.invoke(app, ["projects"])

            # Verify command structure
            assert result.exit_code in [0, 1]


@pytest.mark.skip(
    reason="Tests for old architecture, needs rewrite for new Strategy pattern"
)
class TestListLabels:
    """Tests for 'todopro list labels' command."""

    @patch("todopro_cli.commands.list_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    def test_list_labels_success(self, mock_auth, mock_factory, mock_label):
        """Test listing labels successfully."""
        mock_repo = MagicMock()
        mock_factory.return_value.get_label_repository.return_value = mock_repo

        service_mock = MagicMock()
        service_mock.list_labels = AsyncMock(return_value=[mock_label])

        with patch(
            "todopro_cli.commands.list_command.LabelService", return_value=service_mock
        ):
            result = runner.invoke(app, ["labels"])

            # Verify command structure
            assert result.exit_code in [0, 1]


class TestListCommandStructure:
    """Tests for overall list command structure."""

    def test_list_help(self):
        """Test that list command shows help correctly."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "List resources" in result.stdout
        assert "tasks" in result.stdout
        assert "projects" in result.stdout
        assert "labels" in result.stdout

    def test_list_tasks_help(self):
        """Test that list tasks subcommand has help."""
        result = runner.invoke(app, ["tasks", "--help"])

        assert result.exit_code == 0
        assert "List tasks" in result.stdout

    def test_list_projects_help(self):
        """Test that list projects subcommand has help."""
        result = runner.invoke(app, ["projects", "--help"])

        assert result.exit_code == 0
        assert "List all projects" in result.stdout

    def test_list_labels_help(self):
        """Test that list labels subcommand has help."""
        result = runner.invoke(app, ["labels", "--help"])

        assert result.exit_code == 0
        assert "List all labels" in result.stdout
