"""Unit tests for achievements commands (list, check, stats)."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.achievements_command import app

runner = CliRunner()


class TestAchievementsCommand:
    """Tests for 'todopro achievements' commands."""

    def test_achievements_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_list_achievements_empty(self):
        with patch(
            "todopro_cli.commands.achievements.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = []
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No achievements" in result.output

    def test_list_achievements_with_data(self):
        mock_achievement = MagicMock()
        mock_achievement.icon = "🔥"
        mock_achievement.name = "Hot Streak"
        mock_achievement.description = "desc"
        mock_achievement.requirement = {"type": "streak_days"}

        with patch(
            "todopro_cli.commands.achievements.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = [mock_achievement]
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_check_achievements_none(self):
        with patch(
            "todopro_cli.commands.achievements.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            result = runner.invoke(app, ["check"])
        assert "No new achievements" in result.output

    def test_achievement_stats(self):
        with patch(
            "todopro_cli.commands.achievements.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = {}
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
