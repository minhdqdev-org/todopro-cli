"""Unit tests for comment_command (task comments)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.comment_command import app

runner = CliRunner()


def _make_mocks():
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_api = MagicMock()
    return mock_client, mock_api


def _invoke(args, mock_client, mock_api, **kwargs):
    with patch(
        "todopro_cli.commands.comment_command.get_client", return_value=mock_client
    ):
        with patch(
            "todopro_cli.commands.comment_command.CollaborationAPI",
            return_value=mock_api,
        ):
            return runner.invoke(app, args, **kwargs)


class TestAddComment:
    """Tests for 'comment add' subcommand."""

    def test_add_success(self):
        mock_client, mock_api = _make_mocks()
        mock_api.add_comment = AsyncMock(
            return_value={"id": "cmt-1", "content": "Hello"}
        )
        result = _invoke(["add", "task-1", "Hello world"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "cmt-1" in result.output
        mock_api.add_comment.assert_awaited_once_with("task-1", "Hello world")

    def test_add_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.add_comment = AsyncMock(side_effect=Exception("API error"))
        result = _invoke(["add", "task-1", "Hello"], mock_client, mock_api)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestListComments:
    """Tests for 'comment list' subcommand."""

    def test_list_empty(self):
        mock_client, mock_api = _make_mocks()
        mock_api.get_comments = AsyncMock(return_value=[])
        result = _invoke(["list", "task-1"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "No comments" in result.output

    def test_list_with_data(self):
        mock_client, mock_api = _make_mocks()
        mock_api.get_comments = AsyncMock(
            return_value=[
                {
                    "id": "cmt-1",
                    "content": "First comment",
                    "author": {"email": "alice@example.com"},
                    "created_at": "2025-01-01",
                },
                {
                    "id": "cmt-2",
                    "content": "Second comment",
                    "author": {"email": "bob@example.com"},
                    "created_at": "2025-01-02",
                },
            ]
        )
        result = _invoke(["list", "task-1"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "cmt-1" in result.output
        assert "First comment" in result.output
        assert "alice@example.com" in result.output


class TestDeleteComment:
    """Tests for 'comment delete' subcommand."""

    def test_delete_yes(self):
        mock_client, mock_api = _make_mocks()
        mock_api.delete_comment = AsyncMock()
        result = _invoke(["delete", "task-1", "cmt-1", "--yes"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "cmt-1" in result.output
        mock_api.delete_comment.assert_awaited_once_with("task-1", "cmt-1")

    def test_delete_abort(self):
        mock_client, mock_api = _make_mocks()
        mock_api.delete_comment = AsyncMock()
        result = _invoke(
            ["delete", "task-1", "cmt-1"], mock_client, mock_api, input="n\n"
        )
        assert "Aborted" in result.output
        mock_api.delete_comment.assert_not_awaited()

    def test_delete_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.delete_comment = AsyncMock(side_effect=Exception("Not found"))
        result = _invoke(
            ["delete", "task-1", "cmt-999", "--yes"], mock_client, mock_api
        )
        assert result.exit_code == 1
        assert "Error" in result.output


class TestHelp:
    """Tests for help output."""

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "comment" in result.output.lower() or "task" in result.output.lower()
