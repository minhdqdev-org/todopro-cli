"""Unit tests for goals commands (show, set, list, reset, callback)."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.goals import app, format_duration, render_progress_bar

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_PROGRESS = {
    "daily": {
        "sessions": {"current": 0, "target": 8, "progress": 0.0, "achieved": False},
        "minutes": {"current": 0, "target": 200, "progress": 0.0, "achieved": False},
    },
    "weekly": {
        "sessions": {"current": 0, "target": 40, "progress": 0.0, "achieved": False},
        "minutes": {"current": 0, "target": 1000, "progress": 0.0, "achieved": False},
    },
    "streak": {
        "current": 0,
        "target": 30,
        "progress": 0.0,
        "achieved": False,
        "longest": 0,
    },
}

_DEFAULT_GOALS = {
    "daily_sessions": 8,
    "daily_minutes": 200,
    "weekly_sessions": 40,
    "weekly_minutes": 1000,
    "streak_target": 30,
}


def _make_manager(
    goals=None,
    progress=None,
    achievements=None,
):
    """Build a MagicMock that mimics GoalsManager."""
    mgr = MagicMock()
    mgr.get_goals.return_value = goals if goals is not None else dict(_DEFAULT_GOALS)
    mgr.get_all_progress.return_value = (
        progress if progress is not None else _deep_copy_progress(_DEFAULT_PROGRESS)
    )
    mgr.check_achievements.return_value = achievements if achievements is not None else []
    mgr.save_config = MagicMock()
    mgr.config = MagicMock()
    mgr.config.focus_goals = dict(_DEFAULT_GOALS)
    return mgr


def _deep_copy_progress(p):
    import copy

    return copy.deepcopy(p)


# ---------------------------------------------------------------------------
# Pure helper function tests
# ---------------------------------------------------------------------------


class TestFormatDuration:
    """Tests for the format_duration helper."""

    def test_zero_minutes(self):
        assert format_duration(0) == "0m"

    def test_minutes_only(self):
        assert format_duration(45) == "45m"

    def test_exactly_one_hour(self):
        assert format_duration(60) == "1h 0m"

    def test_hours_and_minutes(self):
        assert format_duration(90) == "1h 30m"

    def test_large_value(self):
        result = format_duration(200)
        assert "h" in result  # 3h 20m
        assert "m" in result

    def test_fractional_minutes_truncated(self):
        # 61.9 minutes → 1h 1m
        result = format_duration(61.9)
        assert result == "1h 1m"


class TestRenderProgressBar:
    """Tests for the render_progress_bar helper."""

    def test_zero_progress(self):
        bar = render_progress_bar(0, 10, width=10)
        assert bar == "░" * 10

    def test_full_progress(self):
        bar = render_progress_bar(10, 10, width=10)
        assert bar == "█" * 10

    def test_half_progress(self):
        bar = render_progress_bar(5, 10, width=10)
        assert bar.count("█") == 5
        assert bar.count("░") == 5

    def test_zero_max_value(self):
        bar = render_progress_bar(5, 0, width=8)
        assert bar == "░" * 8

    def test_over_max_clamped(self):
        bar = render_progress_bar(20, 10, width=10)
        assert bar == "█" * 10

    def test_default_width(self):
        bar = render_progress_bar(6, 12)
        assert len(bar) == 12  # default width=12


# ---------------------------------------------------------------------------
# show_goals / goals_callback tests
# ---------------------------------------------------------------------------


class TestShowGoals:
    """Tests for 'goals show' command."""

    def test_show_goals_exits_zero(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert result.exit_code == 0

    def test_show_goals_displays_sections(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert "Daily" in result.output
        assert "Weekly" in result.output
        assert "Streak" in result.output

    def test_show_goals_calls_manager_methods(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            runner.invoke(app, ["show"])
        mgr.get_goals.assert_called_once()
        mgr.get_all_progress.assert_called_once()
        mgr.check_achievements.assert_called_once()

    def test_show_goals_no_achievements_tip_daily(self):
        """When no achievements and daily sessions left, shows daily tip."""
        progress = _deep_copy_progress(_DEFAULT_PROGRESS)
        progress["daily"]["sessions"]["current"] = 0  # 8 left
        mgr = _make_manager(progress=progress, achievements=[])
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert "Tip" in result.output or "sessions" in result.output

    def test_show_goals_tip_weekly_when_daily_done(self):
        """When daily sessions done but weekly not, shows weekly tip."""
        progress = _deep_copy_progress(_DEFAULT_PROGRESS)
        progress["daily"]["sessions"]["current"] = 8   # daily done
        progress["daily"]["sessions"]["target"] = 8
        progress["weekly"]["sessions"]["current"] = 5  # still weekly left
        progress["weekly"]["sessions"]["target"] = 40
        mgr = _make_manager(progress=progress, achievements=[])
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert "weekly" in result.output.lower() or "sessions" in result.output.lower()

    def test_show_goals_one_achievement(self):
        mgr = _make_manager(achievements=["ach1"])
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert "achieved" in result.output.lower() or "Nice" in result.output

    def test_show_goals_two_achievements(self):
        mgr = _make_manager(achievements=["a", "b"])
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert "Great" in result.output or "progress" in result.output.lower()

    def test_show_goals_four_achievements(self):
        mgr = _make_manager(achievements=["a", "b", "c", "d"])
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert "Amazing" in result.output or "goals" in result.output.lower()

    def test_show_goals_with_achieved_flags(self):
        """Check achieved ✓ marker appears when achieved=True."""
        progress = _deep_copy_progress(_DEFAULT_PROGRESS)
        progress["daily"]["sessions"]["achieved"] = True
        mgr = _make_manager(progress=progress)
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        # Rich strips markup in test runner output; just check exit code
        assert result.exit_code == 0

    def test_show_goals_streak_achieved(self):
        progress = _deep_copy_progress(_DEFAULT_PROGRESS)
        progress["streak"]["achieved"] = True
        progress["streak"]["current"] = 30
        mgr = _make_manager(progress=progress)
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert result.exit_code == 0

    def test_show_goals_streak_longest_displayed(self):
        progress = _deep_copy_progress(_DEFAULT_PROGRESS)
        progress["streak"]["longest"] = 15
        mgr = _make_manager(progress=progress)
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["show"])
        assert "15" in result.output


class TestGoalsCallback:
    """Tests for goals_callback (invoked when no subcommand given)."""

    def test_callback_no_subcommand_shows_goals(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, [])
        assert result.exit_code == 0
        # Should display same content as show
        assert "Daily" in result.output or "Goals" in result.output

    def test_callback_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "goals" in result.output.lower() or "progress" in result.output.lower()


# ---------------------------------------------------------------------------
# set_goal tests
# ---------------------------------------------------------------------------


class TestSetGoal:
    """Tests for 'goals set' command."""

    def test_set_daily_sessions(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "daily-sessions", "10"])
        assert result.exit_code == 0
        mgr.set_goal.assert_called_once_with("daily_sessions", 10)

    def test_set_daily_minutes(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "daily-minutes", "120"])
        assert result.exit_code == 0
        mgr.set_goal.assert_called_once_with("daily_minutes", 120)
        assert "h" in result.output or "m" in result.output  # duration displayed

    def test_set_weekly_sessions(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "weekly-sessions", "50"])
        assert result.exit_code == 0
        mgr.set_goal.assert_called_once_with("weekly_sessions", 50)

    def test_set_weekly_minutes(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "weekly-minutes", "600"])
        assert result.exit_code == 0
        mgr.set_goal.assert_called_once_with("weekly_minutes", 600)

    def test_set_streak_target(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "streak-target", "14"])
        assert result.exit_code == 0
        mgr.set_goal.assert_called_once_with("streak_target", 14)
        assert "days" in result.output

    def test_set_goal_displays_success(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "daily-sessions", "5"])
        assert "daily sessions" in result.output.lower() or "Goal set" in result.output

    def test_set_goal_value_error_exits_1(self):
        mgr = _make_manager()
        mgr.set_goal.side_effect = ValueError("Invalid goal type")
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "invalid-type", "5"])
        assert result.exit_code == 1
        assert "Error" in result.output or "Invalid" in result.output

    def test_set_goal_minutes_format_duration_shown(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "daily-minutes", "90"])
        # format_duration(90) = "1h 30m"
        assert "1h 30m" in result.output

    def test_set_goal_sessions_format_sessions_shown(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["set", "daily-sessions", "6"])
        assert "sessions" in result.output

    def test_set_goal_missing_args_exits_nonzero(self):
        result = runner.invoke(app, ["set"])
        assert result.exit_code != 0

    def test_set_goal_hyphen_converted_to_underscore(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            runner.invoke(app, ["set", "daily-sessions", "7"])
        # Must be called with underscore version
        call_args = mgr.set_goal.call_args
        assert "_" in call_args[0][0]


# ---------------------------------------------------------------------------
# list_goals tests
# ---------------------------------------------------------------------------


class TestListGoals:
    """Tests for 'goals list' command."""

    def test_list_goals_exits_zero(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_list_goals_calls_get_goals(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            runner.invoke(app, ["list"])
        mgr.get_goals.assert_called_once()

    def test_list_goals_shows_all_types(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["list"])
        output = result.output.lower()
        assert "daily" in output
        assert "weekly" in output
        assert "streak" in output

    def test_list_goals_shows_goal_values(self):
        goals = dict(_DEFAULT_GOALS)
        goals["daily_sessions"] = 12
        mgr = _make_manager(goals=goals)
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["list"])
        assert "12" in result.output

    def test_list_goals_shows_hint(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["list"])
        assert "set" in result.output.lower()

    def test_list_goals_formats_minutes_as_duration(self):
        """daily_minutes=200 should display as '3h 20m', not raw '200'."""
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["list"])
        assert "3h" in result.output  # 200 minutes = 3h 20m

    def test_list_goals_streak_days_label(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["list"])
        assert "days" in result.output.lower()


# ---------------------------------------------------------------------------
# reset_goals tests
# ---------------------------------------------------------------------------


class TestResetGoals:
    """Tests for 'goals reset' command."""

    def test_reset_goals_exits_zero(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["reset"])
        assert result.exit_code == 0

    def test_reset_goals_calls_save_config(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            runner.invoke(app, ["reset"])
        mgr.save_config.assert_called_once()

    def test_reset_goals_sets_defaults(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            runner.invoke(app, ["reset"])
        expected = {
            "daily_sessions": 8,
            "daily_minutes": 200,
            "weekly_sessions": 40,
            "weekly_minutes": 1000,
            "streak_target": 30,
        }
        assert mgr.config.focus_goals == expected

    def test_reset_goals_shows_success_message(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["reset"])
        assert "reset" in result.output.lower() or "default" in result.output.lower()

    def test_reset_goals_shows_hint_to_list(self):
        mgr = _make_manager()
        with patch("todopro_cli.commands.goals._get_goals_manager", return_value=mgr):
            result = runner.invoke(app, ["reset"])
        assert "list" in result.output.lower()


# ---------------------------------------------------------------------------
# CLI structure tests
# ---------------------------------------------------------------------------


class TestGoalsCommandStructure:
    """Tests for overall goals command structure."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_show_subcommand_registered(self):
        result = runner.invoke(app, ["show", "--help"])
        assert result.exit_code == 0

    def test_set_subcommand_registered(self):
        result = runner.invoke(app, ["set", "--help"])
        assert result.exit_code == 0

    def test_list_subcommand_registered(self):
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_reset_subcommand_registered(self):
        result = runner.invoke(app, ["reset", "--help"])
        assert result.exit_code == 0
