"""Unit tests for login_command.py.

The app registers a single 'login' command; invoke it WITHOUT repeating
the command name (single-command Typer app pattern).
"""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.login_command import app

runner = CliRunner(mix_stderr=False)


class TestLoginCommandHelp:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "usage" in result.output.lower()

    def test_help_shows_email_option(self):
        result = runner.invoke(app, ["--help"])
        assert "email" in result.output.lower()

    def test_help_shows_password_option(self):
        result = runner.invoke(app, ["--help"])
        assert "password" in result.output.lower()


class TestLoginCommandInvocation:
    """Tests that cover the login_command function body."""

    def _invoke_login(self, args=None, login_side_effect=None):
        mock_login = MagicMock(side_effect=login_side_effect)
        with patch("todopro_cli.commands.login_command.login", mock_login):
            return runner.invoke(app, args or []), mock_login

    def test_login_with_email_and_password(self):
        result, mock_login = self._invoke_login(
            ["--email", "user@example.com", "--password", "secret"]
        )
        assert result.exit_code == 0
        mock_login.assert_called_once_with(
            email="user@example.com",
            password="secret",
            endpoint=None,
            save_profile=False,
        )

    def test_login_with_endpoint(self):
        result, mock_login = self._invoke_login(
            ["--email", "user@example.com", "--password", "s", "--endpoint", "https://api.example.com"]
        )
        assert result.exit_code == 0
        mock_login.assert_called_once_with(
            email="user@example.com",
            password="s",
            endpoint="https://api.example.com",
            save_profile=False,
        )

    def test_login_with_save_profile(self):
        result, mock_login = self._invoke_login(
            ["--email", "u@x.com", "--password", "p", "--save-profile"]
        )
        assert result.exit_code == 0
        mock_login.assert_called_once_with(
            email="u@x.com",
            password="p",
            endpoint=None,
            save_profile=True,
        )

    def test_login_no_args_delegates_to_auth(self):
        """login_command delegates all prompting to auth.login; no args is ok."""
        result, mock_login = self._invoke_login([])
        # auth.login handles prompting – command itself should succeed
        assert result.exit_code == 0
        mock_login.assert_called_once()

    def test_login_propagates_exception(self):
        """If auth.login raises, command_wrapper surfaces it."""
        result, _ = self._invoke_login(
            ["--email", "x@x.com", "--password", "p"],
            login_side_effect=Exception("auth error"),
        )
        # exit code != 0 when an unexpected exception bubbles up
        assert result.exit_code != 0
