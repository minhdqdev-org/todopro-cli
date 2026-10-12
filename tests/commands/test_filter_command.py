"""Unit tests for the apply filter command."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.apply_command import app as apply_app

apply_runner = CliRunner()


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
        ), patch(
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
        ), patch(
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
        ), patch(
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
        ), patch(
            "todopro_cli.commands.apply_command.FiltersAPI", return_value=mock_api
        ):
            apply_runner.invoke(apply_app, ["x"])
        mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# delete filter
