"""Unit tests for logout_command.py.

Single-command Typer app – invoke WITHOUT the command-name prefix.
"""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.logout_command import app

runner = CliRunner(mix_stderr=False)


class TestLogoutCommandHelp:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "logout" in result.output.lower()

    def test_help_shows_all_option(self):
        result = runner.invoke(app, ["--help"])
        assert "all" in result.output.lower()


class TestLogoutCommandInvocation:
    """Tests that cover the logout_command function body."""

    def _invoke_logout(self, args=None, side_effect=None):
        mock_logout = MagicMock(side_effect=side_effect)
        with patch("todopro_cli.commands.logout_command.logout", mock_logout):
            return runner.invoke(app, args or []), mock_logout

    def test_logout_default(self):
        result, mock_logout = self._invoke_logout([])
        assert result.exit_code == 0
        mock_logout.assert_called_once_with(all_profiles=False)

    def test_logout_all_profiles(self):
        result, mock_logout = self._invoke_logout(["--all"])
        assert result.exit_code == 0
        mock_logout.assert_called_once_with(all_profiles=True)

    def test_logout_propagates_exception(self):
        result, _ = self._invoke_logout(
            [], side_effect=Exception("logout failed")
        )
        assert result.exit_code != 0
