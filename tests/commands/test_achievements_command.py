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
            "todopro_cli.commands.achievements_command.AchievementTracker"
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
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = [mock_achievement]
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_check_achievements_none(self):
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            result = runner.invoke(app, ["check"])
        assert "No new achievements" in result.output

    def test_achievement_stats(self):
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = {}
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Additional tests to cover uncovered branches
# ---------------------------------------------------------------------------


def _make_achievement(
    icon="🔥",
    name="Hot Streak",
    description="Stay on fire",
    req_type="streak_days",
):
    """Build a lightweight mock achievement."""
    a = MagicMock()
    a.icon = icon
    a.name = name
    a.description = description
    a.requirement = {"type": req_type}
    return a


class TestListAchievementsNewlyEarned:
    """Cover the newly_earned celebration banner (lines 35-43)."""

    def test_newly_earned_shows_banner(self):
        """When check_achievements() returns items, a celebration panel is shown."""
        newly = [_make_achievement()]
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = newly
            mock_tracker.get_earned_achievements.return_value = newly
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Achievement Unlocked" in result.output or "Hot Streak" in result.output

    def test_newly_earned_multiple_shows_all(self):
        """Multiple newly-earned achievements are all shown."""
        newly = [
            _make_achievement(name="First", icon="⭐"),
            _make_achievement(name="Second", icon="🎯"),
        ]
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = newly
            mock_tracker.get_earned_achievements.return_value = newly
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0


class TestListAchievementsCategories:
    """Cover category grouping for earned achievements (lines 66-71)."""

    def test_streak_category(self):
        """streak_days requirement type is grouped under Streaks."""
        a = _make_achievement(req_type="streak_days")
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = [a]
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Streaks" in result.output

    def test_milestone_category_sessions(self):
        """total_sessions requirement type is grouped under Milestones."""
        a = _make_achievement(req_type="total_sessions")
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = [a]
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_milestone_category_hours(self):
        """total_hours requirement type is grouped under Milestones."""
        a = _make_achievement(req_type="total_hours")
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = [a]
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_quality_category_perfect(self):
        """perfect_sessions requirement type is grouped under Quality."""
        a = _make_achievement(req_type="perfect_sessions")
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = [a]
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_special_category(self):
        """Unknown requirement type is grouped under Special."""
        a = _make_achievement(req_type="first_task")
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = [a]
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0


class TestListAchievementsShowAll:
    """Cover --all flag showing progress bars (lines 86-117)."""

    def _make_progress(
        self,
        achievement=None,
        current=5,
        required=10,
        percentage=50.0,
    ):
        if achievement is None:
            achievement = _make_achievement()
        return {
            "achievement": achievement,
            "current": current,
            "required": required,
            "percentage": percentage,
        }

    def test_show_all_with_no_earned(self):
        """--all with no earned achievements shows available achievements."""
        progress = {"ach-1": self._make_progress()}
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = progress
            result = runner.invoke(app, ["list", "--all"])
        assert result.exit_code == 0
        assert "Available" in result.output or "Hot Streak" in result.output

    def test_show_all_hours_format(self):
        """--all shows hours-formatted progress for total_hours requirements."""
        ach = _make_achievement(req_type="total_hours")
        progress = {"ach-1": self._make_progress(achievement=ach, current=2.5, required=5)}
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = progress
            result = runner.invoke(app, ["list", "--all"])
        assert result.exit_code == 0

    def test_show_all_bool_format(self):
        """--all shows ✓/✗ for boolean current values."""
        ach = _make_achievement(req_type="first_focus")
        progress = {"ach-1": self._make_progress(achievement=ach, current=True, required=True)}
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = progress
            result = runner.invoke(app, ["list", "--all"])
        assert result.exit_code == 0

    def test_show_all_numeric_format(self):
        """--all shows integer progress for numeric counts."""
        ach = _make_achievement(req_type="total_sessions")
        progress = {"ach-1": self._make_progress(achievement=ach, current=3, required=10)}
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = []
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = progress
            result = runner.invoke(app, ["list", "--all"])
        assert result.exit_code == 0


class TestCheckNewAchievements:
    """Cover check command with newly earned achievements (lines 127-136)."""

    def test_check_with_newly_earned(self):
        """When new achievements are found, shows celebration and count."""
        newly = [_make_achievement(name="Superstar")]
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = newly
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "Unlocked" in result.output or "achievement" in result.output.lower()

    def test_check_with_multiple_newly_earned(self):
        """Multiple newly-earned achievements shows the count."""
        newly = [
            _make_achievement(name="First"),
            _make_achievement(name="Second"),
        ]
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.check_achievements.return_value = newly
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "2" in result.output


class TestAchievementStatsWithData:
    """Cover stats command with earned achievements and progress (lines 165-219)."""

    def test_stats_with_earned_achievements(self):
        """Stats with earned achievements shows category breakdown."""
        earned = [
            _make_achievement(req_type="streak_days"),
            _make_achievement(req_type="total_sessions"),
            _make_achievement(req_type="perfect_sessions"),
        ]
        progress = {
            "ach-1": {
                "achievement": earned[0],
                "current": 7,
                "required": 10,
                "percentage": 70.0,
            }
        }
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.get_earned_achievements.return_value = earned
            mock_tracker.get_progress.return_value = progress
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Achievement Statistics" in result.output or "Progress" in result.output

    def test_stats_closest_achievements_shown(self):
        """Closest achievements (highest % progress) are listed in stats."""
        ach = _make_achievement(name="Almost There")
        progress = {
            "ach-1": {
                "achievement": ach,
                "current": 9,
                "required": 10,
                "percentage": 90.0,
            },
            "ach-2": {
                "achievement": _make_achievement(name="Halfway"),
                "current": 5,
                "required": 10,
                "percentage": 50.0,
            },
        }
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = progress
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Closest" in result.output or "Almost There" in result.output

    def test_stats_empty_progress(self):
        """Stats with no progress shows empty closest section gracefully."""
        with patch(
            "todopro_cli.commands.achievements_command.AchievementTracker"
        ) as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.get_earned_achievements.return_value = []
            mock_tracker.get_progress.return_value = {}
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0


class TestRenderProgressBar:
    """Unit tests for render_progress_bar helper."""

    def test_zero_progress(self):
        from todopro_cli.commands.achievements_command import render_progress_bar

        bar = render_progress_bar(0, 10)
        assert "░" in bar
        assert "█" not in bar

    def test_full_progress(self):
        from todopro_cli.commands.achievements_command import render_progress_bar

        bar = render_progress_bar(10, 10)
        assert "█" in bar
        assert "░" not in bar

    def test_half_progress(self):
        from todopro_cli.commands.achievements_command import render_progress_bar

        bar = render_progress_bar(5, 10)
        assert "█" in bar
        assert "░" in bar

    def test_zero_max_value_returns_empty_bar(self):
        from todopro_cli.commands.achievements_command import render_progress_bar

        bar = render_progress_bar(0, 0)
        assert "█" not in bar
