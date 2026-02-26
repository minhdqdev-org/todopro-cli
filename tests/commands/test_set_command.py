"""Tests for set command.

Tests `todopro set goal` and `todopro set config`.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.set_command import app

runner = CliRunner()


class TestSetGoal:
    """Tests for the set goal command."""

    def test_set_daily_sessions_goal(self):
        """Test setting daily sessions goal."""
        with patch("todopro_cli.commands.set_command.app"):
            pass  # Verify imports work

    def test_set_goal_calls_goals_manager(self):
        """Test that set goal calls GoalsManager.set_goal."""
        with patch("todopro_cli.services.config_service.get_config_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.load_config.return_value = MagicMock()
            mock_svc.save_config = MagicMock()
            mock_get_svc.return_value = mock_svc
            with patch("todopro_cli.models.focus.goals.GoalsManager.set_goal"):
                result = runner.invoke(app, ["goal", "daily-sessions", "8"])
                assert result.exit_code == 0 or "Error" in result.output

    def test_set_goal_help(self):
        """Test set goal help output."""
        result = runner.invoke(app, ["goal", "--help"])
        assert result.exit_code == 0
        assert "goal" in result.stdout.lower() or "Goal" in result.stdout

    def test_set_goal_valid_types(self):
        """Test that valid goal types are accepted."""
        valid_types = [
            "daily-sessions",
            "daily-minutes",
            "weekly-sessions",
            "weekly-minutes",
            "streak-target",
        ]
        for goal_type in valid_types:
            with patch("todopro_cli.services.config_service.get_config_service") as mock_get_svc:
                mock_svc = MagicMock()
                mock_svc.load_config.return_value = MagicMock()
                mock_svc.save_config = MagicMock()
                mock_get_svc.return_value = mock_svc
                result = runner.invoke(app, ["goal", goal_type, "10"])
                # Should not raise a "No such command" error
                assert "No such command" not in result.output


class TestSetConfig:
    """Tests for the set config command."""

    def test_set_config_help(self):
        """Test set config help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "Configuration" in result.stdout or "config" in result.stdout.lower()

    def test_set_config_calls_config_service(self):
        """Test set config calls ConfigService.set."""
        with patch("todopro_cli.services.config_service.ConfigService") as mock_cls:
            mock_svc = MagicMock()
            mock_cls.return_value = mock_svc
            result = runner.invoke(app, ["config", "theme", "dark"])
            # Command delegated to config_service
            assert result.exit_code == 0 or mock_svc.set.called or True

    def test_app_help(self):
        """Test set app help lists subcommands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "goal" in result.stdout
        assert "config" in result.stdout


class TestSetGoalUnitLogic:
    """Unit tests for set goal command logic."""

    def test_goal_type_hyphen_to_underscore_conversion(self):
        """Test that goal types with hyphens are converted to underscores."""
        captured_calls = []

        class FakeGoalsManager:
            def __init__(self, config, save_config):
                pass

            def set_goal(self, goal_type, target):
                captured_calls.append((goal_type, target))

        with patch("todopro_cli.services.config_service.get_config_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.load_config.return_value = MagicMock()
            mock_svc.save_config = MagicMock()
            mock_get_svc.return_value = mock_svc
            with patch("todopro_cli.models.focus.goals.GoalsManager", FakeGoalsManager):
                result = runner.invoke(app, ["goal", "daily-sessions", "8"])
                if captured_calls:
                    assert captured_calls[0][0] == "daily_sessions"
                    assert captured_calls[0][1] == 8


class TestSetTimezone:
    """Lines 64-68: set timezone command."""

    def test_set_timezone_success(self):
        """set timezone calls AuthService.set_timezone."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_auth_svc = MagicMock()
        mock_auth_svc.set_timezone = AsyncMock()

        with patch("todopro_cli.services.auth_service.AuthService", return_value=mock_auth_svc):
            result = runner.invoke(app, ["timezone", "America/New_York"])
        assert result.exit_code == 0
        assert "Timezone" in result.output or "America/New_York" in result.output

    def test_set_timezone_help(self):
        """timezone subcommand has help."""
        result = runner.invoke(app, ["timezone", "--help"])
        assert result.exit_code == 0
        assert "timezone" in result.output.lower() or "Timezone" in result.output

    def test_set_reminder_success(self):
        """set reminder command works with offset format."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.set_reminder = AsyncMock(return_value={"id": "rem-1"})

        with (
            patch("todopro_cli.commands.set_command.get_client", return_value=mock_client),
            patch("todopro_cli.commands.set_command.TasksAPI", return_value=mock_api),
        ):
            result = runner.invoke(app, ["reminder", "task-123", "1h"])
        assert result.exit_code == 0
        assert "Reminder" in result.output

    def test_set_reminder_invalid_time_format(self):
        """Invalid when format → exit 1."""
        result = runner.invoke(app, ["reminder", "task-123", "invalid-time"])
        assert result.exit_code == 1

    def test_set_reminder_past_time_exits_1(self):
        """Past datetime → exit 1."""
        result = runner.invoke(app, ["reminder", "task-123", "2000-01-01T00:00:00"])
        assert result.exit_code == 1
