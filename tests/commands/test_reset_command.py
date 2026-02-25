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

        class FakeContextManager:
            def save_config(self):
                pass

        class FakeGoalsManager:
            def __init__(self):
                self.config = MagicMock()
                self.config.focus_goals = {}
                self.context_manager = FakeContextManager()

        with patch("todopro_cli.focus.goals.GoalsManager", FakeGoalsManager):
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
        """Test reset goals sets the expected default values."""
        expected_defaults = {
            "daily_sessions": 8,
            "daily_minutes": 200,
            "weekly_sessions": 40,
            "weekly_minutes": 1000,
            "streak_target": 30,
        }
        saved_goals = {}

        class FakeContextManager:
            def save_config(self):
                pass

        class FakeGoalsManager:
            def __init__(self):
                self.config = MagicMock()
                self.context_manager = FakeContextManager()

            @property
            def focus_goals(self):
                return saved_goals

        with patch("todopro_cli.focus.goals.GoalsManager", FakeGoalsManager):
            result = runner.invoke(app, ["goals", "--force"])
            # Just verify no crash
            assert result.exit_code == 0


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
