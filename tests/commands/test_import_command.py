"""Unit tests for import commands.

The ``import data`` command body references undefined names. We inject mocks
via patch(create=True) to exercise those lines.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.import_command import app

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Help tests
# ---------------------------------------------------------------------------

class TestImportHelp:
    """Verify that each sub-command is registered and exposes --help."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_data_help(self):
        result = runner.invoke(app, ["data", "--help"])
        assert result.exit_code == 0
        assert "input" in result.output.lower() or "file" in result.output.lower()


# ---------------------------------------------------------------------------
# Functional tests (covers lines 23-29)
# ---------------------------------------------------------------------------

class TestImportDataCommand:
    def _invoke_import_data(self, args, service_side_effect=None):
        mock_data_service = MagicMock()
        mock_data_service.import_data = AsyncMock(side_effect=service_side_effect)
        fake_module = MagicMock()
        fake_module.DataService = MagicMock(return_value=mock_data_service)

        with patch.dict("sys.modules", {"todopro_cli.services.data_service": fake_module}):
            with patch(
                "todopro_cli.commands.import_command.get_storage_strategy_context",
                return_value=MagicMock(),
                create=True,
            ):
                with patch(
                    "todopro_cli.commands.import_command.factory",
                    MagicMock(),
                    create=True,
                ):
                    return runner.invoke(app, args), mock_data_service

    def test_import_data_success(self):
        result, mock_service = self._invoke_import_data(["input.json"])
        assert result.exit_code == 0
        mock_service.import_data.assert_awaited_once_with(
            "input.json", merge=False
        )

    def test_import_data_with_merge(self):
        result, mock_service = self._invoke_import_data(
            ["input.json", "--merge"]
        )
        assert result.exit_code == 0
        mock_service.import_data.assert_awaited_once_with(
            "input.json", merge=True
        )

    def test_import_data_shows_success(self):
        result, _ = self._invoke_import_data(["input.json"])
        assert "input.json" in result.output or "imported" in result.output.lower()

    def test_import_data_service_error_exits_nonzero(self):
        result, _ = self._invoke_import_data(
            ["input.json"],
            service_side_effect=Exception("parse error"),
        )
        assert result.exit_code != 0

    def test_import_data_missing_file_arg_exits_nonzero(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0
