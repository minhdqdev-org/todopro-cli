"""Unit tests for collaborate_command (project sharing and collaboration)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.collaborate_command import app

runner = CliRunner()


def _make_mocks():
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_api = MagicMock()
    return mock_client, mock_api


def _invoke(args, mock_client, mock_api, **kwargs):
    with patch(
        "todopro_cli.commands.collaborate_command.get_client", return_value=mock_client
    ):
        with patch(
            "todopro_cli.commands.collaborate_command.CollaborationAPI",
            return_value=mock_api,
        ):
            return runner.invoke(app, args, **kwargs)


class TestShareProject:
    """Tests for 'share' subcommand."""

    def test_share_success(self):
        mock_client, mock_api = _make_mocks()
        mock_api.share_project = AsyncMock(return_value={"id": "collab-1"})
        result = _invoke(
            ["share", "proj-1", "--email", "user@example.com"], mock_client, mock_api
        )
        assert result.exit_code == 0
        assert "user@example.com" in result.output
        assert "editor" in result.output
        mock_api.share_project.assert_awaited_once_with(
            "proj-1", "user@example.com", "editor"
        )

    def test_share_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.share_project = AsyncMock(side_effect=Exception("403 Forbidden"))
        result = _invoke(
            ["share", "proj-1", "--email", "user@example.com"], mock_client, mock_api
        )
        assert result.exit_code == 1
        assert "Error" in result.output


class TestListCollaborators:
    """Tests for 'collaborators' subcommand."""

    def test_list_empty(self):
        mock_client, mock_api = _make_mocks()
        mock_api.get_collaborators = AsyncMock(return_value=[])
        result = _invoke(["collaborators", "proj-1"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "No collaborators" in result.output

    def test_list_with_data(self):
        mock_client, mock_api = _make_mocks()
        mock_api.get_collaborators = AsyncMock(
            return_value=[
                {"user_id": "u-1", "permission": "editor", "shared_at": "2025-01-01"},
                {"user_id": "u-2", "permission": "viewer", "shared_at": "2025-02-01"},
            ]
        )
        result = _invoke(["collaborators", "proj-1"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "u-1" in result.output
        assert "editor" in result.output
        assert "u-2" in result.output


class TestUnshareProject:
    """Tests for 'unshare' subcommand."""

    def test_unshare_success(self):
        mock_client, mock_api = _make_mocks()
        mock_api.remove_collaborator = AsyncMock()
        result = _invoke(
            ["unshare", "proj-1", "--user-id", "u-123"], mock_client, mock_api
        )
        assert result.exit_code == 0
        assert "u-123" in result.output
        mock_api.remove_collaborator.assert_awaited_once_with("proj-1", "u-123")

    def test_unshare_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.remove_collaborator = AsyncMock(side_effect=Exception("Not found"))
        result = _invoke(
            ["unshare", "proj-1", "--user-id", "u-999"], mock_client, mock_api
        )
        assert result.exit_code == 1
        assert "Error" in result.output


class TestLeaveProject:
    """Tests for 'leave' subcommand."""

    def test_leave_yes(self):
        mock_client, mock_api = _make_mocks()
        mock_api.leave_project = AsyncMock()
        result = _invoke(["leave", "proj-1", "--yes"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "proj-1" in result.output
        mock_api.leave_project.assert_awaited_once_with("proj-1")

    def test_leave_abort(self):
        mock_client, mock_api = _make_mocks()
        mock_api.leave_project = AsyncMock()
        result = _invoke(["leave", "proj-1"], mock_client, mock_api, input="n\n")
        assert "Aborted" in result.output
        mock_api.leave_project.assert_not_awaited()

    def test_leave_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.leave_project = AsyncMock(side_effect=Exception("Forbidden"))
        result = _invoke(["leave", "proj-1", "--yes"], mock_client, mock_api)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestHelp:
    """Tests for help output."""

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert (
            "collaborat" in result.output.lower()
            or "share" in result.output.lower()
            or "project" in result.output.lower()
        )
