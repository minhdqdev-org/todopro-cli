"""Unit tests for task dependency link commands (add, remove, list)."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.link_command import app

runner = CliRunner()


def _make_mocks():
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_api = MagicMock()
    return mock_client, mock_api


def _invoke(args, mock_client, mock_api, **kwargs):
    with patch(
        "todopro_cli.commands.link_command.get_client", return_value=mock_client
    ):
        with patch("todopro_cli.commands.link_command.TasksAPI", return_value=mock_api):
            return runner.invoke(app, args, **kwargs)


class TestLinkTask:
    """Tests for 'link add'."""

    def test_link_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_link_task_blocks(self):
        mock_client, mock_api = _make_mocks()
        mock_api.add_dependency = AsyncMock(return_value={"id": "dep1"})
        result = _invoke(
            ["add", "task-a-id", "--blocks", "task-b-id"], mock_client, mock_api
        )
        assert result.exit_code == 0
        assert "blocks" in result.output.lower()

    def test_link_task_blocked_by(self):
        mock_client, mock_api = _make_mocks()
        mock_api.add_dependency = AsyncMock(return_value={"id": "dep1"})
        result = _invoke(
            ["add", "task-a-id", "--blocked-by", "task-b-id"], mock_client, mock_api
        )
        assert result.exit_code == 0
        assert "blocked by" in result.output.lower()

    def test_link_no_option(self):
        mock_client, mock_api = _make_mocks()
        result = _invoke(["add", "task-id"], mock_client, mock_api)
        assert result.exit_code == 1
        assert "blocks" in result.output or "blocked-by" in result.output

    def test_link_both_options(self):
        mock_client, mock_api = _make_mocks()
        result = _invoke(
            ["add", "task-id", "--blocks", "b", "--blocked-by", "c"],
            mock_client,
            mock_api,
        )
        assert result.exit_code == 1

    def test_link_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.add_dependency = AsyncMock(side_effect=Exception("API error"))
        result = _invoke(
            ["add", "task-id", "--blocks", "other-id"], mock_client, mock_api
        )
        assert result.exit_code == 1


class TestUnlinkTask:
    """Tests for 'link remove'."""

    def test_unlink_task(self):
        mock_client, mock_api = _make_mocks()
        mock_api.remove_dependency = AsyncMock()
        result = _invoke(
            ["remove", "task-id", "--dep", "dep-id"], mock_client, mock_api
        )
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_unlink_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.remove_dependency = AsyncMock(side_effect=Exception("API error"))
        result = _invoke(
            ["remove", "task-id", "--dep", "dep-id"], mock_client, mock_api
        )
        assert result.exit_code == 1


class TestListDependencies:
    """Tests for 'link list'."""

    def test_list_deps_empty(self):
        mock_client, mock_api = _make_mocks()
        mock_api.list_dependencies = AsyncMock(return_value=[])
        result = _invoke(["list", "task-id"], mock_client, mock_api)
        assert "No dependencies" in result.output

    def test_list_deps_with_data(self):
        mock_client, mock_api = _make_mocks()
        mock_api.list_dependencies = AsyncMock(
            return_value=[
                {
                    "id": "dep1",
                    "depends_on_content": "Other task",
                    "dependency_type": "blocks",
                },
            ]
        )
        result = _invoke(["list", "task-id"], mock_client, mock_api)
        assert result.exit_code == 0
