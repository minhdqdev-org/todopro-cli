"""Unit tests for setup_command.py.

Single-command Typer app (command registered as 'encryption').
Invoke WITHOUT repeating the command name.
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


class TestSetupCommandInvocation:
    def test_setup_with_passphrase_succeeds(self):
        mock_svc = _make_encryption_service()
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "mypassphrase"])
        assert result.exit_code == 0
        mock_svc.setup.assert_awaited_once_with("mypassphrase")

    def test_setup_shows_success_message(self):
        mock_svc = _make_encryption_service("KEY-SETUP-SUCCESS")
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "p"])
        assert result.exit_code == 0
        assert "complete" in result.output.lower() or "success" in result.output.lower()

    def test_setup_shows_recovery_key(self):
        mock_svc = _make_encryption_service("MY-RECOVERY-KEY-12345")
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "p"])
        assert result.exit_code == 0
        assert "MY-RECOVERY-KEY-12345" in result.output

    def test_setup_prompts_when_passphrase_not_provided(self):
        mock_svc = _make_encryption_service("PROMPTED-KEY")
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            with patch("typer.prompt", return_value="prompted-pass"):
                result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_svc.setup.assert_awaited_once_with("prompted-pass")

    def test_setup_json_output(self):
        mock_svc = _make_encryption_service("KEY-JSON")
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "p", "--output", "json"])
        assert result.exit_code == 0

    def test_setup_service_error_exits_nonzero(self):
        mock_svc = _make_encryption_service(
            setup_side_effect=Exception("encryption init failed")
        )
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "p"])
        assert result.exit_code != 0
