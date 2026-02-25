"""Unit tests for template management commands (create, list, apply, delete)."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.template_command import app

runner = CliRunner()


def _make_mocks():
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_api = MagicMock()
    return mock_client, mock_api


def _invoke(args, mock_client, mock_api, **kwargs):
    with patch(
        "todopro_cli.commands.template_command.get_client", return_value=mock_client
    ):
        with patch(
            "todopro_cli.commands.template_command.TemplatesAPI", return_value=mock_api
        ):
            return runner.invoke(app, args, **kwargs)


class TestCreateTemplate:
    """Tests for 'template create'."""

    def test_create_template_success(self):
        mock_client, mock_api = _make_mocks()
        mock_api.create_template = AsyncMock(
            return_value={"id": "t-uuid", "name": "Daily Standup"}
        )
        result = _invoke(
            ["create", "Daily Standup", "--content", "Review PRs"],
            mock_client,
            mock_api,
        )
        assert result.exit_code == 0
        assert "Daily Standup" in result.output

    def test_create_template_with_priority(self):
        mock_client, mock_api = _make_mocks()
        mock_api.create_template = AsyncMock(
            return_value={"id": "t-uuid", "name": "High"}
        )
        result = _invoke(
            ["create", "High", "--content", "foo", "--priority", "3"],
            mock_client,
            mock_api,
        )
        assert result.exit_code == 0

    def test_create_template_invalid_recur(self):
        mock_client, mock_api = _make_mocks()
        result = _invoke(
            ["create", "T", "--content", "foo", "--recur", "invalid"],
            mock_client,
            mock_api,
        )
        assert result.exit_code == 1

    def test_create_template_with_recur(self):
        mock_client, mock_api = _make_mocks()
        mock_api.create_template = AsyncMock(return_value={"id": "t1", "name": "Daily"})
        result = _invoke(
            ["create", "Daily", "--content", "Stand-up", "--recur", "daily"],
            mock_client,
            mock_api,
        )
        assert result.exit_code == 0

    def test_create_template_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.create_template = AsyncMock(side_effect=Exception("API error"))
        result = _invoke(["create", "T", "--content", "foo"], mock_client, mock_api)
        assert result.exit_code == 1


class TestListTemplates:
    """Tests for 'template list'."""

    def test_list_templates_empty(self):
        mock_client, mock_api = _make_mocks()
        mock_api.list_templates = AsyncMock(return_value=[])
        result = _invoke(["list"], mock_client, mock_api)
        assert "No templates" in result.output

    def test_list_templates_with_data(self):
        mock_client, mock_api = _make_mocks()
        mock_api.list_templates = AsyncMock(
            return_value=[
                {
                    "id": "t1",
                    "name": "Daily",
                    "content": "Stand-up",
                    "priority": 1,
                    "recurrence_rule": "FREQ=DAILY",
                },
            ]
        )
        result = _invoke(["list"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "Daily" in result.output

    def test_list_templates_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.list_templates = AsyncMock(side_effect=Exception("API error"))
        result = _invoke(["list"], mock_client, mock_api)
        assert result.exit_code == 1


class TestApplyTemplate:
    """Tests for 'template apply'."""

    def test_apply_template_by_name(self):
        mock_client, mock_api = _make_mocks()
        mock_api.find_template_by_name = AsyncMock(
            return_value={"id": "t1", "name": "Daily"}
        )
        mock_api.apply_template = AsyncMock(
            return_value={"id": "task1", "content": "Stand-up"}
        )
        result = _invoke(["apply", "Daily"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "Stand-up" in result.output

    def test_apply_template_not_found(self):
        mock_client, mock_api = _make_mocks()
        mock_api.find_template_by_name = AsyncMock(return_value=None)
        result = _invoke(["apply", "unknown"], mock_client, mock_api)
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_apply_template_with_overrides(self):
        mock_client, mock_api = _make_mocks()
        mock_api.find_template_by_name = AsyncMock(
            return_value={"id": "t1", "name": "Daily"}
        )
        mock_api.apply_template = AsyncMock(
            return_value={"id": "task1", "content": "My standup"}
        )
        result = _invoke(
            ["apply", "Daily", "--title", "My standup", "--due", "2026-03-01"],
            mock_client,
            mock_api,
        )
        assert result.exit_code == 0


class TestDeleteTemplate:
    """Tests for 'template delete'."""

    def test_delete_template_yes(self):
        mock_client, mock_api = _make_mocks()
        mock_api.find_template_by_name = AsyncMock(
            return_value={"id": "t1", "name": "Daily"}
        )
        mock_api.delete_template = AsyncMock()
        result = _invoke(["delete", "Daily", "--yes"], mock_client, mock_api)
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()

    def test_delete_template_not_found(self):
        mock_client, mock_api = _make_mocks()
        mock_api.find_template_by_name = AsyncMock(return_value=None)
        result = _invoke(["delete", "ghost", "--yes"], mock_client, mock_api)
        assert result.exit_code == 1

    def test_delete_template_api_error(self):
        mock_client, mock_api = _make_mocks()
        mock_api.find_template_by_name = AsyncMock(
            return_value={"id": "t1", "name": "Daily"}
        )
        mock_api.delete_template = AsyncMock(side_effect=Exception("API error"))
        result = _invoke(["delete", "Daily", "--yes"], mock_client, mock_api)
        assert result.exit_code == 1

    def test_delete_template_aborted(self):
        mock_client, mock_api = _make_mocks()
        mock_api.find_template_by_name = AsyncMock(
            return_value={"id": "t1", "name": "Daily"}
        )
        mock_api.delete_template = AsyncMock()
        result = _invoke(["delete", "Daily"], mock_client, mock_api, input="n\n")
        assert "Aborted" in result.output
