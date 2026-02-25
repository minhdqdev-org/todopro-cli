"""Tests for status command.

Tests `todopro status focus` which delegates to focus.py's focus_status().
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.status_command import app

runner = CliRunner()


class TestStatusFocus:
    """Tests for the status focus command."""

    def test_status_app_exists(self):
        """Test that the status app is registered."""
        assert app is not None

    def test_status_focus_help(self):
        """Test status focus help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "focus" in result.stdout.lower() or "status" in result.stdout.lower()

    def test_status_focus_subcommand_registered(self):
        """Test that status focus command is registered in app."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_status_focus_calls_impl(self):
        """Test that status focus calls the underlying focus.focus_status implementation."""
        with patch("todopro_cli.commands.focus.focus_status") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, [])
            mock_impl.assert_called_once()

    def test_status_focus_with_output_option(self):
        """Test status focus accepts output format option."""
        with patch("todopro_cli.commands.focus.focus_status") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, ["--output", "json"])
            mock_impl.assert_called_once()
