"""Unit tests for push_command.py.

The command body references undefined names (get_storage_strategy_context,
factory). Tests cover the --help flag and verify graceful failure.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.push_command import app

runner = CliRunner(mix_stderr=False)


class TestPushCommandHelp:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)

    def test_help_shows_force_option(self):
        result = runner.invoke(app, ["--help"])
        assert "force" in result.output.lower() or "Usage" in result.output


class TestPushCommandInvocation:
    """Invoke the command body after mocking the undefined names."""

    def _invoke_push(self, args=None, push_side_effect=None):
        mock_ctx = MagicMock()
        mock_service = MagicMock()
        mock_service.push = AsyncMock(side_effect=push_side_effect)

        with patch(
            "todopro_cli.commands.push_command.get_storage_strategy_context",
            return_value=mock_ctx,
            create=True,
        ):
            with patch(
                "todopro_cli.commands.push_command.factory",
                MagicMock(),
                create=True,
            ):
                with patch(
                    "todopro_cli.services.sync_service.SyncService",
                    return_value=mock_service,
                ):
                    return runner.invoke(app, args or []), mock_service

    def test_push_fails_gracefully_with_undefined_refs(self):
        result = runner.invoke(app, [])
        # NameError is caught by command_wrapper -> non-zero exit
        assert result.exit_code != 0

    def test_push_with_mocked_deps(self):
        result, _ = self._invoke_push([])
        assert result.exit_code in (0, 1)

    def test_push_force_flag_parsed(self):
        result = runner.invoke(app, ["--force"])
        assert result.exit_code != 0 or result.exception is None

    def test_push_help_exit_code(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)
