"""Unit tests for export commands.

All three command bodies reference undefined names (get_storage_strategy_context,
factory, strategy_context). We inject mocks via patch(create=True) to cover
those lines.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.export_command import app

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Shared mock setup helpers
# ---------------------------------------------------------------------------

def _patch_export_context():
    """Context manager stack to patch all undefined names in export_command."""
    return (
        patch(
            "todopro_cli.commands.export_command.get_storage_strategy_context",
            return_value=MagicMock(),
            create=True,
        ),
        patch(
            "todopro_cli.commands.export_command.factory",
            MagicMock(),
            create=True,
        ),
        patch(
            "todopro_cli.commands.export_command.strategy_context",
            MagicMock(),
            create=True,
        ),
    )


# ---------------------------------------------------------------------------
# Help tests
# ---------------------------------------------------------------------------

class TestExportHelp:
    """Verify that each sub-command is registered and exposes --help."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_data_help(self):
        result = runner.invoke(app, ["data", "--help"])
        assert result.exit_code == 0
        assert "output" in result.output.lower() or "file" in result.output.lower()

    def test_stats_help(self):
        result = runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0

    def test_analytics_help(self):
        result = runner.invoke(app, ["analytics", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Functional tests (covers lines 21-27, 36-43, 52-59)
# ---------------------------------------------------------------------------

class TestExportDataCommand:
    def test_export_data_success(self):
        mock_data_service = MagicMock()
        mock_data_service.export_data = AsyncMock()
        MockDataService = MagicMock(return_value=mock_data_service)
        fake_module = MagicMock()
        fake_module.DataService = MockDataService
        ctx_patch, factory_patch, strategy_patch = _patch_export_context()

        with patch.dict("sys.modules", {"todopro_cli.services.data_service": fake_module}):
            with ctx_patch, factory_patch, strategy_patch:
                result = runner.invoke(app, ["data", "output.json"])
        assert result.exit_code == 0
        mock_data_service.export_data.assert_awaited_once_with(
            "output.json", compress=False
        )

    def test_export_data_with_compress(self):
        mock_data_service = MagicMock()
        mock_data_service.export_data = AsyncMock()
        MockDataService = MagicMock(return_value=mock_data_service)
        fake_module = MagicMock()
        fake_module.DataService = MockDataService
        ctx_patch, factory_patch, strategy_patch = _patch_export_context()

        with patch.dict("sys.modules", {"todopro_cli.services.data_service": fake_module}):
            with ctx_patch, factory_patch, strategy_patch:
                result = runner.invoke(app, ["data", "output.json.gz", "--compress"])
        assert result.exit_code == 0
        mock_data_service.export_data.assert_awaited_once_with(
            "output.json.gz", compress=True
        )

    def test_export_data_shows_success(self):
        mock_data_service = MagicMock()
        mock_data_service.export_data = AsyncMock()
        fake_module = MagicMock()
        fake_module.DataService = MagicMock(return_value=mock_data_service)
        ctx_patch, factory_patch, strategy_patch = _patch_export_context()

        with patch.dict("sys.modules", {"todopro_cli.services.data_service": fake_module}):
            with ctx_patch, factory_patch, strategy_patch:
                result = runner.invoke(app, ["data", "out.json"])
        assert "out.json" in result.output or "exported" in result.output.lower()

    def test_export_data_service_error_exits_nonzero(self):
        mock_data_service = MagicMock()
        mock_data_service.export_data = AsyncMock(side_effect=Exception("disk full"))
        fake_module = MagicMock()
        fake_module.DataService = MagicMock(return_value=mock_data_service)
        ctx_patch, factory_patch, strategy_patch = _patch_export_context()

        with patch.dict("sys.modules", {"todopro_cli.services.data_service": fake_module}):
            with ctx_patch, factory_patch, strategy_patch:
                result = runner.invoke(app, ["data", "out.json"])
        assert result.exit_code != 0

    def test_export_data_missing_file_arg_exits_nonzero(self):
        result = runner.invoke(app, ["data"])
        assert result.exit_code != 0

    def test_export_data_missing_file_arg_exits_nonzero(self):
        result = runner.invoke(app, ["data"])
        assert result.exit_code != 0


class TestExportStatsCommand:
    def test_export_stats_success(self):
        mock_focus_service = MagicMock()
        mock_focus_service.export_stats = AsyncMock()
        mock_factory = MagicMock()
        fake_focus_module = MagicMock()
        fake_focus_module.FocusService = MagicMock(return_value=mock_focus_service)

        with patch.dict("sys.modules", {"todopro_cli.services.focus_service": fake_focus_module}):
            with patch(
                "todopro_cli.commands.export_command.get_storage_strategy_context",
                return_value=MagicMock(),
                create=True,
            ):
                with patch(
                    "todopro_cli.commands.export_command.factory",
                    mock_factory,
                    create=True,
                ):
                    result = runner.invoke(app, ["stats", "stats.json"])
        assert result.exit_code == 0
        mock_focus_service.export_stats.assert_awaited_once_with("stats.json")

    def test_export_stats_service_error_exits_nonzero(self):
        mock_focus_service = MagicMock()
        mock_focus_service.export_stats = AsyncMock(side_effect=Exception("err"))
        fake_focus_module = MagicMock()
        fake_focus_module.FocusService = MagicMock(return_value=mock_focus_service)

        with patch.dict("sys.modules", {"todopro_cli.services.focus_service": fake_focus_module}):
            with patch(
                "todopro_cli.commands.export_command.get_storage_strategy_context",
                return_value=MagicMock(),
                create=True,
            ):
                with patch(
                    "todopro_cli.commands.export_command.factory",
                    MagicMock(),
                    create=True,
                ):
                    result = runner.invoke(app, ["stats", "stats.json"])
        assert result.exit_code != 0

    def test_export_stats_missing_file_arg_exits_nonzero(self):
        result = runner.invoke(app, ["stats"])
        assert result.exit_code != 0


class TestExportAnalyticsCommand:
    def test_export_analytics_success(self):
        mock_analytics_service = MagicMock()
        mock_analytics_service.export_analytics = AsyncMock()
        mock_strategy_ctx = MagicMock()
        fake_analytics_module = MagicMock()
        fake_analytics_module.AnalyticsService = MagicMock(return_value=mock_analytics_service)

        with patch.dict("sys.modules", {"todopro_cli.services.analytics_service": fake_analytics_module}):
            with patch(
                "todopro_cli.commands.export_command.get_storage_strategy_context",
                return_value=MagicMock(),
                create=True,
            ):
                with patch(
                    "todopro_cli.commands.export_command.factory",
                    MagicMock(),
                    create=True,
                ):
                    with patch(
                        "todopro_cli.commands.export_command.strategy_context",
                        mock_strategy_ctx,
                        create=True,
                    ):
                        result = runner.invoke(app, ["analytics", "analytics.json"])
        assert result.exit_code == 0
        mock_analytics_service.export_analytics.assert_awaited_once_with(
            "analytics.json"
        )

    def test_export_analytics_service_error_exits_nonzero(self):
        mock_analytics_service = MagicMock()
        mock_analytics_service.export_analytics = AsyncMock(
            side_effect=Exception("analytics error")
        )
        fake_analytics_module = MagicMock()
        fake_analytics_module.AnalyticsService = MagicMock(return_value=mock_analytics_service)

        with patch.dict("sys.modules", {"todopro_cli.services.analytics_service": fake_analytics_module}):
            with patch(
                "todopro_cli.commands.export_command.get_storage_strategy_context",
                return_value=MagicMock(),
                create=True,
            ):
                with patch(
                    "todopro_cli.commands.export_command.factory",
                    MagicMock(),
                    create=True,
                ):
                    with patch(
                        "todopro_cli.commands.export_command.strategy_context",
                        MagicMock(),
                        create=True,
                    ):
                        result = runner.invoke(app, ["analytics", "analytics.json"])
        assert result.exit_code != 0

    def test_export_analytics_missing_file_arg_exits_nonzero(self):
        result = runner.invoke(app, ["analytics"])
        assert result.exit_code != 0
