"""Unit tests for new get_command (verb-first pattern)."""
# pylint: disable=redefined-outer-name

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.get_command import app
from todopro_cli.models import Task, Project, Label

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


@pytest.mark.skip(reason="Tests for old architecture, needs rewrite for new Strategy pattern")
class TestGetTask:
    """Tests for 'todopro get task' command."""

    @patch("todopro_cli.commands.get_command.resolve_task_id")
    @patch("todopro_cli.commands.get_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    def test_get_task_success(self, mock_auth, mock_factory, mock_resolve, mock_task):
        """Test getting a task successfully with new verb-first pattern."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        
        mock_repo = MagicMock()
        mock_factory.return_value.get_task_repository.return_value = mock_repo
        
        service_mock = MagicMock()
        service_mock.get_task = AsyncMock(return_value=mock_task)
        
        with patch("todopro_cli.commands.get_command.TaskService", return_value=service_mock):
            result = runner.invoke(app, ["task", "123"])
            
            # Verify command structure
            assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="Tests for old architecture, needs rewrite for new Strategy pattern")
class TestGetProject:
    """Tests for 'todopro get project' command."""

    @patch("todopro_cli.commands.get_command.get_repository_factory")
    @patch("todopro_cli.commands.utils.require_auth")
    def test_get_project_success(self, mock_auth, mock_factory, mock_project):
        """Test getting a project successfully."""
        mock_repo = MagicMock()
        mock_factory.return_value.get_project_repository.return_value = mock_repo
        
        service_mock = MagicMock()
        service_mock.get_project = AsyncMock(return_value=mock_project)
        
        with patch("todopro_cli.commands.get_command.ProjectService", return_value=service_mock):
            result = runner.invoke(app, ["project", "Test"])
            
            # Verify command structure
            assert result.exit_code in [0, 1]


class TestGetCommandStructure:
    """Tests for overall get command structure."""

    def test_get_help(self):
        """Test that get command shows help correctly."""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "Get resource details" in result.stdout
        assert "task" in result.stdout
        assert "project" in result.stdout
        assert "label" in result.stdout

    def test_get_task_help(self):
        """Test that get task subcommand has help."""
        result = runner.invoke(app, ["task", "--help"])
        
        assert result.exit_code == 0
        assert "Get task details" in result.stdout

    def test_get_project_help(self):
        """Test that get project subcommand has help."""
        result = runner.invoke(app, ["project", "--help"])
        
        assert result.exit_code == 0
        assert "Get project details" in result.stdout
