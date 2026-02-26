"""Unit tests for signup_command.py.

Single-command Typer app (decorated with @command_wrapper for async support).
Invoke WITHOUT the command-name prefix.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.signup_command import app

runner = CliRunner(mix_stderr=False)


def _mock_auth_service(signup_side_effect=None):
    svc = MagicMock()
    svc.signup = AsyncMock(side_effect=signup_side_effect)
    return svc


class TestSignupCommandHelp:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)

    def test_help_shows_email_option(self):
        result = runner.invoke(app, ["--help"])
        assert "email" in result.output.lower()

    def test_help_shows_password_option(self):
        result = runner.invoke(app, ["--help"])
        assert "password" in result.output.lower()


class TestSignupCommandInvocation:
    def test_signup_with_email_and_password(self):
        mock_svc = _mock_auth_service()
        with patch(
            "todopro_cli.services.auth_service.AuthService",
            return_value=mock_svc,
        ):
            result = runner.invoke(
                app, ["--email", "new@example.com", "--password", "secret123"]
            )
        assert result.exit_code == 0
        mock_svc.signup.assert_awaited_once_with(
            email="new@example.com", password="secret123"
        )

    def test_signup_shows_success_message(self):
        mock_svc = _mock_auth_service()
        with patch(
            "todopro_cli.services.auth_service.AuthService",
            return_value=mock_svc,
        ):
            result = runner.invoke(
                app, ["--email", "u@example.com", "--password", "pw"]
            )
        assert result.exit_code == 0
        # format_success outputs something about the account/email
        assert "u@example.com" in result.output or "created" in result.output.lower()

    def test_signup_service_error_exits_nonzero(self):
        mock_svc = _mock_auth_service(signup_side_effect=Exception("email taken"))
        with patch(
            "todopro_cli.services.auth_service.AuthService",
            return_value=mock_svc,
        ):
            result = runner.invoke(
                app, ["--email", "taken@x.com", "--password", "pw"]
            )
        assert result.exit_code != 0

    def test_signup_prompts_for_email_when_not_provided(self):
        """When --email is omitted, typer.prompt is called."""
        mock_svc = _mock_auth_service()
        with patch(
            "todopro_cli.services.auth_service.AuthService",
            return_value=mock_svc,
        ):
            with patch("typer.prompt", side_effect=["prompted@x.com", "pw123"]):
                result = runner.invoke(app, [])
        # Should succeed if prompts supply valid values
        assert result.exit_code == 0
        mock_svc.signup.assert_awaited_once_with(
            email="prompted@x.com", password="pw123"
        )

    def test_signup_prompts_for_password_when_not_provided(self):
        """When --password is omitted, typer.prompt is called."""
        mock_svc = _mock_auth_service()
        with patch(
            "todopro_cli.services.auth_service.AuthService",
            return_value=mock_svc,
        ):
            with patch("typer.prompt", return_value="pw123"):
                result = runner.invoke(app, ["--email", "x@x.com"])
        assert result.exit_code == 0
