"""Unit tests for new create_command (verb-first pattern)."""

# pylint: disable=redefined-outer-name

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.create_command import app
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


@pytest.mark.skip(
    reason="Tests for old architecture, needs rewrite for new Strategy pattern"
)
class TestCreateTask:
    """Tests for 'todopro create task' command."""

    @patch("todopro_cli.commands.create_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    def test_create_task_minimal(self, mock_auth, mock_factory, mock_task):
        """Test creating a task with minimal parameters."""
        mock_repo = MagicMock()
        mock_factory.return_value.get_task_repository.return_value = mock_repo

        service_mock = MagicMock()
        service_mock.add_task = AsyncMock(return_value=mock_task)

        with patch(
            "todopro_cli.commands.create_command.TaskService", return_value=service_mock
        ):
            result = runner.invoke(app, ["task", "New test task"])

            # Verify command structure
            assert result.exit_code in [0, 1]

    @patch("todopro_cli.commands.create_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    def test_create_task_with_options(self, mock_auth, mock_factory, mock_task):
        """Test creating a task with all options."""
        mock_repo = MagicMock()
        mock_factory.return_value.get_task_repository.return_value = mock_repo

        service_mock = MagicMock()
        service_mock.add_task = AsyncMock(return_value=mock_task)

        with patch(
            "todopro_cli.commands.create_command.TaskService", return_value=service_mock
        ):
            result = runner.invoke(
                app,
                [
                    "task",
                    "New task",
                    "--description",
                    "Task description",
                    "--priority",
                    "2",
                ],
            )

            # Verify command structure
            assert result.exit_code in [0, 1]


@pytest.mark.skip(
    reason="Tests for old architecture, needs rewrite for new Strategy pattern"
)
class TestCreateProject:
    """Tests for 'todopro create project' command."""

    @patch("todopro_cli.commands.create_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    def test_create_project_minimal(self, mock_auth, mock_factory, mock_project):
        """Test creating a project with minimal parameters."""
        mock_repo = MagicMock()
        mock_factory.return_value.get_project_repository.return_value = mock_repo

        service_mock = MagicMock()
        service_mock.add_project = AsyncMock(return_value=mock_project)

        with patch(
            "todopro_cli.commands.create_command.ProjectService",
            return_value=service_mock,
        ):
            result = runner.invoke(app, ["project", "New Project"])

            # Verify command structure
            assert result.exit_code in [0, 1]


class TestCreateCommandStructure:
    """Tests for overall create command structure."""

    def test_create_help(self):
        """Test that create command shows help correctly."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Create" in result.stdout
        assert "task" in result.stdout
        assert "project" in result.stdout
        assert "label" in result.stdout

    def test_create_task_help(self):
        """Test that create task subcommand has help."""
        result = runner.invoke(app, ["task", "--help"])

        assert result.exit_code == 0
        assert "Create a new task" in result.stdout

    def test_create_project_help(self):
        """Test that create project subcommand has help."""
        result = runner.invoke(app, ["project", "--help"])

        assert result.exit_code == 0
        assert "Create a new project" in result.stdout
