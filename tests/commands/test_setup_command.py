"""Unit tests for setup_command.py.

ADR-0024 dropped end-to-end encryption: `setup encryption` is discontinued —
it no longer generates a key or calls EncryptionService.setup(), it only
prints a notice. Single-command Typer app (command registered as
'encryption'). Invoke WITHOUT repeating the command name.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.setup_command import app

runner = CliRunner(mix_stderr=False)


def _make_encryption_service(
    setup_return="RECOVERY-KEY-SETUP",
    setup_side_effect=None,
):
    svc = MagicMock()
    svc.setup = AsyncMock(
        return_value=setup_return,
        side_effect=setup_side_effect,
    )
    return svc


class TestSetupCommandHelp:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)

    def test_help_shows_passphrase_option(self):
        result = runner.invoke(app, ["--help"])
        assert "passphrase" in result.output.lower() or "Usage" in result.output

    def test_help_shows_output_option(self):
        result = runner.invoke(app, ["--help"])
        assert "output" in result.output.lower() or "Usage" in result.output


class TestSetupCommandDiscontinued:
    """ADR-0024: command is a no-op that only prints a discontinued notice."""

    def test_setup_prints_discontinued_notice(self):
        result = runner.invoke(app, ["--passphrase", "mypassphrase"])
        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()

    def test_setup_does_not_call_encryption_service(self):
        mock_svc = _make_encryption_service()
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "mypassphrase"])
        assert result.exit_code == 0
        mock_svc.setup.assert_not_awaited()

    def test_setup_does_not_prompt_when_passphrase_missing(self):
        # No stdin supplied: if the command still prompted, this would
        # raise/hang instead of exiting cleanly with the notice.
        result = runner.invoke(app, [], input="")
        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()

    def test_setup_json_output_still_discontinued(self):
        result = runner.invoke(app, ["--passphrase", "p", "--output", "json"])
        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()
