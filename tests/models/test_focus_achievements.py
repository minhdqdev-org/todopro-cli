"""Comprehensive unit tests for todopro_cli.models.focus.achievements.

Coverage strategy
-----------------
* ``FocusAnalytics`` is patched to avoid opening any SQLite databases.
* All DB-querying private methods on ``AchievementTracker`` are patched
  so tests remain fast and filesystem-independent.
* ``AchievementTracker.achievements`` (not set in ``__init__``) is injected
  directly onto the instance where methods require it.
* ``AchievementTracker.config`` (used by ``get_earned_achievements`` and
  ``get_progress``) is injected as a MagicMock.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.models.focus.achievements import (
    ACHIEVEMENTS,
    Achievement,
    AchievementCreate,
    AchievementTracker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_analytics(mocker):
    """Patch FocusAnalytics in the achievements module.

    Returns the *instance* mock with sensible "zero-data" defaults.
    """
    mock_cls = mocker.patch("todopro_cli.models.focus.achievements.FocusAnalytics")
    inst = mock_cls.return_value
    inst.get_current_streak.return_value = {"current_streak": 0, "longest_streak": 0}
    return inst


@pytest.fixture()
def tracker(mock_analytics) -> AchievementTracker:
    """AchievementTracker with analytics mocked and state injected."""
    t = AchievementTracker()
    # Inject the dict that check_achievements / _check_requirement rely on
    t.achievements = {"earned": [], "last_check": None}
    # Inject a mock config for get_earned_achievements / get_progress
    t.config = MagicMock()
    t.config.achievements = {"earned": [], "progress": {}, "last_check": None}
    return t


def _patch_db_methods(tracker_instance, **overrides):
    """Patch all DB-touching private methods on *tracker_instance*.

    Default return values all represent 'no data'.  Pass keyword arguments
    to override individual methods, e.g. ``_get_total_sessions=5``.
    """
    defaults = {
        "_get_total_sessions": 0,
        "_get_total_hours": 0.0,
        "_get_max_daily_sessions": 0,
        "_get_max_daily_hours": 0.0,
        "_get_perfect_session_count": 0,
        "_get_high_efficiency_count": 0,
        "_has_early_session": False,
        "_has_late_session": False,
        "_get_max_weekend_sessions": 0,
    }
    defaults.update(overrides)
    for name, value in defaults.items():
        setattr(tracker_instance, name, MagicMock(return_value=value))


# ---------------------------------------------------------------------------
# Achievement data class
# ---------------------------------------------------------------------------


class TestAchievement:
    def test_init_stores_attributes(self):
        a = Achievement(
            id="test_id",
            name="Test Name",
            description="A description",
            icon="🏆",
            requirement={"type": "total_sessions", "value": 5},
        )
        assert a.id == "test_id"
        assert a.name == "Test Name"
        assert a.description == "A description"
        assert a.icon == "🏆"
        assert a.requirement == {"type": "total_sessions", "value": 5}

    def test_requirement_stored_as_dict(self):
        a = Achievement("x", "X", "desc", "✨", {"type": "streak", "value": 7})
        assert isinstance(a.requirement, dict)


# ---------------------------------------------------------------------------
# ACHIEVEMENTS constant
# ---------------------------------------------------------------------------


class TestAchievementsConstant:
    def test_achievements_is_list(self):
        assert isinstance(ACHIEVEMENTS, list)

    def test_achievements_not_empty(self):
        assert len(ACHIEVEMENTS) > 0

    def test_all_achievements_have_ids(self):
        for a in ACHIEVEMENTS:
            assert a.id, f"Achievement missing id: {a}"

    def test_achievement_ids_are_unique(self):
        ids = [a.id for a in ACHIEVEMENTS]
        assert len(ids) == len(set(ids))

    def test_known_achievement_ids_present(self):
        ids = {a.id for a in ACHIEVEMENTS}
        for expected in ("first_session", "streak_7", "hours_10", "perfect_day"):
            assert expected in ids

    def test_all_achievements_are_achievement_instances(self):
        for a in ACHIEVEMENTS:
            assert isinstance(a, Achievement)


# ---------------------------------------------------------------------------
# AchievementTracker.__init__
# ---------------------------------------------------------------------------


class TestAchievementTrackerInit:
    def test_init_creates_instance(self, mock_analytics):
        t = AchievementTracker()
        assert t is not None

    def test_init_creates_analytics_attribute(self, mock_analytics):
        t = AchievementTracker()
        assert hasattr(t, "analytics")


# ---------------------------------------------------------------------------
# _check_requirement
# ---------------------------------------------------------------------------


class TestCheckRequirement:
    """Tests for AchievementTracker._check_requirement()."""

    def test_total_sessions_met(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=10)
        assert tracker._check_requirement({"type": "total_sessions", "value": 10}) is True

    def test_total_sessions_not_met(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=5)
        assert tracker._check_requirement({"type": "total_sessions", "value": 10}) is False

    def test_streak_met_via_current(self, tracker, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 7,
            "longest_streak": 3,
        }
        _patch_db_methods(tracker)
        assert tracker._check_requirement({"type": "streak", "value": 7}) is True

    def test_streak_met_via_longest(self, tracker, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 2,
            "longest_streak": 14,
        }
        _patch_db_methods(tracker)
        assert tracker._check_requirement({"type": "streak", "value": 14}) is True

    def test_streak_not_met(self, tracker, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 1,
            "longest_streak": 2,
        }
        _patch_db_methods(tracker)
        assert tracker._check_requirement({"type": "streak", "value": 7}) is False

    def test_total_hours_met(self, tracker):
        _patch_db_methods(tracker, _get_total_hours=10.5)
        assert tracker._check_requirement({"type": "total_hours", "value": 10}) is True

    def test_total_hours_not_met(self, tracker):
        _patch_db_methods(tracker, _get_total_hours=5.0)
        assert tracker._check_requirement({"type": "total_hours", "value": 10}) is False

    def test_daily_sessions_met(self, tracker):
        _patch_db_methods(tracker, _get_max_daily_sessions=8)
        assert tracker._check_requirement({"type": "daily_sessions", "value": 8}) is True

    def test_daily_sessions_not_met(self, tracker):
        _patch_db_methods(tracker, _get_max_daily_sessions=3)
        assert tracker._check_requirement({"type": "daily_sessions", "value": 8}) is False

    def test_daily_hours_met(self, tracker):
        _patch_db_methods(tracker, _get_max_daily_hours=7.0)
        assert tracker._check_requirement({"type": "daily_hours", "value": 6}) is True

    def test_daily_hours_not_met(self, tracker):
        _patch_db_methods(tracker, _get_max_daily_hours=2.0)
        assert tracker._check_requirement({"type": "daily_hours", "value": 6}) is False

    def test_perfect_sessions_met(self, tracker):
        _patch_db_methods(tracker, _get_perfect_session_count=10)
        assert tracker._check_requirement({"type": "perfect_sessions", "value": 10}) is True

    def test_perfect_sessions_not_met(self, tracker):
        _patch_db_methods(tracker, _get_perfect_session_count=5)
        assert tracker._check_requirement({"type": "perfect_sessions", "value": 10}) is False

    def test_high_efficiency_met(self, tracker):
        _patch_db_methods(tracker, _get_high_efficiency_count=20)
        assert tracker._check_requirement({"type": "high_efficiency", "value": 20}) is True

    def test_high_efficiency_not_met(self, tracker):
        _patch_db_methods(tracker, _get_high_efficiency_count=5)
        assert tracker._check_requirement({"type": "high_efficiency", "value": 20}) is False

    def test_early_session_true(self, tracker):
        _patch_db_methods(tracker, _has_early_session=True)
        assert tracker._check_requirement({"type": "early_session", "value": 6}) is True

    def test_early_session_false(self, tracker):
        _patch_db_methods(tracker, _has_early_session=False)
        assert tracker._check_requirement({"type": "early_session", "value": 6}) is False

    def test_late_session_true(self, tracker):
        _patch_db_methods(tracker, _has_late_session=True)
        assert tracker._check_requirement({"type": "late_session", "value": 22}) is True

    def test_late_session_false(self, tracker):
        _patch_db_methods(tracker, _has_late_session=False)
        assert tracker._check_requirement({"type": "late_session", "value": 22}) is False

    def test_weekend_sessions_met(self, tracker):
        _patch_db_methods(tracker, _get_max_weekend_sessions=5)
        assert tracker._check_requirement({"type": "weekend_sessions", "value": 5}) is True

    def test_weekend_sessions_not_met(self, tracker):
        _patch_db_methods(tracker, _get_max_weekend_sessions=2)
        assert tracker._check_requirement({"type": "weekend_sessions", "value": 5}) is False

    def test_unknown_requirement_type_returns_false(self, tracker):
        _patch_db_methods(tracker)
        assert tracker._check_requirement({"type": "unknown_type", "value": 1}) is False


# ---------------------------------------------------------------------------
# check_achievements
# ---------------------------------------------------------------------------


class TestCheckAchievements:
    def test_returns_list(self, tracker):
        _patch_db_methods(tracker)
        result = tracker.check_achievements()
        assert isinstance(result, list)

    def test_empty_when_no_requirements_met(self, tracker):
        _patch_db_methods(tracker)
        result = tracker.check_achievements()
        assert result == []

    def test_first_session_achievement_earned(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=1)
        result = tracker.check_achievements()
        ids = [a.id for a in result]
        assert "first_session" in ids

    def test_earned_achievement_added_to_state(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=1)
        tracker.check_achievements()
        assert "first_session" in tracker.achievements["earned"]

    def test_already_earned_not_returned_again(self, tracker):
        tracker.achievements["earned"] = ["first_session"]
        _patch_db_methods(tracker, _get_total_sessions=1)
        result = tracker.check_achievements()
        # first_session should not appear again
        ids = [a.id for a in result]
        assert "first_session" not in ids

    def test_multiple_achievements_can_be_earned_at_once(self, tracker, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 3,
            "longest_streak": 3,
        }
        _patch_db_methods(tracker, _get_total_sessions=10)
        result = tracker.check_achievements()
        ids = [a.id for a in result]
        assert "first_session" in ids
        assert "sessions_10" in ids
        assert "streak_3" in ids

    def test_last_check_updated_after_call(self, tracker):
        _patch_db_methods(tracker)
        tracker.check_achievements()
        assert tracker.achievements["last_check"] is not None

    def test_no_duplicates_in_earned_list(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=1)
        tracker.check_achievements()
        tracker.check_achievements()  # second call
        count = tracker.achievements["earned"].count("first_session")
        assert count == 1


# ---------------------------------------------------------------------------
# get_earned_achievements
# ---------------------------------------------------------------------------


class TestGetEarnedAchievements:
    def test_returns_list(self, tracker):
        tracker.config.achievements = {"earned": []}
        result = tracker.get_earned_achievements()
        assert isinstance(result, list)

    def test_empty_when_nothing_earned(self, tracker):
        tracker.config.achievements = {"earned": []}
        result = tracker.get_earned_achievements()
        assert result == []

    def test_returns_matching_achievement_objects(self, tracker):
        tracker.config.achievements = {"earned": ["first_session"]}
        result = tracker.get_earned_achievements()
        assert len(result) == 1
        assert result[0].id == "first_session"

    def test_multiple_earned_achievements(self, tracker):
        tracker.config.achievements = {"earned": ["first_session", "sessions_10"]}
        result = tracker.get_earned_achievements()
        ids = {a.id for a in result}
        assert ids == {"first_session", "sessions_10"}

    def test_unknown_ids_are_ignored(self, tracker):
        tracker.config.achievements = {"earned": ["nonexistent_id"]}
        result = tracker.get_earned_achievements()
        assert result == []


# ---------------------------------------------------------------------------
# _get_current_value
# ---------------------------------------------------------------------------


class TestGetCurrentValue:
    def test_total_sessions(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=42)
        assert tracker._get_current_value({"type": "total_sessions", "value": 10}) == 42

    def test_streak_uses_max_of_current_and_longest(self, tracker, mock_analytics):
        mock_analytics.get_current_streak.return_value = {
            "current_streak": 3,
            "longest_streak": 12,
        }
        _patch_db_methods(tracker)
        assert tracker._get_current_value({"type": "streak", "value": 7}) == 12

    def test_total_hours(self, tracker):
        _patch_db_methods(tracker, _get_total_hours=55.5)
        assert tracker._get_current_value({"type": "total_hours", "value": 50}) == 55.5

    def test_daily_sessions(self, tracker):
        _patch_db_methods(tracker, _get_max_daily_sessions=8)
        assert tracker._get_current_value({"type": "daily_sessions", "value": 8}) == 8

    def test_daily_hours(self, tracker):
        _patch_db_methods(tracker, _get_max_daily_hours=6.5)
        assert tracker._get_current_value({"type": "daily_hours", "value": 6}) == 6.5

    def test_perfect_sessions(self, tracker):
        _patch_db_methods(tracker, _get_perfect_session_count=15)
        assert tracker._get_current_value({"type": "perfect_sessions", "value": 10}) == 15

    def test_high_efficiency(self, tracker):
        _patch_db_methods(tracker, _get_high_efficiency_count=25)
        assert tracker._get_current_value({"type": "high_efficiency", "value": 20}) == 25

    def test_weekend_sessions(self, tracker):
        _patch_db_methods(tracker, _get_max_weekend_sessions=7)
        assert tracker._get_current_value({"type": "weekend_sessions", "value": 5}) == 7

    def test_unknown_type_returns_zero(self, tracker):
        _patch_db_methods(tracker)
        assert tracker._get_current_value({"type": "unknown", "value": 1}) == 0


# ---------------------------------------------------------------------------
# _get_progress_percentage
# ---------------------------------------------------------------------------


class TestGetProgressPercentage:
    def test_zero_sessions_zero_percent(self, tracker):
        _patch_db_methods(tracker)
        pct = tracker._get_progress_percentage({"type": "total_sessions", "value": 10})
        assert pct == 0.0

    def test_half_sessions_fifty_percent(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=5)
        pct = tracker._get_progress_percentage({"type": "total_sessions", "value": 10})
        assert pct == pytest.approx(50.0)

    def test_goal_met_equals_100_percent(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=10)
        pct = tracker._get_progress_percentage({"type": "total_sessions", "value": 10})
        assert pct == 100.0

    def test_exceeds_goal_capped_at_100(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=200)
        pct = tracker._get_progress_percentage({"type": "total_sessions", "value": 10})
        assert pct == 100.0

    def test_zero_required_returns_zero(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=5)
        pct = tracker._get_progress_percentage({"type": "total_sessions", "value": 0})
        assert pct == 0.0


# ---------------------------------------------------------------------------
# get_progress
# ---------------------------------------------------------------------------


class TestGetProgress:
    def test_returns_dict(self, tracker):
        _patch_db_methods(tracker)
        tracker.config.achievements = {"earned": []}
        result = tracker.get_progress()
        assert isinstance(result, dict)

    def test_all_unearned_achievements_in_progress(self, tracker):
        _patch_db_methods(tracker)
        tracker.config.achievements = {"earned": []}
        result = tracker.get_progress()
        # All ACHIEVEMENTS should appear as keys
        assert len(result) == len(ACHIEVEMENTS)

    def test_earned_achievements_excluded_from_progress(self, tracker):
        _patch_db_methods(tracker)
        tracker.config.achievements = {"earned": ["first_session"]}
        result = tracker.get_progress()
        assert "first_session" not in result

    def test_progress_entry_has_required_fields(self, tracker):
        _patch_db_methods(tracker)
        tracker.config.achievements = {"earned": []}
        result = tracker.get_progress()
        for _id, entry in result.items():
            assert "achievement" in entry
            assert "current" in entry
            assert "required" in entry
            assert "percentage" in entry

    def test_progress_percentage_partial(self, tracker):
        _patch_db_methods(tracker, _get_total_sessions=5)
        tracker.config.achievements = {"earned": []}
        result = tracker.get_progress()
        # sessions_10 needs 10; we have 5 → 50%
        assert result["sessions_10"]["percentage"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# AchievementCreate
# ---------------------------------------------------------------------------


class TestAchievementCreate:
    def test_init_stores_all_fields(self):
        ac = AchievementCreate(
            name="Custom",
            description="A custom achievement",
            icon="🎖️",
            requirement={"type": "total_sessions", "value": 42},
        )
        assert ac.name == "Custom"
        assert ac.description == "A custom achievement"
        assert ac.icon == "🎖️"
        assert ac.requirement == {"type": "total_sessions", "value": 42}

    def test_all_attributes_accessible(self):
        """Every field set in __init__ is reachable as an attribute (line 488)."""
        ac = AchievementCreate(
            name="Persistent",
            description="Still there",
            icon="⭐",
            requirement={"type": "streak", "value": 7},
        )
        assert ac.name == "Persistent"
        assert ac.description == "Still there"
        assert ac.icon == "⭐"
        assert ac.requirement["value"] == 7


# ---------------------------------------------------------------------------
# DB query private methods (real SQLite, tmp path)
# ---------------------------------------------------------------------------
# These tests exercise the actual SQL queries in _get_total_sessions,
# _get_total_hours, etc., by pointing HistoryLogger at a real temp DB file.
# ---------------------------------------------------------------------------


import sqlite3 as _sqlite3
import tempfile
import os as _os


def _create_pomodoro_db(tmp_path_str: str) -> str:
    """Create a pomodoro_sessions DB at the given directory, return the db path."""
    db_path = _os.path.join(tmp_path_str, "focus_history.db")
    conn = _sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pomodoro_sessions (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            task_title TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            actual_focus_minutes INTEGER,
            completed_task INTEGER DEFAULT 0,
            status TEXT,
            session_type TEXT,
            context TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    return db_path


def _insert_session(db_path, sid, start_time, duration, actual=None, status="completed"):
    conn = _sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO pomodoro_sessions (id, start_time, end_time, duration_minutes, actual_focus_minutes, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sid, start_time, start_time, duration, actual if actual is not None else duration, status, start_time),
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def db_path(tmp_path, mocker):
    """Create a temp DB and patch HistoryLogger to point at it."""
    path = str(tmp_path)
    real_db = _create_pomodoro_db(path)

    # Create a mock HistoryLogger whose db_path points to the real temp DB
    from pathlib import Path

    mock_logger = MagicMock()
    mock_logger.db_path = Path(real_db)

    mocker.patch(
        "todopro_cli.models.focus.history.HistoryLogger",
        return_value=mock_logger,
    )
    return real_db


@pytest.fixture()
def db_tracker(mock_analytics) -> AchievementTracker:
    """AchievementTracker suitable for testing DB methods."""
    t = AchievementTracker()
    t.config = MagicMock()
    t.config.achievements = {"earned": []}
    return t


class TestGetTotalSessions:
    def test_returns_zero_when_empty(self, db_path, db_tracker):
        assert db_tracker._get_total_sessions() == 0

    def test_counts_completed_sessions(self, db_path, db_tracker):
        _insert_session(db_path, "s1", "2024-01-01T09:00:00", 25)
        _insert_session(db_path, "s2", "2024-01-01T10:00:00", 25)
        assert db_tracker._get_total_sessions() == 2

    def test_ignores_non_completed_sessions(self, db_path, db_tracker):
        _insert_session(db_path, "s3", "2024-01-01T11:00:00", 25, status="interrupted")
        assert db_tracker._get_total_sessions() == 0


class TestGetTotalHours:
    def test_returns_zero_when_empty(self, db_path, db_tracker):
        assert db_tracker._get_total_hours() == pytest.approx(0.0)

    def test_sums_actual_focus_minutes(self, db_path, db_tracker):
        _insert_session(db_path, "h1", "2024-01-01T09:00:00", 60, actual=60)
        _insert_session(db_path, "h2", "2024-01-01T10:00:00", 30, actual=30)
        assert db_tracker._get_total_hours() == pytest.approx(1.5)


class TestGetMaxDailySessions:
    def test_returns_zero_when_empty(self, db_path, db_tracker):
        assert db_tracker._get_max_daily_sessions() == 0

    def test_finds_max_across_days(self, db_path, db_tracker):
        # Day 1: 3 sessions
        for i, hour in enumerate(["08", "09", "10"]):
            _insert_session(db_path, f"d1-{i}", f"2024-01-01T{hour}:00:00", 25)
        # Day 2: 1 session
        _insert_session(db_path, "d2-0", "2024-01-02T09:00:00", 25)
        assert db_tracker._get_max_daily_sessions() == 3


class TestGetMaxDailyHours:
    def test_returns_zero_when_empty(self, db_path, db_tracker):
        assert db_tracker._get_max_daily_hours() == pytest.approx(0.0)

    def test_finds_max_day(self, db_path, db_tracker):
        _insert_session(db_path, "dh1", "2024-01-01T09:00:00", 120, actual=120)
        _insert_session(db_path, "dh2", "2024-01-02T09:00:00", 30, actual=30)
        assert db_tracker._get_max_daily_hours() == pytest.approx(2.0)


class TestGetPerfectSessionCount:
    def test_returns_zero_when_empty(self, db_path, db_tracker):
        assert db_tracker._get_perfect_session_count() == 0

    def test_counts_sessions_where_actual_ge_duration(self, db_path, db_tracker):
        _insert_session(db_path, "p1", "2024-01-01T09:00:00", 25, actual=25)
        _insert_session(db_path, "p2", "2024-01-01T10:00:00", 25, actual=20)  # not perfect
        _insert_session(db_path, "p3", "2024-01-01T11:00:00", 25, actual=30)  # over duration = perfect
        assert db_tracker._get_perfect_session_count() == 2


class TestGetHighEfficiencyCount:
    def test_returns_zero_when_empty(self, db_path, db_tracker):
        assert db_tracker._get_high_efficiency_count() == 0

    def test_counts_sessions_at_95_percent_efficiency(self, db_path, db_tracker):
        _insert_session(db_path, "e1", "2024-01-01T09:00:00", 100, actual=95)  # exactly 95%
        _insert_session(db_path, "e2", "2024-01-01T10:00:00", 100, actual=94)  # just below
        assert db_tracker._get_high_efficiency_count() == 1


class TestHasEarlySession:
    def test_returns_false_when_empty(self, db_path, db_tracker):
        assert db_tracker._has_early_session(6) is False

    def test_returns_true_when_session_before_hour(self, db_path, db_tracker):
        _insert_session(db_path, "early1", "2024-01-01T05:30:00", 25)
        assert db_tracker._has_early_session(6) is True

    def test_returns_false_when_no_session_before_hour(self, db_path, db_tracker):
        _insert_session(db_path, "late1", "2024-01-01T09:00:00", 25)
        assert db_tracker._has_early_session(6) is False


class TestHasLateSession:
    def test_returns_false_when_empty(self, db_path, db_tracker):
        assert db_tracker._has_late_session(22) is False

    def test_returns_true_when_session_at_or_after_hour(self, db_path, db_tracker):
        _insert_session(db_path, "late2", "2024-01-01T22:30:00", 25)
        assert db_tracker._has_late_session(22) is True

    def test_returns_false_when_all_sessions_before_hour(self, db_path, db_tracker):
        _insert_session(db_path, "early2", "2024-01-01T10:00:00", 25)
        assert db_tracker._has_late_session(22) is False


class TestGetMaxWeekendSessions:
    def test_returns_zero_when_empty(self, db_path, db_tracker):
        assert db_tracker._get_max_weekend_sessions() == 0

    def test_returns_zero_when_only_weekday_sessions(self, db_path, db_tracker):
        # 2024-01-01 is a Monday (strftime %w = 1)
        _insert_session(db_path, "wd1", "2024-01-01T09:00:00", 25)
        assert db_tracker._get_max_weekend_sessions() == 0

    def test_counts_saturday_sessions(self, db_path, db_tracker):
        # 2024-01-06 is a Saturday (strftime %w = 6)
        _insert_session(db_path, "sat1", "2024-01-06T09:00:00", 25)
        _insert_session(db_path, "sat2", "2024-01-06T10:00:00", 25)
        assert db_tracker._get_max_weekend_sessions() == 2

    def test_counts_sunday_sessions(self, db_path, db_tracker):
        # 2024-01-07 is a Sunday (strftime %w = 0)
        _insert_session(db_path, "sun1", "2024-01-07T09:00:00", 25)
        assert db_tracker._get_max_weekend_sessions() == 1
