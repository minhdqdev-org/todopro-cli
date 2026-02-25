"""Tests for stop command.

Tests `todopro stop focus` which delegates to focus.py's stop_focus().
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.stop_command import app

runner = CliRunner()


class TestStopFocus:
    """Tests for the stop focus command."""

    def test_stop_app_exists(self):
        """Test that the stop app is registered."""
        assert app is not None

    def test_stop_focus_help(self):
        """Test stop focus help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Stop" in result.stdout or "focus" in result.stdout.lower()

    def test_stop_focus_subcommand_registered(self):
        """Test that stop focus command is registered in app."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_stop_focus_calls_impl(self):
        """Test that stop focus calls the underlying focus.stop_focus implementation."""
        with patch("todopro_cli.commands.focus.stop_focus") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, [])
            mock_impl.assert_called_once()

    def test_stop_focus_with_output_option(self):
        """Test stop focus accepts output format option."""
        with patch("todopro_cli.commands.focus.stop_focus") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, ["--output", "json"])
            mock_impl.assert_called_once()
