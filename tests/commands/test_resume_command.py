"""Tests for resume command.

Tests `todopro resume focus` which delegates to focus.py's resume_focus().
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.resume_command import app

runner = CliRunner()


class TestResumeFocus:
    """Tests for the resume focus command."""

    def test_resume_app_exists(self):
        """Test that the resume app is registered."""
        assert app is not None

    def test_resume_focus_help(self):
        """Test resume focus help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Resume" in result.stdout or "paused" in result.stdout.lower()

    def test_resume_focus_subcommand_registered(self):
        """Test that resume focus command is registered in app."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_resume_focus_calls_impl(self):
        """Test that resume focus calls the underlying focus.resume_focus implementation."""
        with patch("todopro_cli.commands.focus.resume_focus") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, [])
            mock_impl.assert_called_once()

    def test_resume_focus_with_output_option(self):
        """Test resume focus accepts output format option."""
        with patch("todopro_cli.commands.focus.resume_focus") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, ["--output", "json"])
            mock_impl.assert_called_once()
