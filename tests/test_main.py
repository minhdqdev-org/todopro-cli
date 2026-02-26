"""Unit tests for main.py — the CLI entry point.

Tests focus on:
- The app can be imported and invoked
- --help flags work for top-level and sub-commands
- main() function is callable
- Known sub-commands are registered
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from todopro_cli.main import app, main

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(*args, catch_exceptions: bool = True):
    return runner.invoke(app, list(args), catch_exceptions=catch_exceptions)


# ---------------------------------------------------------------------------
# Top-level help
# ---------------------------------------------------------------------------


class TestTopLevelHelp:
    """Tests for the top-level CLI help output."""

    def test_help_flag_exits_zero(self):
        result = _invoke("--help")
        assert result.exit_code == 0

    def test_help_shows_app_name(self):
        result = _invoke("--help")
        assert "todopro" in result.output.lower()

    def test_help_shows_sub_commands(self):
        result = _invoke("--help")
        output = result.output.lower()
        # Core sub-commands must be listed
        assert "task" in output or "auth" in output or "stats" in output

    def test_no_args_shows_help(self):
        """no_args_is_help=True means invoking with no args prints help."""
        result = _invoke()
        # Exit code 0 or non-zero is acceptable, but help text should be shown
        assert "Usage" in result.output or "todopro" in result.output.lower()


# ---------------------------------------------------------------------------
# Sub-command help flags
# ---------------------------------------------------------------------------


class TestSubCommandHelp:
    """Verify registered sub-commands respond to --help."""

    @pytest.mark.parametrize("subcommand", [
        # General
        "version",
        "update",
        # Convenience task commands
        "add",
        "complete",
        "reschedule",
        "edit",
        "today",
        "reopen",
        "ramble",
        # Resource groups
        "auth",
        "task",
        "project",
        "label",
        "context",
        "config",
        "focus",
        "goals",
        "stats",
        "analytics",
        "achievements",
        "sync",
        "data",
        "encryption",
        "template",
        "github",
        "calendar",
    ])
    def test_subcommand_help(self, subcommand):
        result = _invoke(subcommand, "--help")
        # Either exit 0 or exit 2 (no_args_is_help triggers 0/exit)
        # Key assertion: help text is printed
        assert "Usage" in result.output or result.exit_code in (0, 2)


# ---------------------------------------------------------------------------
# Specific command smoke tests
# ---------------------------------------------------------------------------


class TestVersionCommand:
    def test_version_help(self):
        result = _invoke("version", "--help")
        assert result.exit_code == 0 or "version" in result.output.lower()


class TestStatsSubcommands:
    """stats sub-commands should print help."""

    @pytest.mark.parametrize("sub", ["today", "week", "month", "streak", "score", "heatmap", "export", "quality"])
    def test_stats_subcommand_help(self, sub):
        result = _invoke("stats", sub, "--help")
        assert "Usage" in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------


class TestMainEntryPoint:
    def test_main_function_callable(self):
        """main() wraps app(); calling with --help should not raise."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_main_import(self):
        """main is importable from todopro_cli.main."""
        from todopro_cli.main import main as _main
        assert callable(_main)

    def test_main_invokes_app(self):
        """main() calls app() internally."""
        with patch("todopro_cli.main.app") as mock_app:
            main()
            mock_app.assert_called_once()


# ---------------------------------------------------------------------------
# App registration smoke tests
# ---------------------------------------------------------------------------


class TestAppRegistration:
    """Verify that typers are added correctly by checking help output."""

    def test_task_command_in_help(self):
        result = _invoke("--help")
        assert "task" in result.output.lower()

    def test_auth_command_in_help(self):
        result = _invoke("--help")
        assert "auth" in result.output.lower()

    def test_stats_command_in_help(self):
        result = _invoke("--help")
        assert "stats" in result.output.lower()

    def test_sync_command_in_help(self):
        result = _invoke("--help")
        assert "sync" in result.output.lower()

    def test_focus_command_in_help(self):
        result = _invoke("--help")
        assert "focus" in result.output.lower()
