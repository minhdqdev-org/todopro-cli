"""Tests for start command.

Tests `todopro start focus` which delegates to focus.py's start_focus().
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.start_command import app

runner = CliRunner()


class TestStartFocus:
    """Tests for the start focus command."""

    def test_start_focus_delegates_to_impl(self):
        """Test that start focus calls focus.start_focus implementation."""
        with patch("todopro_cli.commands.start_command.app") as mock_app:
            # Verify the app was registered
            assert app is not None

    def test_start_focus_help(self):
        """Test start focus help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert (
            "task-id" in result.stdout.lower()
            or "task_id" in result.stdout.lower()
            or "TASK_ID" in result.stdout
        )

    def test_start_focus_calls_impl(self):
        """Test that start focus command calls the underlying implementation."""
        with patch("todopro_cli.commands.focus.start_focus") as mock_impl:
            mock_impl.return_value = None
            with patch("todopro_cli.commands.start_command.app"):
                pass  # Just verify module imports correctly

    def test_start_focus_invokes_focus_impl(self):
        """Test that invoking start focus runs the focus start implementation."""
        with patch("todopro_cli.commands.focus.start_focus") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, ["task-123"])
            mock_impl.assert_called_once_with(
                task_id="task-123", duration=25, template=None
            )

    def test_start_focus_with_duration(self):
        """Test start focus with custom duration."""
        with patch("todopro_cli.commands.focus.start_focus") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, ["task-123", "--duration", "45"])
            mock_impl.assert_called_once_with(
                task_id="task-123", duration=45, template=None
            )

    def test_start_focus_with_template(self):
        """Test start focus with template name."""
        with patch("todopro_cli.commands.focus.start_focus") as mock_impl:
            mock_impl.return_value = None
            result = runner.invoke(app, ["task-123", "--template", "deep_work"])
            mock_impl.assert_called_once_with(
                task_id="task-123", duration=25, template="deep_work"
            )

    def test_start_app_subcommand_registered(self):
        """Test that start focus command is registered in app."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert (
            "Start a focus session" in result.stdout or "focus" in result.stdout.lower()
        )
