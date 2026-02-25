"""Tests for show (stats) command.

Tests `todopro show today/week/month/streak/score` which uses FocusAnalytics.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.stats import app

runner = CliRunner()

# Minimal mock data for analytics responses
MOCK_DAILY = {
    "date": "2026-02-24T00:00:00",
    "total_sessions": 5,
    "completed_sessions": 4,
    "total_focus_minutes": 100,
    "break_minutes": 20,
    "most_focused_context": "project-a",
    "most_focused_sessions": 3,
    "tasks_completed": 2,
    "sessions": [],
}

MOCK_WEEKLY = {
    "start_date": "2026-02-17T00:00:00",
    "end_date": "2026-02-23T00:00:00",
    "total_sessions": 21,
    "total_focus_minutes": 525,
    "daily_average_sessions": 3.0,
    "daily_average_minutes": 75.0,
    "most_productive_day": {"date": "2026-02-20", "sessions": 5},
    "peak_hours": [{"hour": 10}, {"hour": 14}],
    "context_distribution": [],
    "daily_summaries": [
        {
            "date": "2026-02-17T00:00:00",
            "total_sessions": 3,
            "total_focus_minutes": 75,
        }
    ],
}

MOCK_STREAK = {
    "current_streak": 5,
    "longest_streak": 14,
    "longest_streak_start": "2026-01-01T00:00:00",
    "longest_streak_end": "2026-01-14T00:00:00",
}

MOCK_SCORE = {
    "score": 82,
    "grade": "B+",
    "components": {
        "consistency": {"score": 20, "value": 5, "max": 7},
        "completion": {"score": 90, "value": 90, "max": 100},
        "volume": {"score": 18, "value": 18, "max": 25},
        "streak": {"score": 10, "value": 5, "max": 14},
    },
}


@pytest.fixture
def mock_analytics():
    """Mock FocusAnalytics for testing."""
    with patch("todopro_cli.commands.stats.FocusAnalytics") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.get_daily_summary.return_value = MOCK_DAILY
        mock_instance.get_weekly_summary.return_value = MOCK_WEEKLY
        mock_instance.get_current_streak.return_value = MOCK_STREAK
        mock_instance.get_productivity_score.return_value = MOCK_SCORE
        yield mock_instance


class TestShowToday:
    """Tests for the show today command."""

    def test_show_today_output(self, mock_analytics):
        """Test show today produces expected output."""
        result = runner.invoke(app, ["today"])
        assert result.exit_code == 0
        assert "Focus Summary" in result.stdout

    def test_show_today_json_output(self, mock_analytics):
        """Test show today with JSON output."""
        result = runner.invoke(app, ["today", "--output", "json"])
        assert result.exit_code == 0
        mock_analytics.get_daily_summary.assert_called_once()

    def test_show_today_calls_analytics(self, mock_analytics):
        """Test show today calls FocusAnalytics.get_daily_summary."""
        runner.invoke(app, ["today"])
        mock_analytics.get_daily_summary.assert_called_once()


class TestShowWeek:
    """Tests for the show week command."""

    def test_show_week_output(self, mock_analytics):
        """Test show week produces expected output."""
        result = runner.invoke(app, ["week"])
        assert result.exit_code == 0
        assert "Weekly Focus Report" in result.stdout

    def test_show_week_json_output(self, mock_analytics):
        """Test show week with JSON output."""
        result = runner.invoke(app, ["week", "--output", "json"])
        assert result.exit_code == 0
        mock_analytics.get_weekly_summary.assert_called_once()

    def test_show_week_calls_analytics(self, mock_analytics):
        """Test show week calls FocusAnalytics.get_weekly_summary."""
        runner.invoke(app, ["week"])
        mock_analytics.get_weekly_summary.assert_called_once()


class TestShowStreak:
    """Tests for the show streak command."""

    def test_show_streak_output(self, mock_analytics):
        """Test show streak produces expected output."""
        result = runner.invoke(app, ["streak"])
        assert result.exit_code == 0
        assert "Current Streak" in result.stdout
        assert "5 days" in result.stdout

    def test_show_streak_json_output(self, mock_analytics):
        """Test show streak with JSON output."""
        result = runner.invoke(app, ["streak", "--output", "json"])
        assert result.exit_code == 0
        mock_analytics.get_current_streak.assert_called_once()

    def test_show_streak_calls_analytics(self, mock_analytics):
        """Test show streak calls FocusAnalytics.get_current_streak."""
        runner.invoke(app, ["streak"])
        mock_analytics.get_current_streak.assert_called_once()

    def test_show_streak_zero(self, mock_analytics):
        """Test show streak with zero current streak."""
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 0,
            "longest_streak": 5,
            "longest_streak_start": None,
            "longest_streak_end": None,
        }
        result = runner.invoke(app, ["streak"])
        assert result.exit_code == 0
        assert "new streak" in result.stdout.lower() or "Start" in result.stdout


class TestShowScore:
    """Tests for the show score command."""

    def test_show_score_output(self, mock_analytics):
        """Test show score produces expected output."""
        result = runner.invoke(app, ["score"])
        assert result.exit_code == 0
        assert "Productivity Score" in result.stdout
        assert "82" in result.stdout

    def test_show_score_json_output(self, mock_analytics):
        """Test show score with JSON output."""
        result = runner.invoke(app, ["score", "--output", "json"])
        assert result.exit_code == 0
        mock_analytics.get_productivity_score.assert_called_once()


class TestShowHelp:
    """Tests for show command help."""

    def test_app_help(self):
        """Test show app help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "today" in result.stdout
        assert "week" in result.stdout
        assert "streak" in result.stdout
        assert "score" in result.stdout

    def test_today_help(self):
        """Test show today help."""
        result = runner.invoke(app, ["today", "--help"])
        assert result.exit_code == 0

    def test_week_help(self):
        """Test show week help."""
        result = runner.invoke(app, ["week", "--help"])
        assert result.exit_code == 0
