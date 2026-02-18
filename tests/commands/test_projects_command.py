"""Tests for project commands.

This module tests all project management commands using mocked services.
"""
# pylint: disable=redefined-outer-name

import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.projects import app
from todopro_cli.models import Project
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
def mock_project():
    """Create a mock project for testing."""
    return Project(
        id="proj-123",
        name="Test Project",
        color="#FF0000",
        is_favorite=False,
        is_archived=False,
        workspace_id=None,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def mock_project_service():
    """Mock ProjectService for testing."""
    # Create service mock
    service_mock = MagicMock()
    service_mock.list_projects = AsyncMock()
    service_mock.get_project = AsyncMock()
    service_mock.create_project = AsyncMock()
    service_mock.update_project = AsyncMock()
    service_mock.delete_project = AsyncMock()
    service_mock.archive_project = AsyncMock()
    service_mock.unarchive_project = AsyncMock()

    with patch(
        "todopro_cli.commands.projects.ProjectService", return_value=service_mock
    ):
        yield service_mock


class TestListProjects:
    """Tests for list projects command."""

    def test_list_projects_default(self, mock_project_service, mock_project):
        """Test list command with default options."""
        mock_project_service.list_projects.return_value = [mock_project]

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_project_service.list_projects.assert_called_once()
        call_kwargs = mock_project_service.list_projects.call_args[1]
        assert call_kwargs["is_archived"] is None
        assert call_kwargs["is_favorite"] is None

    def test_list_projects_archived(self, mock_project_service, mock_project):
        """Test list command with --archived flag."""
        archived_project = mock_project.model_copy(update={"is_archived": True})
        mock_project_service.list_projects.return_value = [archived_project]

        result = runner.invoke(app, ["list", "--archived"])

        assert result.exit_code == 0
        call_kwargs = mock_project_service.list_projects.call_args[1]
        assert call_kwargs["is_archived"] is True

    def test_list_projects_favorites(self, mock_project_service, mock_project):
        """Test list command with --favorites flag."""
        favorite_project = mock_project.model_copy(update={"is_favorite": True})
        mock_project_service.list_projects.return_value = [favorite_project]

        result = runner.invoke(app, ["list", "--favorites"])

        assert result.exit_code == 0
        call_kwargs = mock_project_service.list_projects.call_args[1]
        assert call_kwargs["is_favorite"] is True

    def test_list_projects_empty(self, mock_project_service):
        """Test list command with no projects."""
        mock_project_service.list_projects.return_value = []

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0


class TestGetProject:
    """Tests for get project command."""

    def test_get_project_success(self, mock_project_service, mock_project):
        """Test get command with valid project ID."""
        mock_project_service.get_project.return_value = mock_project

        result = runner.invoke(app, ["get", "proj-123"])

        assert result.exit_code == 0
        mock_project_service.get_project.assert_called_once_with("proj-123")

    def test_get_project_not_found(self, mock_project_service):
        """Test get command with non-existent project."""
        mock_project_service.get_project.side_effect = ValueError("Project not found")

        result = runner.invoke(app, ["get", "invalid-id"])

        assert result.exit_code == 1

    def test_get_project_with_output_format(self, mock_project_service, mock_project):
        """Test get command with custom output format."""
        mock_project_service.get_project.return_value = mock_project

        result = runner.invoke(app, ["get", "proj-123", "--output", "json"])

        assert result.exit_code == 0


class TestCreateProject:
    """Tests for create project command."""

    def test_create_project_basic(self, mock_project_service, mock_project):
        """Test create command with just name."""
        mock_project_service.create_project.return_value = mock_project

        result = runner.invoke(app, ["create", "New Project"])

        assert result.exit_code == 0
        assert "Project created: proj-123" in result.stdout
        mock_project_service.create_project.assert_called_once()
        call_kwargs = mock_project_service.create_project.call_args[1]
        assert call_kwargs["name"] == "New Project"
        assert call_kwargs["color"] is None
        assert call_kwargs["is_favorite"] is False

    def test_create_project_with_color(self, mock_project_service, mock_project):
        """Test create command with color option."""
        mock_project_service.create_project.return_value = mock_project

        result = runner.invoke(app, ["create", "Colored Project", "--color", "#00FF00"])

        assert result.exit_code == 0
        call_kwargs = mock_project_service.create_project.call_args[1]
        assert call_kwargs["color"] == "#00FF00"

    def test_create_project_as_favorite(self, mock_project_service, mock_project):
        """Test create command with favorite flag."""
        favorite_project = mock_project.model_copy(update={"is_favorite": True})
        mock_project_service.create_project.return_value = favorite_project

        result = runner.invoke(app, ["create", "Favorite Project", "--favorite"])

        assert result.exit_code == 0
        call_kwargs = mock_project_service.create_project.call_args[1]
        assert call_kwargs["is_favorite"] is True

    def test_create_project_with_all_options(self, mock_project_service, mock_project):
        """Test create command with all options."""
        mock_project_service.create_project.return_value = mock_project

        result = runner.invoke(
            app,
            [
                "create",
                "Full Project",
                "--color",
                "#0000FF",
                "--favorite",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0


class TestUpdateProject:
    """Tests for update project command."""

    def test_update_project_name(self, mock_project_service, mock_project):
        """Test update command with new name."""
        updated_project = mock_project.model_copy(update={"name": "Updated Project"})
        mock_project_service.update_project.return_value = updated_project

        result = runner.invoke(app, ["update", "proj-123", "--name", "Updated Project"])

        assert result.exit_code == 0
        assert "Project updated: proj-123" in result.stdout
        call_kwargs = mock_project_service.update_project.call_args[1]
        assert call_kwargs["name"] == "Updated Project"

    def test_update_project_color(self, mock_project_service, mock_project):
        """Test update command with new color."""
        mock_project_service.update_project.return_value = mock_project

        result = runner.invoke(app, ["update", "proj-123", "--color", "#FFFF00"])

        assert result.exit_code == 0
        call_kwargs = mock_project_service.update_project.call_args[1]
        assert call_kwargs["color"] == "#FFFF00"

    def test_update_project_both_fields(self, mock_project_service, mock_project):
        """Test update command with both name and color."""
        mock_project_service.update_project.return_value = mock_project

        result = runner.invoke(
            app, ["update", "proj-123", "--name", "New Name", "--color", "#FF00FF"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_project_service.update_project.call_args[1]
        assert call_kwargs["name"] == "New Name"
        assert call_kwargs["color"] == "#FF00FF"

    def test_update_project_no_updates(self, mock_project_service):
        """Test update command with no update fields."""
        result = runner.invoke(app, ["update", "proj-123"])

        assert result.exit_code == 1
        assert "No updates specified" in result.stdout
        mock_project_service.update_project.assert_not_called()


class TestDeleteProject:
    """Tests for delete project command."""

    def test_delete_project_with_yes_flag(self, mock_project_service):
        """Test delete command with --yes flag."""
        mock_project_service.delete_project.return_value = True

        result = runner.invoke(app, ["delete", "proj-123", "--yes"])

        assert result.exit_code == 0
        assert "Project deleted: proj-123" in result.stdout
        mock_project_service.delete_project.assert_called_once_with("proj-123")

    def test_delete_project_with_confirmation(self, mock_project_service):
        """Test delete command with confirmation prompt."""
        mock_project_service.delete_project.return_value = True

        result = runner.invoke(app, ["delete", "proj-123"], input="y\n")

        assert result.exit_code == 0
        mock_project_service.delete_project.assert_called_once()

    def test_delete_project_cancelled(self, mock_project_service):
        """Test delete command when user cancels."""
        result = runner.invoke(app, ["delete", "proj-123"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        mock_project_service.delete_project.assert_not_called()


class TestArchiveProject:
    """Tests for archive project command."""

    def test_archive_project_success(self, mock_project_service, mock_project):
        """Test archive command."""
        archived_project = mock_project.model_copy(update={"is_archived": True})
        mock_project_service.archive_project.return_value = archived_project

        result = runner.invoke(app, ["archive", "proj-123"])

        assert result.exit_code == 0
        assert "Project archived: proj-123" in result.stdout
        mock_project_service.archive_project.assert_called_once_with("proj-123")

    def test_archive_project_with_output(self, mock_project_service, mock_project):
        """Test archive command with output format."""
        archived_project = mock_project.model_copy(update={"is_archived": True})
        mock_project_service.archive_project.return_value = archived_project

        result = runner.invoke(app, ["archive", "proj-123", "--output", "json"])

        assert result.exit_code == 0


class TestUnarchiveProject:
    """Tests for unarchive project command."""

    def test_unarchive_project_success(self, mock_project_service, mock_project):
        """Test unarchive command."""
        mock_project_service.unarchive_project.return_value = mock_project

        result = runner.invoke(app, ["unarchive", "proj-123"])

        assert result.exit_code == 0
        assert "Project unarchived: proj-123" in result.stdout
        mock_project_service.unarchive_project.assert_called_once_with("proj-123")

    def test_unarchive_project_with_output(self, mock_project_service, mock_project):
        """Test unarchive command with output format."""
        mock_project_service.unarchive_project.return_value = mock_project

        result = runner.invoke(app, ["unarchive", "proj-123", "--output", "json"])

        assert result.exit_code == 0


class TestViewProject:
    """Tests for view project command."""

    def test_view_project_unsupported_layout(self):
        """Test view command with unsupported layout."""
        result = runner.invoke(app, ["view", "proj-123", "--layout", "kanban"])

        # Typer will exit with code 2 for unknown argument
        assert result.exit_code != 0
        assert "Unsupported layout" in result.stdout or "Error" in result.stdout


class TestProjectCommandsIntegration:
    """Integration tests for project commands."""

    def test_help_command(self):
        """Test projects help command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Project management commands" in result.stdout
        assert "list" in result.stdout
        assert "create" in result.stdout
        assert "update" in result.stdout
        assert "delete" in result.stdout
        assert "archive" in result.stdout

    def test_list_help(self):
        """Test list command help."""
        result = runner.invoke(app, ["list", "--help"])

        assert result.exit_code == 0
        assert "List projects" in result.stdout
        assert "--archived" in result.stdout
        assert "--favorites" in result.stdout

    def test_create_help(self):
        """Test create command help."""
        result = runner.invoke(app, ["create", "--help"])

        assert result.exit_code == 0
        assert "Create a new project" in result.stdout
        assert "--color" in result.stdout
        assert "--favorite" in result.stdout

    def test_update_help(self):
        """Test update command help."""
        result = runner.invoke(app, ["update", "--help"])

        assert result.exit_code == 0
        assert "Update a project" in result.stdout
        assert "--name" in result.stdout
        assert "--color" in result.stdout


class TestProjectCommandsErrorHandling:
    """Tests for error handling in project commands."""

    def test_service_error_propagates(self, mock_project_service):
        """Test that service errors are properly handled."""
        mock_project_service.get_project.side_effect = Exception("Service error")

        result = runner.invoke(app, ["get", "proj-123"])

        assert result.exit_code == 1

    def test_repository_error_propagates(self, mock_project_service):
        """Test that repository errors are properly handled."""
        mock_project_service.create_project.side_effect = ValueError("Invalid data")

        result = runner.invoke(app, ["create", "Bad Project"])

        assert result.exit_code == 1

    def test_network_error_handling(self, mock_project_service):
        """Test network error handling."""
        mock_project_service.list_projects.side_effect = Exception("Network error")

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
