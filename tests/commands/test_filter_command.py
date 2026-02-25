"""Unit tests for filter management commands (create, list, apply, delete)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.apply_command import app as apply_app
from todopro_cli.commands.delete_command import app as delete_app
from todopro_cli.commands.list_command import app as list_app

apply_runner = CliRunner()
delete_runner = CliRunner()
list_runner = CliRunner()


# ---------------------------------------------------------------------------
# apply filter
# ---------------------------------------------------------------------------


class TestApplyFilter:
    """Tests for 'todopro apply filter <name>'."""

    def test_apply_filter_help(self):
        result = apply_runner.invoke(apply_app, ["--help"])
        assert result.exit_code == 0
        assert "filter" in result.stdout.lower()

    def test_apply_filter_by_name(self):
        """apply filter should resolve name → id then fetch tasks."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        found_filter = {"id": "f-uuid-1", "name": "urgent"}
        tasks = [{"id": "t1", "content": "Urgent task"}]
        mock_api = MagicMock()
        mock_api.find_filter_by_name = AsyncMock(return_value=found_filter)
        mock_api.apply_filter = AsyncMock(return_value=tasks)
        with patch(
            "todopro_cli.commands.apply_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.apply_command.FiltersAPI", return_value=mock_api
            ):
                result = apply_runner.invoke(apply_app, ["urgent"])
        assert result.exit_code == 0
        mock_api.apply_filter.assert_awaited_once_with("f-uuid-1")

    def test_apply_filter_by_uuid(self):
        """apply filter with UUID should skip name resolution."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        uuid = "12345678-1234-1234-1234-123456789012"
        tasks = [{"id": "t2", "content": "Task 2"}]
        mock_api = MagicMock()
        mock_api.find_filter_by_name = AsyncMock()
        mock_api.apply_filter = AsyncMock(return_value=tasks)
        with patch(
            "todopro_cli.commands.apply_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.apply_command.FiltersAPI", return_value=mock_api
            ):
                result = apply_runner.invoke(apply_app, [uuid])
        assert result.exit_code == 0
        mock_api.find_filter_by_name.assert_not_awaited()
        mock_api.apply_filter.assert_awaited_once_with(uuid)

    def test_apply_filter_name_not_found_exits(self):
        """apply filter with unknown name should exit with error."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.find_filter_by_name = AsyncMock(return_value=None)
        mock_api.apply_filter = AsyncMock()
        with patch(
            "todopro_cli.commands.apply_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.apply_command.FiltersAPI", return_value=mock_api
            ):
                result = apply_runner.invoke(apply_app, ["nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.stdout.lower() or "nonexistent" in result.stdout

    def test_apply_filter_closes_client(self):
        """apply filter should always close the API client."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.find_filter_by_name = AsyncMock(
            return_value={"id": "f-1", "name": "x"}
        )
        mock_api.apply_filter = AsyncMock(return_value=[])
        with patch(
            "todopro_cli.commands.apply_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.apply_command.FiltersAPI", return_value=mock_api
            ):
                apply_runner.invoke(apply_app, ["x"])
        mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# delete filter
# ---------------------------------------------------------------------------


class TestDeleteFilter:
    """Tests for 'todopro delete filter <id-or-name>'."""

    def test_delete_filter_help(self):
        result = delete_runner.invoke(delete_app, ["filter", "--help"])
        assert result.exit_code == 0

    def test_delete_filter_by_uuid_with_force(self):
        """delete filter by UUID --force should call delete_filter."""
        uuid = "12345678-1234-1234-1234-123456789012"
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_filter = AsyncMock(return_value=None)
        with patch(
            "todopro_cli.commands.delete_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.delete_command.FiltersAPI", return_value=mock_api
            ):
                result = delete_runner.invoke(delete_app, ["filter", uuid, "--force"])
        assert result.exit_code == 0
        mock_api.delete_filter.assert_awaited_once_with(uuid)

    def test_delete_filter_by_name_resolves_id(self):
        """delete filter by name should look up the filter first."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        found_filter = {"id": "f-resolved", "name": "myfilter"}
        mock_api = MagicMock()
        mock_api.find_filter_by_name = AsyncMock(return_value=found_filter)
        mock_api.delete_filter = AsyncMock(return_value=None)
        with patch(
            "todopro_cli.commands.delete_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.delete_command.FiltersAPI", return_value=mock_api
            ):
                result = delete_runner.invoke(
                    delete_app, ["filter", "myfilter", "--force"]
                )
        assert result.exit_code == 0
        mock_api.find_filter_by_name.assert_awaited_once_with("myfilter")
        mock_api.delete_filter.assert_awaited_once_with("f-resolved")

    def test_delete_filter_name_not_found_exits(self):
        """delete filter with unknown name should exit with error."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.find_filter_by_name = AsyncMock(return_value=None)
        mock_api.delete_filter = AsyncMock()
        with patch(
            "todopro_cli.commands.delete_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.delete_command.FiltersAPI", return_value=mock_api
            ):
                result = delete_runner.invoke(
                    delete_app, ["filter", "ghost", "--force"]
                )
        assert result.exit_code != 0

    def test_delete_filter_confirm_no_cancels(self):
        """Declining confirmation should not delete."""
        uuid = "12345678-1234-1234-1234-123456789012"
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_filter = AsyncMock()
        with patch(
            "todopro_cli.commands.delete_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.delete_command.FiltersAPI", return_value=mock_api
            ):
                result = delete_runner.invoke(delete_app, ["filter", uuid], input="n\n")
        mock_api.delete_filter.assert_not_awaited()


# ---------------------------------------------------------------------------
# list filters
# ---------------------------------------------------------------------------


class TestListFilters:
    """Tests for 'todopro list filters'."""

    def test_list_filters_help(self):
        result = list_runner.invoke(list_app, ["filters", "--help"])
        assert result.exit_code == 0

    def test_list_filters_calls_api(self):
        """list filters should call FiltersAPI.list_filters."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        sample_filters = [
            {"id": "f-1", "name": "urgent", "color": "#FF0000", "criteria": {}},
            {"id": "f-2", "name": "work", "color": "#0000FF", "criteria": {}},
        ]
        mock_api = MagicMock()
        mock_api.list_filters = AsyncMock(return_value=sample_filters)
        with patch(
            "todopro_cli.commands.list_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.list_command.FiltersAPI", return_value=mock_api
            ):
                result = list_runner.invoke(list_app, ["filters"])
        assert result.exit_code == 0
        mock_api.list_filters.assert_awaited_once()

    def test_list_filters_empty(self):
        """list filters with no filters should succeed."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.list_filters = AsyncMock(return_value=[])
        with patch(
            "todopro_cli.commands.list_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.list_command.FiltersAPI", return_value=mock_api
            ):
                result = list_runner.invoke(list_app, ["filters"])
        assert result.exit_code == 0

    def test_list_filter_singular_alias(self):
        """'list filter' (singular) should also work."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.list_filters = AsyncMock(return_value=[])
        with patch(
            "todopro_cli.commands.list_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.list_command.FiltersAPI", return_value=mock_api
            ):
                result = list_runner.invoke(list_app, ["filter"])
        assert result.exit_code == 0
