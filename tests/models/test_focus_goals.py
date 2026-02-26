"""Comprehensive unit tests for todopro_cli.models.focus.goals.GoalsManager.

Strategy
--------
* ``FocusAnalytics`` is patched at import time for every test so that no
  real SQLite database is opened.
* ``GoalsManager`` is constructed with an empty ``AppConfig()`` and a
  no-op ``save_config`` lambda so fixture setup is minimal.
* Analytics return values are overridden per-test when a specific data
  scenario is needed; the module-level ``mock_analytics`` fixture provides
  the "zero data" baseline.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from todopro_cli.models.config_models import AppConfig
from todopro_cli.models.focus.goals import GoalsManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_analytics(mocker):
    """Patch FocusAnalytics in the goals module and return the instance mock.

    Default return values represent "no activity" (all zeros) so that tests
    can override only the values they care about.
    """
    mock_cls = mocker.patch("todopro_cli.models.focus.goals.FocusAnalytics")
    instance = mock_cls.return_value
    instance.get_daily_summary.return_value = {
        "total_sessions": 0,
        "total_focus_minutes": 0,
    }
    instance.get_weekly_summary.return_value = {
        "total_sessions": 0,
        "total_focus_minutes": 0,
    }
    instance.get_current_streak.return_value = {
        "current_streak": 0,
        "longest_streak": 0,
    }
    return instance


@pytest.fixture()
def goals_manager(mock_analytics) -> GoalsManager:
    """GoalsManager backed by a fresh AppConfig and a no-op save."""
    config = AppConfig()
    return GoalsManager(config=config, save_config=lambda: None)


# ---------------------------------------------------------------------------
# Tests: get_goals
# ---------------------------------------------------------------------------


class TestGetGoals:
    """Tests for GoalsManager.get_goals()."""

    def test_returns_dict(self, goals_manager):
        assert isinstance(goals_manager.get_goals(), dict)

    def test_default_goals_have_all_keys(self, goals_manager):
        goals = goals_manager.get_goals()
        expected_keys = {
            "daily_sessions",
            "daily_minutes",
            "weekly_sessions",
            "weekly_minutes",
            "streak_target",
        }
        assert expected_keys == set(goals.keys())

    def test_default_daily_sessions(self, goals_manager):
        assert goals_manager.get_goals()["daily_sessions"] == 8

    def test_default_daily_minutes(self, goals_manager):
        assert goals_manager.get_goals()["daily_minutes"] == 200

    def test_default_weekly_sessions(self, goals_manager):
        assert goals_manager.get_goals()["weekly_sessions"] == 40

    def test_default_weekly_minutes(self, goals_manager):
        assert goals_manager.get_goals()["weekly_minutes"] == 1000

    def test_default_streak_target(self, goals_manager):
        assert goals_manager.get_goals()["streak_target"] == 30

    def test_returns_custom_goals_when_set(self, mock_analytics):
        custom = {
            "daily_sessions": 4,
            "daily_minutes": 100,
            "weekly_sessions": 20,
            "weekly_minutes": 500,
            "streak_target": 7,
        }
        config = AppConfig()
        config.focus_goals = custom
        gm = GoalsManager(config=config, save_config=lambda: None)
        assert gm.get_goals() == custom

    def test_returns_defaults_when_focus_goals_is_none(self, mock_analytics):
        config = AppConfig()
        config.focus_goals = None
        gm = GoalsManager(config=config, save_config=lambda: None)
        goals = gm.get_goals()
        assert goals["daily_sessions"] == 8


# ---------------------------------------------------------------------------
# Tests: set_goal
# ---------------------------------------------------------------------------


class TestSetGoal:
    """Tests for GoalsManager.set_goal()."""

    @pytest.mark.parametrize(
        "goal_type",
        [
            "daily_sessions",
            "daily_minutes",
            "weekly_sessions",
            "weekly_minutes",
            "streak_target",
        ],
    )
    def test_valid_goal_type_updates_value(self, goals_manager, goal_type):
        goals_manager.set_goal(goal_type, 99)
        assert goals_manager.config.focus_goals[goal_type] == 99

    def test_invalid_goal_type_raises_value_error(self, goals_manager):
        with pytest.raises(ValueError, match="Invalid goal type"):
            goals_manager.set_goal("nonexistent_goal", 10)

    def test_invalid_goal_type_message_contains_valid_types(self, goals_manager):
        with pytest.raises(ValueError) as exc_info:
            goals_manager.set_goal("bad_key", 5)
        assert "daily_sessions" in str(exc_info.value)

    def test_save_config_is_called_on_valid_set(self, mock_analytics):
        save_mock = MagicMock()
        gm = GoalsManager(config=AppConfig(), save_config=save_mock)
        gm.set_goal("daily_sessions", 5)
        save_mock.assert_called_once()

    def test_save_config_not_called_on_invalid_set(self, mock_analytics):
        save_mock = MagicMock()
        gm = GoalsManager(config=AppConfig(), save_config=save_mock)
        with pytest.raises(ValueError):
            gm.set_goal("bad_key", 5)
        save_mock.assert_not_called()

    def test_initialises_focus_goals_when_none(self, mock_analytics):
        """If config.focus_goals is None, set_goal populates it with defaults first."""
        config = AppConfig()
        config.focus_goals = None
        gm = GoalsManager(config=config, save_config=lambda: None)
        gm.set_goal("streak_target", 14)
        assert gm.config.focus_goals["streak_target"] == 14

    def test_set_goal_zero_value(self, goals_manager):
        """Setting a goal to 0 is allowed."""
        goals_manager.set_goal("daily_sessions", 0)
        assert goals_manager.config.focus_goals["daily_sessions"] == 0

    def test_set_goal_large_value(self, goals_manager):
        goals_manager.set_goal("daily_minutes", 10_000)
        assert goals_manager.config.focus_goals["daily_minutes"] == 10_000


# ---------------------------------------------------------------------------
# Tests: get_daily_progress
# ---------------------------------------------------------------------------


class TestGetDailyProgress:
    """Tests for GoalsManager.get_daily_progress()."""

    def test_returns_sessions_and_minutes_keys(self, goals_manager):
        result = goals_manager.get_daily_progress()
        assert "sessions" in result
        assert "minutes" in result

    def test_sessions_has_required_fields(self, goals_manager):
        sessions = goals_manager.get_daily_progress()["sessions"]
        assert {"current", "target", "progress", "achieved"} == set(sessions.keys())

    def test_minutes_has_required_fields(self, goals_manager):
        minutes = goals_manager.get_daily_progress()["minutes"]
        assert {"current", "target", "progress", "achieved"} == set(minutes.keys())

    def test_zero_progress_not_achieved(self, goals_manager):
        """With 0 sessions and 0 minutes (defaults from mock), goals are not met."""
        result = goals_manager.get_daily_progress()
        assert result["sessions"]["achieved"] is False
        assert result["minutes"]["achieved"] is False

    def test_zero_progress_values(self, goals_manager):
        result = goals_manager.get_daily_progress()
        assert result["sessions"]["current"] == 0
        assert result["minutes"]["current"] == 0

    def test_progress_percentage_zero_when_no_activity(self, goals_manager):
        result = goals_manager.get_daily_progress()
        assert result["sessions"]["progress"] == 0.0
        assert result["minutes"]["progress"] == 0.0

    def test_partial_progress_computed_correctly(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 4,
            "total_focus_minutes": 100,
        }
        result = goals_manager.get_daily_progress()
        # 4 / 8 * 100 = 50 %
        assert result["sessions"]["progress"] == pytest.approx(50.0)
        # 100 / 200 * 100 = 50 %
        assert result["minutes"]["progress"] == pytest.approx(50.0)

    def test_achieved_when_sessions_meet_goal(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 8,
            "total_focus_minutes": 0,
        }
        result = goals_manager.get_daily_progress()
        assert result["sessions"]["achieved"] is True

    def test_achieved_when_minutes_meet_goal(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 0,
            "total_focus_minutes": 200,
        }
        result = goals_manager.get_daily_progress()
        assert result["minutes"]["achieved"] is True

    def test_progress_capped_at_100(self, goals_manager, mock_analytics):
        """Progress percentage never exceeds 100, even when goal is exceeded."""
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 20,      # exceeds goal of 8
            "total_focus_minutes": 500,  # exceeds goal of 200
        }
        result = goals_manager.get_daily_progress()
        assert result["sessions"]["progress"] == 100.0
        assert result["minutes"]["progress"] == 100.0

    def test_target_matches_goals(self, goals_manager):
        result = goals_manager.get_daily_progress()
        goals = goals_manager.get_goals()
        assert result["sessions"]["target"] == goals["daily_sessions"]
        assert result["minutes"]["target"] == goals["daily_minutes"]

    def test_zero_goal_returns_zero_progress(self, mock_analytics):
        """A goal of 0 should not cause ZeroDivisionError – returns 0."""
        config = AppConfig()
        config.focus_goals = {
            "daily_sessions": 0,
            "daily_minutes": 0,
            "weekly_sessions": 40,
            "weekly_minutes": 1000,
            "streak_target": 30,
        }
        gm = GoalsManager(config=config, save_config=lambda: None)
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 5,
            "total_focus_minutes": 100,
        }
        result = gm.get_daily_progress()
        assert result["sessions"]["progress"] == 0
        assert result["minutes"]["progress"] == 0


# ---------------------------------------------------------------------------
# Tests: get_weekly_progress
# ---------------------------------------------------------------------------


class TestGetWeeklyProgress:
    """Tests for GoalsManager.get_weekly_progress()."""

    def test_returns_sessions_and_minutes_keys(self, goals_manager):
        result = goals_manager.get_weekly_progress()
        assert "sessions" in result
        assert "minutes" in result

    def test_zero_progress_not_achieved(self, goals_manager):
        result = goals_manager.get_weekly_progress()
        assert result["sessions"]["achieved"] is False
        assert result["minutes"]["achieved"] is False

    def test_partial_weekly_progress(self, goals_manager, mock_analytics):
        mock_analytics.get_weekly_summary.return_value = {
            "total_sessions": 20,
            "total_focus_minutes": 500,
        }
        result = goals_manager.get_weekly_progress()
        # 20 / 40 * 100 = 50%
        assert result["sessions"]["progress"] == pytest.approx(50.0)
        # 500 / 1000 * 100 = 50%
        assert result["minutes"]["progress"] == pytest.approx(50.0)

    def test_achieved_when_weekly_sessions_met(self, goals_manager, mock_analytics):
        mock_analytics.get_weekly_summary.return_value = {
            "total_sessions": 40,
            "total_focus_minutes": 0,
        }
        assert goals_manager.get_weekly_progress()["sessions"]["achieved"] is True

    def test_progress_capped_at_100_weekly(self, goals_manager, mock_analytics):
        mock_analytics.get_weekly_summary.return_value = {
            "total_sessions": 100,
            "total_focus_minutes": 5000,
        }
        result = goals_manager.get_weekly_progress()
        assert result["sessions"]["progress"] == 100.0
        assert result["minutes"]["progress"] == 100.0

    def test_target_matches_goals(self, goals_manager):
        result = goals_manager.get_weekly_progress()
        goals = goals_manager.get_goals()
        assert result["sessions"]["target"] == goals["weekly_sessions"]
        assert result["minutes"]["target"] == goals["weekly_minutes"]


# ---------------------------------------------------------------------------
# Tests: get_streak_progress
# ---------------------------------------------------------------------------


class TestGetStreakProgress:
    """Tests for GoalsManager.get_streak_progress()."""

    def test_returns_required_fields(self, goals_manager):
        result = goals_manager.get_streak_progress()
        assert {"current", "target", "progress", "achieved", "longest"} == set(
            result.keys()
        )

    def test_zero_streak_not_achieved(self, goals_manager):
        assert goals_manager.get_streak_progress()["achieved"] is False

    def test_zero_streak_progress_is_zero(self, goals_manager):
        assert goals_manager.get_streak_progress()["progress"] == 0.0

    def test_partial_streak_progress(self, goals_manager, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 15,
            "longest_streak": 20,
        }
        result = goals_manager.get_streak_progress()
        # 15 / 30 * 100 = 50%
        assert result["progress"] == pytest.approx(50.0)

    def test_achieved_when_streak_meets_target(self, goals_manager, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 30,
            "longest_streak": 30,
        }
        assert goals_manager.get_streak_progress()["achieved"] is True

    def test_streak_progress_capped_at_100(self, goals_manager, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 100,
            "longest_streak": 100,
        }
        assert goals_manager.get_streak_progress()["progress"] == 100.0

    def test_current_and_longest_values_present(self, goals_manager, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 5,
            "longest_streak": 12,
        }
        result = goals_manager.get_streak_progress()
        assert result["current"] == 5
        assert result["longest"] == 12

    def test_zero_target_returns_zero_progress(self, mock_analytics):
        """streak_target=0 should not raise ZeroDivisionError."""
        config = AppConfig()
        config.focus_goals = {
            "daily_sessions": 8,
            "daily_minutes": 200,
            "weekly_sessions": 40,
            "weekly_minutes": 1000,
            "streak_target": 0,
        }
        gm = GoalsManager(config=config, save_config=lambda: None)
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 5,
            "longest_streak": 10,
        }
        result = gm.get_streak_progress()
        assert result["progress"] == 0


# ---------------------------------------------------------------------------
# Tests: get_all_progress
# ---------------------------------------------------------------------------


class TestGetAllProgress:
    """Tests for GoalsManager.get_all_progress()."""

    def test_returns_daily_weekly_streak_keys(self, goals_manager):
        result = goals_manager.get_all_progress()
        assert {"daily", "weekly", "streak"} == set(result.keys())

    def test_daily_section_matches_get_daily_progress(self, goals_manager):
        assert goals_manager.get_all_progress()["daily"] == (
            goals_manager.get_daily_progress()
        )

    def test_weekly_section_matches_get_weekly_progress(self, goals_manager):
        assert goals_manager.get_all_progress()["weekly"] == (
            goals_manager.get_weekly_progress()
        )

    def test_streak_section_matches_get_streak_progress(self, goals_manager):
        assert goals_manager.get_all_progress()["streak"] == (
            goals_manager.get_streak_progress()
        )

    def test_all_progress_with_partial_data(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 4,
            "total_focus_minutes": 80,
        }
        mock_analytics.get_weekly_summary.return_value = {
            "total_sessions": 20,
            "total_focus_minutes": 400,
        }
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 7,
            "longest_streak": 14,
        }
        result = goals_manager.get_all_progress()
        assert result["daily"]["sessions"]["progress"] == pytest.approx(50.0)
        assert result["weekly"]["sessions"]["progress"] == pytest.approx(50.0)
        assert result["streak"]["current"] == 7


# ---------------------------------------------------------------------------
# Tests: check_achievements
# ---------------------------------------------------------------------------


class TestCheckAchievements:
    """Tests for GoalsManager.check_achievements()."""

    def test_returns_list(self, goals_manager):
        assert isinstance(goals_manager.check_achievements(), list)

    def test_no_achievements_when_all_zeros(self, goals_manager):
        assert goals_manager.check_achievements() == []

    def test_daily_sessions_achievement_detected(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 8,      # equals goal
            "total_focus_minutes": 0,
        }
        achievements = goals_manager.check_achievements()
        assert "daily_sessions" in achievements

    def test_daily_minutes_achievement_detected(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 0,
            "total_focus_minutes": 200,  # equals goal
        }
        achievements = goals_manager.check_achievements()
        assert "daily_minutes" in achievements

    def test_weekly_sessions_achievement_detected(self, goals_manager, mock_analytics):
        mock_analytics.get_weekly_summary.return_value = {
            "total_sessions": 40,
            "total_focus_minutes": 0,
        }
        achievements = goals_manager.check_achievements()
        assert "weekly_sessions" in achievements

    def test_weekly_minutes_achievement_detected(self, goals_manager, mock_analytics):
        mock_analytics.get_weekly_summary.return_value = {
            "total_sessions": 0,
            "total_focus_minutes": 1000,
        }
        achievements = goals_manager.check_achievements()
        assert "weekly_minutes" in achievements

    def test_streak_achievement_detected(self, goals_manager, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 30,
            "longest_streak": 30,
        }
        achievements = goals_manager.check_achievements()
        assert "streak_target" in achievements

    def test_all_achievements_at_once(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 10,
            "total_focus_minutes": 250,
        }
        mock_analytics.get_weekly_summary.return_value = {
            "total_sessions": 50,
            "total_focus_minutes": 1200,
        }
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 35,
            "longest_streak": 35,
        }
        achievements = goals_manager.check_achievements()
        expected = {
            "daily_sessions",
            "daily_minutes",
            "weekly_sessions",
            "weekly_minutes",
            "streak_target",
        }
        assert set(achievements) == expected

    def test_no_duplicates_in_achievements(self, goals_manager, mock_analytics):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 8,
            "total_focus_minutes": 200,
        }
        achievements = goals_manager.check_achievements()
        assert len(achievements) == len(set(achievements))

    def test_partial_achievements_only_met_ones_returned(
        self, goals_manager, mock_analytics
    ):
        mock_analytics.get_daily_summary.return_value = {
            "total_sessions": 8,   # met
            "total_focus_minutes": 50,  # not met (goal 200)
        }
        achievements = goals_manager.check_achievements()
        assert "daily_sessions" in achievements
        assert "daily_minutes" not in achievements
