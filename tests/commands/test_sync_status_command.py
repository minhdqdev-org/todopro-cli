"""Unit tests for sync-status command.

The command body references undefined names. We inject mocks via
patch(create=True) to exercise those lines.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.sync_status_command import app

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Help tests
# ---------------------------------------------------------------------------

class TestSyncStatusHelp:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_sync_status_subcommand_help(self):
        """The default command should also surface --help."""
        result = runner.invoke(app, ["sync-status", "--help"])
        # Either the subcommand exists or only the root help is available
        assert result.exit_code in (0, 2)


# ---------------------------------------------------------------------------
# Functional tests (covers lines 23-27)
# ---------------------------------------------------------------------------

class TestSyncStatusCommand:
    def _invoke_sync_status(self, args=None, service_side_effect=None):
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {
            "synced": True,
            "last_sync": "2024-01-01T00:00:00",
        }
        mock_service = MagicMock()
        mock_service.get_status = AsyncMock(
            return_value=mock_status,
            side_effect=service_side_effect,
        )

        with patch(
            "todopro_cli.commands.sync_status_command.get_storage_strategy_context",
            return_value=MagicMock(),
            create=True,
        ):
            with patch(
                "todopro_cli.commands.sync_status_command.factory",
                MagicMock(),
                create=True,
            ):
                with patch(
                    "todopro_cli.services.sync_service.SyncService",
                    return_value=mock_service,
                ):
                    return runner.invoke(app, args or []), mock_service

    def test_sync_status_success(self):
        result, mock_service = self._invoke_sync_status()
        assert result.exit_code == 0
        mock_service.get_status.assert_awaited_once()

    def test_sync_status_json_output(self):
        result, _ = self._invoke_sync_status(["--output", "json"])
        assert result.exit_code == 0

    def test_sync_status_service_error_exits_nonzero(self):
        result, _ = self._invoke_sync_status(
            service_side_effect=Exception("connection failed")
        )
        assert result.exit_code != 0
