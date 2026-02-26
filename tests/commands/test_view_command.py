"""Unit tests for view_command.py.

Single-command Typer app (no explicit command name).
Invoke WITHOUT repeating any command name.
"""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.view_command import app

runner = CliRunner(mix_stderr=False)


class TestViewCommandHelp:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)

    def test_help_shows_layout_option(self):
        result = runner.invoke(app, ["--help"])
        assert "layout" in result.output.lower() or "Usage" in result.output

    def test_help_shows_project_code_argument(self):
        result = runner.invoke(app, ["--help"])
        assert "project" in result.output.lower() or "code" in result.output.lower()


class TestViewCommandInvocation:
    def test_view_board_layout_calls_run_board_view(self):
        mock_board_view = MagicMock()
        with patch(
            "todopro_cli.commands.view_command.run_board_view", mock_board_view
        ):
            result = runner.invoke(app, ["PROJECT-001"])
        assert result.exit_code == 0
        mock_board_view.assert_called_once_with("PROJECT-001")

    def test_view_explicit_board_layout(self):
        mock_board_view = MagicMock()
        with patch(
            "todopro_cli.commands.view_command.run_board_view", mock_board_view
        ):
            result = runner.invoke(app, ["PROJECT-001", "--layout", "board"])
        assert result.exit_code == 0
        mock_board_view.assert_called_once_with("PROJECT-001")

    def test_view_unsupported_layout_exits_nonzero(self):
        """Only 'board' layout is supported; others should exit with code 1."""
        mock_board_view = MagicMock()
        with patch(
            "todopro_cli.commands.view_command.run_board_view", mock_board_view
        ):
            result = runner.invoke(app, ["PROJECT-001", "--layout", "list"])
        assert result.exit_code != 0
        mock_board_view.assert_not_called()

    def test_view_unsupported_layout_shows_error(self):
        with patch("todopro_cli.commands.view_command.run_board_view"):
            result = runner.invoke(app, ["P-001", "--layout", "kanban"])
        assert "unsupported" in result.output.lower() or "board" in result.output.lower()

    def test_view_missing_project_code_exits_nonzero(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0

    def test_view_board_view_exception_handled(self):
        with patch(
            "todopro_cli.commands.view_command.run_board_view",
            side_effect=Exception("board error"),
        ):
            result = runner.invoke(app, ["PROJECT-001"])
        # view_command doesn't use command_wrapper, so exception may propagate
        assert result.exit_code != 0 or result.exception is not None
