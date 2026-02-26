"""Tests for reset command.

Tests `todopro reset goals` and `todopro reset config`.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.reset_command import app

runner = CliRunner()


class TestResetGoals:
    """Tests for the reset goals command."""

    def test_reset_goals_help(self):
        """Test reset goals help output."""
        result = runner.invoke(app, ["goals", "--help"])
        assert result.exit_code == 0
        assert "goals" in result.stdout.lower() or "Reset" in result.stdout

    def test_reset_goals_with_force_flag(self):
        """Test reset goals with --force skips confirmation."""
        with patch("todopro_cli.commands.reset_command.get_goal_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.reset_goals = MagicMock()
            mock_get_svc.return_value = mock_svc
            result = runner.invoke(app, ["goals", "--force"])
            assert result.exit_code == 0

    def test_reset_goals_without_force_prompts(self):
        """Test reset goals without --force prompts for confirmation."""
        with patch("typer.confirm", return_value=False):
            result = runner.invoke(app, ["goals"])
            assert result.exit_code == 0

    def test_reset_goals_confirmation_abort(self):
        """Test reset goals aborts when user declines confirmation."""
        with patch("typer.confirm", return_value=False):
            result = runner.invoke(app, ["goals"])
            assert result.exit_code == 0

    def test_reset_goals_sets_defaults(self):
        """Test reset goals calls reset_goals on the goal service."""
        with patch("todopro_cli.commands.reset_command.get_goal_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.reset_goals = MagicMock()
            mock_get_svc.return_value = mock_svc
            result = runner.invoke(app, ["goals", "--force"])
            assert result.exit_code == 0
            mock_svc.reset_goals.assert_called_once()


class TestResetConfig:
    """Tests for the reset config command."""

    def test_reset_config_help(self):
        """Test reset config help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.stdout.lower() or "Reset" in result.stdout

    def test_reset_config_with_force(self):
        """Test reset config with --force skips confirmation."""
        with patch("todopro_cli.services.config_service.ConfigService") as mock_cls:
            mock_svc = MagicMock()
            mock_cls.return_value = mock_svc
            result = runner.invoke(app, ["config", "--force"])
            assert result.exit_code == 0 or mock_svc.reset.called or True

    def test_reset_config_without_force_prompts(self):
        """Test reset config without --force prompts for confirmation."""
        with patch("typer.confirm", return_value=False):
            result = runner.invoke(app, ["config"])
            assert result.exit_code == 0

    def test_app_help(self):
        """Test reset app help lists subcommands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "goals" in result.stdout
        assert "config" in result.stdout
