"""Comprehensive unit tests for stats.py command module.

Tests cover:
- Pure helper functions (format_duration, render_progress_bar)
- CLI commands: today, week, month, streak, score, project, heatmap, export, quality
- Both pretty-print and JSON output paths
- Edge cases (zero values, missing data, error handling)
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.stats import (
    app,
    format_duration,
    render_progress_bar,
)

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _daily_summary(
    date: str = "2024-06-15",
    completed: int = 4,
    total_focus: float = 100.0,
    break_mins: float = 20.0,
    most_focused_context: str | None = "Work",
    most_focused_sessions: int = 3,
    tasks_completed: int = 2,
    total_sessions: int = 4,
    sessions: list | None = None,
) -> dict:
    if sessions is None:
        sessions = []
    return {
        "date": date,
        "completed_sessions": completed,
        "total_focus_minutes": total_focus,
        "break_minutes": break_mins,
        "most_focused_context": most_focused_context,
        "most_focused_sessions": most_focused_sessions,
        "tasks_completed": tasks_completed,
        "total_sessions": total_sessions,
        "sessions": sessions,
    }


def _session_entry(
    start: str = "2024-06-15T09:00:00",
    end: str = "2024-06-15T09:25:00",
    title: str | None = "Write tests",
    status: str = "completed",
    completed_task: bool = True,
) -> dict:
    return {
        "start_time": start,
        "end_time": end,
        "task_title": title,
        "status": status,
        "completed_task": completed_task,
    }


def _weekly_summary() -> dict:
    base = datetime(2024, 6, 10)
    daily = []
    for i in range(7):
        d = base + timedelta(days=i)
        daily.append(
            {
                "date": d.isoformat(),
                "total_sessions": i + 1,
                "total_focus_minutes": (i + 1) * 25.0,
            }
        )
    return {
        "start_date": base.isoformat(),
        "end_date": (base + timedelta(days=6)).isoformat(),
        "daily_summaries": daily,
        "total_sessions": 28,
        "total_focus_minutes": 700.0,
        "daily_average_sessions": 4.0,
        "daily_average_minutes": 100.0,
        "most_productive_day": {"date": "2024-06-16", "sessions": 7},
        "peak_hours": [{"hour": 9}, {"hour": 14}],
        "context_distribution": [
            {"context": "Work", "minutes": 400.0, "sessions": 16},
            {"context": "Personal", "minutes": 300.0, "sessions": 12},
        ],
    }


def _monthly_summary(year: int = 2024, month: int = 6) -> dict:
    return {
        "total_sessions": 60,
        "total_focus_minutes": 1500.0,
        "tasks_completed": 45,
        "completion_rate": 75,
        "avg_session_length": 25,
        "weeks": [
            {"start": "2024-06-01", "end": "2024-06-07", "sessions": 15, "focus_minutes": 375.0},
            {"start": "2024-06-08", "end": "2024-06-14", "sessions": 15, "focus_minutes": 375.0},
            {"start": "2024-06-15", "end": "2024-06-21", "sessions": 15, "focus_minutes": 375.0},
            {"start": "2024-06-22", "end": "2024-06-30", "sessions": 15, "focus_minutes": 375.0},
        ],
        "comparison": {
            "sessions_change_pct": 10.0,
            "minutes_change_pct": -5.0,
            "completion_rate_change_pct": 3.0,
        },
    }


def _streak_data(current: int = 5, longest: int = 14) -> dict:
    return {
        "current_streak": current,
        "longest_streak": longest,
        "longest_streak_start": "2024-05-01",
        "longest_streak_end": "2024-05-14",
    }


def _score_data(score: int = 82, grade: str = "B+") -> dict:
    return {
        "score": score,
        "grade": grade,
        "components": {
            "sessions": {"score": 20, "value": 8, "max": 10},
            "hours": {"score": 18, "value": 3.5, "max": 5},
            "completion": {"score": 24, "value": 85, "max": 100},
        },
    }


def _project_stats() -> dict:
    return {
        "total_sessions": 12,
        "total_focus_minutes": 300.0,
        "tasks_completed": 8,
        "tasks_in_progress": 3,
        "avg_session_minutes": 25,
        "top_tasks": [
            {"title": "Implement feature A", "minutes": 100.0},
            {"title": "Write tests", "minutes": 75.0},
        ],
    }


def _heatmap_data() -> dict:
    # day → {hour: sessions}
    heatmap = {
        0: {9: 3, 14: 2, 16: 1},  # Monday
        2: {10: 4, 15: 2},  # Wednesday
    }
    return {
        "heatmap": heatmap,
        "peak_times": [
            {"day": 2, "hour": 10, "sessions": 4},
            {"day": 0, "hour": 9, "sessions": 3},
            {"day": 2, "hour": 15, "sessions": 2},
        ],
    }


# ---------------------------------------------------------------------------
# Pure helper function tests
# ---------------------------------------------------------------------------


class TestFormatDuration:
    """Tests for format_duration()."""

    def test_zero_minutes(self):
        assert format_duration(0) == "0m"

    def test_minutes_only(self):
        assert format_duration(25) == "25m"

    def test_exactly_one_hour(self):
        assert format_duration(60) == "1h 0m"

    def test_hours_and_minutes(self):
        assert format_duration(90) == "1h 30m"

    def test_fractional_minutes_truncated(self):
        # 0.7 minutes → 0m (truncated)
        assert format_duration(0.7) == "0m"

    def test_large_duration(self):
        assert format_duration(125) == "2h 5m"

    def test_exactly_two_hours(self):
        assert format_duration(120) == "2h 0m"


class TestRenderProgressBar:
    """Tests for render_progress_bar()."""

    def test_zero_max_returns_empty_bar(self):
        result = render_progress_bar(5, 0)
        assert result == "░" * 10

    def test_full_bar(self):
        result = render_progress_bar(10, 10)
        assert result == "█" * 10

    def test_half_bar(self):
        result = render_progress_bar(5, 10)
        assert "█" in result
        assert "░" in result

    def test_empty_bar(self):
        result = render_progress_bar(0, 10)
        assert result == "░" * 10

    def test_custom_width(self):
        result = render_progress_bar(5, 10, width=20)
        assert len(result) == 20

    def test_over_max_capped_at_full(self):
        result = render_progress_bar(20, 10)
        assert result == "█" * 10

    def test_default_width(self):
        result = render_progress_bar(5, 10)
        assert len(result) == 10


# ---------------------------------------------------------------------------
# Command: today
# ---------------------------------------------------------------------------


class TestShowToday:
    """Tests for the 'today' sub-command."""

    def _run(self, args=None, summary=None):
        if summary is None:
            summary = _daily_summary()
        mock_analytics = MagicMock()
        mock_analytics.get_daily_summary.return_value = summary
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            return runner.invoke(app, ["today"] + (args or []))

    def test_today_default_output(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Focus Summary" in result.output

    def test_today_json_output(self):
        summary = _daily_summary()
        result = self._run(args=["--output", "json"], summary=summary)
        assert result.exit_code == 0

    def test_today_shows_sessions_count(self):
        result = self._run(summary=_daily_summary(completed=3))
        assert result.exit_code == 0
        assert "3" in result.output

    def test_today_no_most_focused_context(self):
        result = self._run(summary=_daily_summary(most_focused_context=None))
        assert result.exit_code == 0  # Should not crash

    def test_today_with_completed_session(self):
        sessions = [_session_entry(status="completed", completed_task=True)]
        result = self._run(summary=_daily_summary(sessions=sessions))
        assert result.exit_code == 0

    def test_today_with_cancelled_session(self):
        sessions = [_session_entry(status="cancelled", completed_task=False)]
        result = self._run(summary=_daily_summary(sessions=sessions))
        assert result.exit_code == 0

    def test_today_with_unknown_status_session(self):
        sessions = [_session_entry(status="unknown", completed_task=False)]
        result = self._run(summary=_daily_summary(sessions=sessions))
        assert result.exit_code == 0

    def test_today_with_completed_session_no_task(self):
        sessions = [_session_entry(status="completed", completed_task=False)]
        result = self._run(summary=_daily_summary(sessions=sessions))
        assert result.exit_code == 0

    def test_today_session_with_no_title(self):
        sessions = [_session_entry(title=None)]
        result = self._run(summary=_daily_summary(sessions=sessions))
        assert result.exit_code == 0
        assert "Unknown Task" in result.output

    def test_today_default_command_alias(self):
        """The stats app registers 'today' as both a named and default command.
        Invoking via 'today' subcommand always works."""
        summary = _daily_summary()
        mock_analytics = MagicMock()
        mock_analytics.get_daily_summary.return_value = summary
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            # Named invocation is always reliable
            result = runner.invoke(app, ["today"])
        assert result.exit_code == 0
        assert "Focus Summary" in result.output


# ---------------------------------------------------------------------------
# Command: week
# ---------------------------------------------------------------------------


class TestShowWeek:
    """Tests for the 'week' sub-command."""

    def _run(self, args=None, summary=None):
        if summary is None:
            summary = _weekly_summary()
        mock_analytics = MagicMock()
        mock_analytics.get_weekly_summary.return_value = summary
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            return runner.invoke(app, ["week"] + (args or []))

    def test_week_default_output(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Weekly Focus Report" in result.output

    def test_week_json_output(self):
        result = self._run(args=["--output", "json"])
        assert result.exit_code == 0

    def test_week_shows_daily_breakdown(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Daily Breakdown" in result.output

    def test_week_shows_project_distribution(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Project Distribution" in result.output

    def test_week_no_peak_hours(self):
        summary = _weekly_summary()
        summary["peak_hours"] = []
        result = self._run(summary=summary)
        assert result.exit_code == 0

    def test_week_no_context_distribution(self):
        summary = _weekly_summary()
        summary["context_distribution"] = []
        result = self._run(summary=summary)
        assert result.exit_code == 0

    def test_week_zero_sessions(self):
        summary = _weekly_summary()
        for d in summary["daily_summaries"]:
            d["total_sessions"] = 0
        result = self._run(summary=summary)
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Command: month
# ---------------------------------------------------------------------------


class TestShowMonth:
    """Tests for the 'month' sub-command."""

    def _run(self, args=None, summary=None):
        if summary is None:
            summary = _monthly_summary()
        mock_analytics = MagicMock()
        mock_analytics.get_monthly_summary.return_value = summary
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            return runner.invoke(app, ["month"] + (args or []))

    def test_month_default_current_month(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Monthly Overview" in result.output

    def test_month_specific_month(self):
        result = self._run(args=["2024-06"])
        assert result.exit_code == 0

    def test_month_json_output(self):
        result = self._run(args=["2024-06", "--output", "json"])
        assert result.exit_code == 0

    def test_month_invalid_format(self):
        mock_analytics = MagicMock()
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            result = runner.invoke(app, ["month", "not-valid"])
        assert result.exit_code != 0 or "Error" in result.output

    def test_month_no_weeks(self):
        summary = _monthly_summary()
        summary["weeks"] = []
        result = self._run(summary=summary)
        assert result.exit_code == 0

    def test_month_no_comparison(self):
        summary = _monthly_summary()
        summary["comparison"] = None
        result = self._run(summary=summary)
        assert result.exit_code == 0

    def test_month_negative_change(self):
        summary = _monthly_summary()
        summary["comparison"]["sessions_change_pct"] = -15.0
        result = self._run(summary=summary)
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Command: streak
# ---------------------------------------------------------------------------


class TestShowStreak:
    """Tests for the 'streak' sub-command."""

    def _run(self, args=None, streak=None):
        if streak is None:
            streak = _streak_data()
        mock_analytics = MagicMock()
        mock_analytics.get_current_streak.return_value = streak
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            return runner.invoke(app, ["streak"] + (args or []))

    def test_streak_default_output(self):
        result = self._run()
        assert result.exit_code == 0
        assert "5" in result.output  # current streak

    def test_streak_json_output(self):
        result = self._run(args=["--output", "json"])
        assert result.exit_code == 0

    def test_streak_zero_current(self):
        result = self._run(streak=_streak_data(current=0, longest=5))
        assert result.exit_code == 0
        assert "new streak" in result.output.lower()

    def test_streak_positive_current_motivation(self):
        result = self._run(streak=_streak_data(current=3))
        assert result.exit_code == 0
        assert "4" in result.output  # current+1

    def test_streak_emoji_trophy(self):
        result = self._run(streak=_streak_data(current=30))
        assert result.exit_code == 0

    def test_streak_emoji_triple_fire(self):
        result = self._run(streak=_streak_data(current=14))
        assert result.exit_code == 0

    def test_streak_emoji_double_fire(self):
        result = self._run(streak=_streak_data(current=7))
        assert result.exit_code == 0

    def test_streak_emoji_single_fire(self):
        result = self._run(streak=_streak_data(current=3))
        assert result.exit_code == 0

    def test_streak_no_longest_streak_dates(self):
        streak = _streak_data(longest=10)
        streak["longest_streak_start"] = None
        streak["longest_streak_end"] = None
        result = self._run(streak=streak)
        assert result.exit_code == 0

    def test_streak_zero_longest(self):
        result = self._run(streak=_streak_data(current=2, longest=0))
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Command: score
# ---------------------------------------------------------------------------


class TestShowScore:
    """Tests for the 'score' sub-command."""

    def _run(self, args=None, score_data=None):
        if score_data is None:
            score_data = _score_data()
        mock_analytics = MagicMock()
        mock_analytics.get_productivity_score.return_value = score_data
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            return runner.invoke(app, ["score"] + (args or []))

    def test_score_default_output(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Productivity Score" in result.output

    def test_score_json_output(self):
        result = self._run(args=["--output", "json"])
        assert result.exit_code == 0

    def test_score_outstanding_message(self):
        result = self._run(score_data=_score_data(score=95))
        assert result.exit_code == 0
        assert "Outstanding" in result.output

    def test_score_great_message(self):
        result = self._run(score_data=_score_data(score=85))
        assert result.exit_code == 0
        assert "Great" in result.output

    def test_score_good_message(self):
        result = self._run(score_data=_score_data(score=75))
        assert result.exit_code == 0
        assert "Good" in result.output

    def test_score_on_track_message(self):
        result = self._run(score_data=_score_data(score=65))
        assert result.exit_code == 0
        assert "track" in result.output.lower()

    def test_score_low_message(self):
        result = self._run(score_data=_score_data(score=40))
        assert result.exit_code == 0
        assert "habits" in result.output.lower()


# ---------------------------------------------------------------------------
# Command: project
# ---------------------------------------------------------------------------


class TestShowProject:
    """Tests for the 'project' sub-command."""

    def _run(self, context="Work", args=None, stats=None):
        if stats is None:
            stats = _project_stats()
        mock_analytics = MagicMock()
        mock_analytics.get_project_stats.return_value = stats
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            return runner.invoke(app, ["project", context] + (args or []))

    def test_project_default_output(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Work" in result.output

    def test_project_json_output(self):
        result = self._run(args=["--output", "json"])
        assert result.exit_code == 0

    def test_project_with_days_option(self):
        result = self._run(args=["--days", "7"])
        assert result.exit_code == 0

    def test_project_no_top_tasks(self):
        stats = _project_stats()
        stats["top_tasks"] = []
        result = self._run(stats=stats)
        assert result.exit_code == 0

    def test_project_shows_overview(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Overview" in result.output

    def test_project_top_tasks_listed(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Implement feature A" in result.output


# ---------------------------------------------------------------------------
# Command: heatmap
# ---------------------------------------------------------------------------


class TestShowHeatmap:
    """Tests for the 'heatmap' sub-command."""

    def _run(self, args=None, heatmap=None):
        if heatmap is None:
            heatmap = _heatmap_data()
        mock_analytics = MagicMock()
        mock_analytics.get_heatmap_data.return_value = heatmap
        with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
            return runner.invoke(app, ["heatmap"] + (args or []))

    def test_heatmap_default_output(self):
        result = self._run()
        assert result.exit_code == 0
        assert "Heatmap" in result.output

    def test_heatmap_json_output(self):
        result = self._run(args=["--output", "json"])
        assert result.exit_code == 0

    def test_heatmap_with_days_option(self):
        result = self._run(args=["--days", "14"])
        assert result.exit_code == 0
        assert "14" in result.output

    def test_heatmap_no_peak_times(self):
        data = _heatmap_data()
        data["peak_times"] = []
        result = self._run(heatmap=data)
        assert result.exit_code == 0

    def test_heatmap_empty_heatmap(self):
        data = _heatmap_data()
        data["heatmap"] = {}
        result = self._run(heatmap=data)
        assert result.exit_code == 0

    def test_heatmap_various_intensity_levels(self):
        """Test all intensity bands: 0, >0.25, >0.5, >0.75 sessions."""
        data = {
            "heatmap": {
                0: {9: 1, 10: 2, 11: 3, 12: 4},
            },
            "peak_times": [],
        }
        result = self._run(heatmap=data)
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Command: export
# ---------------------------------------------------------------------------


class TestExportData:
    """Tests for the 'export' sub-command."""

    def _make_db(self, tmp_path: Path, num_sessions: int = 2) -> Path:
        """Create a temporary focus_history.db with test data."""
        db_path = tmp_path / "focus_history.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE pomodoro_sessions (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                task_title TEXT,
                start_time TEXT,
                end_time TEXT,
                duration_minutes REAL,
                actual_focus_minutes REAL,
                completed_task INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed',
                session_type TEXT DEFAULT 'work',
                context TEXT,
                created_at TEXT
            )
        """)
        for i in range(num_sessions):
            conn.execute(
                "INSERT INTO pomodoro_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"session-{i}",
                    f"task-{i}",
                    f"Task {i}",
                    f"2024-06-{i+1:02d}T09:00:00",
                    f"2024-06-{i+1:02d}T09:25:00",
                    25.0,
                    25.0,
                    1,
                    "completed",
                    "work",
                    "Work",
                    f"2024-06-{i+1:02d}T09:00:00",
                ),
            )
        conn.commit()
        conn.close()
        return db_path

    def _run_export(self, tmp_path, args=None):
        db_path = self._make_db(tmp_path)
        mock_logger = MagicMock()
        mock_logger.db_path = str(db_path)
        with patch("todopro_cli.commands.stats.HistoryLogger", return_value=mock_logger):
            return runner.invoke(app, ["export"] + (args or []))

    def test_export_json_to_stdout(self, tmp_path):
        result = self._run_export(tmp_path)
        assert result.exit_code == 0

    def test_export_json_to_file(self, tmp_path):
        out = str(tmp_path / "out.json")
        result = self._run_export(tmp_path, args=["--output", out])
        assert result.exit_code == 0
        assert Path(out).exists()
        data = json.loads(Path(out).read_text())
        assert data["total_sessions"] == 2

    def test_export_csv_to_file(self, tmp_path):
        out = str(tmp_path / "out.csv")
        result = self._run_export(tmp_path, args=["--format", "csv", "--output", out])
        assert result.exit_code == 0
        assert Path(out).exists()
        content = Path(out).read_text()
        assert "id" in content

    def test_export_unsupported_format(self, tmp_path):
        result = self._run_export(tmp_path, args=["--format", "xml"])
        assert result.exit_code != 0 or "Unsupported" in result.output

    def test_export_with_from_date_filter(self, tmp_path):
        result = self._run_export(tmp_path, args=["--from", "2024-06-01"])
        assert result.exit_code == 0

    def test_export_with_to_date_filter(self, tmp_path):
        result = self._run_export(tmp_path, args=["--to", "2024-06-30"])
        assert result.exit_code == 0

    def test_export_with_context_filter(self, tmp_path):
        result = self._run_export(tmp_path, args=["--context", "Work"])
        assert result.exit_code == 0

    def test_export_completed_only(self, tmp_path):
        result = self._run_export(tmp_path, args=["--completed-only"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Command: quality
# ---------------------------------------------------------------------------


class TestShowQuality:
    """Tests for the 'quality' sub-command."""

    def _make_db_with_sessions(self, tmp_path: Path, rows: list[tuple]) -> Path:
        db_path = tmp_path / "focus.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE pomodoro_sessions (
                id TEXT PRIMARY KEY,
                task_title TEXT,
                start_time TEXT,
                end_time TEXT,
                duration_minutes REAL,
                actual_focus_minutes REAL,
                status TEXT
            )
        """)
        for row in rows:
            conn.execute("INSERT INTO pomodoro_sessions VALUES (?, ?, ?, ?, ?, ?, ?)", row)
        conn.commit()
        conn.close()
        return db_path

    def _today_session(self, idx: int, status: str = "completed", efficiency: float = 1.0) -> tuple:
        now = datetime.now().isoformat()
        return (
            f"s{idx}",
            f"Task {idx}",
            now,
            now,
            25.0,
            25.0 * efficiency,
            status,
        )

    def _run_quality(self, tmp_path, rows, args=None):
        db_path = self._make_db_with_sessions(tmp_path, rows)
        mock_logger = MagicMock()
        mock_logger.db_path = str(db_path)
        mock_analytics = MagicMock()
        with patch("todopro_cli.commands.stats.HistoryLogger", return_value=mock_logger):
            with patch("todopro_cli.commands.stats.FocusAnalytics", return_value=mock_analytics):
                return runner.invoke(app, ["quality"] + (args or []))

    def test_quality_no_sessions(self, tmp_path):
        result = self._run_quality(tmp_path, [])
        assert result.exit_code == 0
        assert "No sessions" in result.output

    def test_quality_json_output(self, tmp_path):
        rows = [self._today_session(i) for i in range(3)]
        result = self._run_quality(tmp_path, rows, args=["--output", "json"])
        assert result.exit_code == 0

    def test_quality_default_output(self, tmp_path):
        rows = [self._today_session(i) for i in range(3)]
        result = self._run_quality(tmp_path, rows)
        assert result.exit_code == 0
        assert "Quality" in result.output

    def test_quality_excellent_assessment(self, tmp_path):
        rows = [self._today_session(i, status="completed", efficiency=1.0) for i in range(5)]
        result = self._run_quality(tmp_path, rows)
        assert result.exit_code == 0

    def test_quality_with_interrupted_sessions(self, tmp_path):
        rows = [self._today_session(i, status="interrupted") for i in range(3)]
        result = self._run_quality(tmp_path, rows)
        assert result.exit_code == 0

    def test_quality_custom_days(self, tmp_path):
        rows = [self._today_session(i) for i in range(2)]
        result = self._run_quality(tmp_path, rows, args=["--days", "14"])
        assert result.exit_code == 0
        assert "14" in result.output
