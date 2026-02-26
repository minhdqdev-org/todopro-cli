"""Comprehensive unit tests for HistoryLogger.

Uses a real SQLite database in a temporary directory.  Tests cover
schema initialisation, session logging, all query methods, and
the delete_old_sessions maintenance utility.

DB schema (from history.py _init_database):
    id, task_id, task_title, start_time, end_time,
    duration_minutes, actual_focus_minutes, completed_task,
    status, session_type, context, created_at
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from todopro_cli.models.focus.history import HistoryLogger
from todopro_cli.models.focus.state import SessionState, SessionStateManager


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Temporary SQLite file path."""
    return tmp_path / "history_test.db"


@pytest.fixture()
def logger(db_path: Path) -> HistoryLogger:
    """HistoryLogger backed by a tmp file."""
    return HistoryLogger(db_path=db_path)


@pytest.fixture()
def db_conn(db_path: Path, logger: HistoryLogger):
    """
    Raw sqlite3 connection to the DB (logger fixture ensures schema is created
    before the connection is opened).
    """
    with sqlite3.connect(db_path) as conn:
        yield conn


def _make_session(
    *,
    session_id: str = "test-session",
    task_id: str | None = "task-1",
    task_title: str | None = "Test Task",
    duration_minutes: int = 25,
    status: str = "completed",
    session_type: str = "focus",
    context: str = "default",
    accumulated_paused_seconds: int = 0,
    start_offset_days: int = 0,
) -> SessionState:
    """Create a SessionState suitable for log_session tests."""
    now = datetime.now() - timedelta(days=start_offset_days)
    end = now + timedelta(minutes=duration_minutes)
    return SessionState(
        session_id=session_id,
        task_id=task_id,
        task_title=task_title,
        start_time=now.isoformat(),
        end_time=end.isoformat(),
        duration_minutes=duration_minutes,
        status=status,
        session_type=session_type,
        context=context,
        accumulated_paused_seconds=accumulated_paused_seconds,
    )


def _insert(
    conn: sqlite3.Connection,
    *,
    id: str,
    start_time: str,
    end_time: str,
    duration_minutes: int,
    actual_focus_minutes: int,
    completed_task: int = 0,
    status: str = "completed",
    session_type: str = "focus",
    context: str = "default",
    task_id: str | None = None,
    task_title: str | None = None,
    created_at: str | None = None,
) -> None:
    """Insert a row directly into pomodoro_sessions."""
    if created_at is None:
        created_at = datetime.now().isoformat()
    conn.execute(
        """
        INSERT INTO pomodoro_sessions
            (id, task_id, task_title, start_time, end_time,
             duration_minutes, actual_focus_minutes, completed_task,
             status, session_type, context, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            id,
            task_id,
            task_title,
            start_time,
            end_time,
            duration_minutes,
            actual_focus_minutes,
            completed_task,
            status,
            session_type,
            context,
            created_at,
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------


class TestHistoryLoggerInit:
    """Tests for HistoryLogger construction and schema creation."""

    def test_creates_db_file(self, db_path: Path, logger: HistoryLogger) -> None:
        """The SQLite file should exist after instantiation."""
        assert db_path.exists()

    def test_creates_pomodoro_sessions_table(
        self, db_path: Path, logger: HistoryLogger
    ) -> None:
        """The pomodoro_sessions table must be present after init."""
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pomodoro_sessions'"
            ).fetchone()
        assert row is not None

    def test_creates_required_indexes(
        self, db_path: Path, logger: HistoryLogger
    ) -> None:
        """The three indexes (date, task, status) should be created."""
        with sqlite3.connect(db_path) as conn:
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        assert "idx_sessions_date" in indexes
        assert "idx_sessions_task" in indexes
        assert "idx_sessions_status" in indexes

    def test_init_is_idempotent(self, db_path: Path) -> None:
        """Creating two HistoryLoggers pointing to the same file should not crash."""
        HistoryLogger(db_path=db_path)
        HistoryLogger(db_path=db_path)  # second call — should not raise

    def test_db_path_stored_on_instance(
        self, db_path: Path, logger: HistoryLogger
    ) -> None:
        """logger.db_path should equal the path passed in the constructor."""
        assert logger.db_path == db_path

    def test_parent_directory_created(self, tmp_path: Path) -> None:
        """HistoryLogger creates intermediate directories automatically."""
        deep_path = tmp_path / "a" / "b" / "c" / "test.db"
        logger = HistoryLogger(db_path=deep_path)
        assert deep_path.exists()


# ---------------------------------------------------------------------------
# log_session
# ---------------------------------------------------------------------------


class TestLogSession:
    """Tests for HistoryLogger.log_session()."""

    def test_inserts_row_into_db(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """After log_session, exactly one row appears in the table."""
        session = _make_session(session_id="s1")
        logger.log_session(session)

        count = db_conn.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions"
        ).fetchone()[0]
        assert count == 1

    def test_stored_fields_match_session(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """All key fields are persisted with the correct values."""
        session = _make_session(
            session_id="s-check",
            task_id="t99",
            task_title="My Task",
            duration_minutes=25,
            status="completed",
            session_type="focus",
            context="work",
        )
        logger.log_session(session, completed_task=True)

        row = db_conn.execute(
            "SELECT * FROM pomodoro_sessions WHERE id = ?", ("s-check",)
        ).fetchone()
        assert row is not None

        # Map columns by index: id(0), task_id(1), task_title(2), start_time(3),
        # end_time(4), duration_minutes(5), actual_focus_minutes(6),
        # completed_task(7), status(8), session_type(9), context(10), created_at(11)
        assert row[1] == "t99"
        assert row[2] == "My Task"
        assert row[5] == 25        # duration_minutes
        assert row[7] == 1         # completed_task
        assert row[8] == "completed"
        assert row[9] == "focus"
        assert row[10] == "work"

    def test_actual_focus_minutes_excludes_paused_time(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """actual_focus_minutes = duration_minutes - (paused_seconds // 60)."""
        session = _make_session(
            session_id="paused",
            duration_minutes=25,
            accumulated_paused_seconds=300,  # 5 minutes paused
        )
        logger.log_session(session)

        row = db_conn.execute(
            "SELECT actual_focus_minutes FROM pomodoro_sessions WHERE id = 'paused'"
        ).fetchone()
        # actual = (25*60 - 300) // 60 = 1200 // 60 = 20
        assert row[0] == 20

    def test_actual_focus_minutes_never_negative(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """If paused > duration, actual_focus_minutes is 0 (not negative)."""
        session = _make_session(
            session_id="over-paused",
            duration_minutes=5,
            accumulated_paused_seconds=3600,  # 60 minutes paused
        )
        logger.log_session(session)

        row = db_conn.execute(
            "SELECT actual_focus_minutes FROM pomodoro_sessions WHERE id = 'over-paused'"
        ).fetchone()
        assert row[0] == 0

    def test_completed_task_false_stored_as_zero(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """completed_task=False → integer 0 in the database."""
        session = _make_session(session_id="not-done")
        logger.log_session(session, completed_task=False)

        row = db_conn.execute(
            "SELECT completed_task FROM pomodoro_sessions WHERE id = 'not-done'"
        ).fetchone()
        assert row[0] == 0

    def test_null_task_id_and_title_accepted(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Sessions without a task_id/task_title should still be logged."""
        session = _make_session(
            session_id="no-task",
            task_id=None,
            task_title=None,
        )
        logger.log_session(session)

        row = db_conn.execute(
            "SELECT task_id, task_title FROM pomodoro_sessions WHERE id = 'no-task'"
        ).fetchone()
        assert row[0] is None
        assert row[1] is None

    def test_multiple_sessions_all_inserted(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Multiple consecutive log_session calls each produce a distinct row."""
        for i in range(5):
            session = _make_session(session_id=f"multi-{i}")
            logger.log_session(session)

        count = db_conn.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions"
        ).fetchone()[0]
        assert count == 5


# ---------------------------------------------------------------------------
# get_recent_sessions
# ---------------------------------------------------------------------------


class TestGetRecentSessions:
    """Tests for HistoryLogger.get_recent_sessions()."""

    def test_empty_db_returns_empty_list(self, logger: HistoryLogger) -> None:
        """With no sessions, get_recent_sessions returns []."""
        assert logger.get_recent_sessions() == []

    def test_returns_list_of_dicts(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Each element in the result is a dict with the expected keys."""
        _insert(
            db_conn,
            id="r1",
            start_time="2024-06-15T09:00:00",
            end_time="2024-06-15T09:25:00",
            duration_minutes=25,
            actual_focus_minutes=25,
        )

        results = logger.get_recent_sessions()

        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert "id" in results[0]
        assert "start_time" in results[0]
        assert "status" in results[0]

    def test_ordered_most_recent_first(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Sessions are returned in descending start_time order."""
        for i, hour in enumerate([9, 10, 11]):
            _insert(
                db_conn,
                id=f"ord{i}",
                start_time=f"2024-06-15T{hour:02d}:00:00",
                end_time=f"2024-06-15T{hour:02d}:25:00",
                duration_minutes=25,
                actual_focus_minutes=25,
            )

        results = logger.get_recent_sessions()

        assert results[0]["id"] == "ord2"  # 11am — most recent
        assert results[-1]["id"] == "ord0"  # 9am — oldest

    def test_limit_respected(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """At most `limit` sessions are returned."""
        for i in range(10):
            _insert(
                db_conn,
                id=f"lim{i}",
                start_time=f"2024-06-{15 + i // 10:02d}T{8 + i:02d}:00:00",
                end_time=f"2024-06-{15 + i // 10:02d}T{8 + i:02d}:25:00",
                duration_minutes=25,
                actual_focus_minutes=25,
            )

        results = logger.get_recent_sessions(limit=3)

        assert len(results) == 3

    def test_session_type_filter(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Passing session_type filters out non-matching sessions."""
        _insert(
            db_conn,
            id="focus1",
            start_time="2024-06-15T09:00:00",
            end_time="2024-06-15T09:25:00",
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
        )
        _insert(
            db_conn,
            id="break1",
            start_time="2024-06-15T09:30:00",
            end_time="2024-06-15T09:35:00",
            duration_minutes=5,
            actual_focus_minutes=5,
            session_type="short_break",
        )

        results_focus = logger.get_recent_sessions(session_type="focus")
        results_break = logger.get_recent_sessions(session_type="short_break")

        assert all(r["session_type"] == "focus" for r in results_focus)
        assert all(r["session_type"] == "short_break" for r in results_break)
        assert len(results_focus) == 1
        assert len(results_break) == 1

    def test_no_session_type_filter_returns_all(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Without session_type filter, all sessions are returned."""
        for sid, stype in [("f1", "focus"), ("b1", "short_break"), ("lb1", "long_break")]:
            _insert(
                db_conn,
                id=sid,
                start_time="2024-06-15T09:00:00",
                end_time="2024-06-15T09:25:00",
                duration_minutes=25,
                actual_focus_minutes=25,
                session_type=stype,
            )

        results = logger.get_recent_sessions()

        assert len(results) == 3


# ---------------------------------------------------------------------------
# get_sessions_by_task
# ---------------------------------------------------------------------------


class TestGetSessionsByTask:
    """Tests for HistoryLogger.get_sessions_by_task()."""

    def test_empty_db_returns_empty_list(self, logger: HistoryLogger) -> None:
        """With no sessions, returns []."""
        assert logger.get_sessions_by_task("task-xyz") == []

    def test_returns_only_matching_task_sessions(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Only sessions for the given task_id are returned."""
        _insert(
            db_conn,
            id="s-a",
            start_time="2024-06-15T09:00:00",
            end_time="2024-06-15T09:25:00",
            duration_minutes=25,
            actual_focus_minutes=25,
            task_id="task-A",
        )
        _insert(
            db_conn,
            id="s-b",
            start_time="2024-06-15T10:00:00",
            end_time="2024-06-15T10:25:00",
            duration_minutes=25,
            actual_focus_minutes=25,
            task_id="task-B",
        )

        results = logger.get_sessions_by_task("task-A")

        assert len(results) == 1
        assert results[0]["id"] == "s-a"

    def test_returns_all_sessions_for_task(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Multiple sessions for the same task are all returned."""
        for i in range(3):
            _insert(
                db_conn,
                id=f"ts{i}",
                start_time=f"2024-06-{15 + i:02d}T09:00:00",
                end_time=f"2024-06-{15 + i:02d}T09:25:00",
                duration_minutes=25,
                actual_focus_minutes=25,
                task_id="my-task",
            )

        results = logger.get_sessions_by_task("my-task")

        assert len(results) == 3

    def test_ordered_most_recent_first(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Results are ordered by start_time descending."""
        for i in range(3):
            _insert(
                db_conn,
                id=f"order{i}",
                start_time=f"2024-06-{10 + i:02d}T09:00:00",
                end_time=f"2024-06-{10 + i:02d}T09:25:00",
                duration_minutes=25,
                actual_focus_minutes=25,
                task_id="ordertask",
            )

        results = logger.get_sessions_by_task("ordertask")

        assert results[0]["id"] == "order2"
        assert results[-1]["id"] == "order0"

    def test_returns_list_of_dicts(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Each element is a dict with an 'id' key."""
        _insert(
            db_conn,
            id="dict-check",
            start_time="2024-06-15T09:00:00",
            end_time="2024-06-15T09:25:00",
            duration_minutes=25,
            actual_focus_minutes=25,
            task_id="t1",
        )

        results = logger.get_sessions_by_task("t1")

        assert isinstance(results[0], dict)
        assert "id" in results[0]


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    """Tests for HistoryLogger.get_stats()."""

    def test_empty_db_returns_all_zeros(self, logger: HistoryLogger) -> None:
        """With no sessions, all stats are 0."""
        stats = logger.get_stats()

        assert stats["total_sessions"] == 0
        assert stats["completed_sessions"] == 0
        assert stats["cancelled_sessions"] == 0
        assert stats["completion_rate"] == 0.0
        assert stats["total_focus_minutes"] == 0
        assert stats["total_focus_hours"] == 0.0
        assert stats["tasks_completed"] == 0
        assert stats["avg_session_length"] == 0.0

    def test_counts_only_focus_sessions(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """get_stats only counts sessions with session_type = 'focus'."""
        now = datetime.now()
        _insert(
            db_conn,
            id="focus-s",
            start_time=now.isoformat(),
            end_time=(now + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
            status="completed",
        )
        _insert(
            db_conn,
            id="break-s",
            start_time=now.isoformat(),
            end_time=(now + timedelta(minutes=5)).isoformat(),
            duration_minutes=5,
            actual_focus_minutes=5,
            session_type="short_break",
            status="completed",
        )

        stats = logger.get_stats()

        assert stats["total_sessions"] == 1

    def test_total_and_completed_counts(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """total_sessions and completed_sessions reflect actual DB state."""
        now = datetime.now()
        for i, status in enumerate(["completed", "completed", "cancelled"]):
            _insert(
                db_conn,
                id=f"st{i}",
                start_time=(now - timedelta(hours=i)).isoformat(),
                end_time=(now - timedelta(hours=i) + timedelta(minutes=25)).isoformat(),
                duration_minutes=25,
                actual_focus_minutes=25,
                session_type="focus",
                status=status,
            )

        stats = logger.get_stats()

        assert stats["total_sessions"] == 3
        assert stats["completed_sessions"] == 2
        assert stats["cancelled_sessions"] == 1

    def test_completion_rate_percentage(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """completion_rate = completed / total * 100, rounded to 1 decimal."""
        now = datetime.now()
        for i, status in enumerate(["completed", "cancelled", "cancelled", "cancelled"]):
            _insert(
                db_conn,
                id=f"cr{i}",
                start_time=(now - timedelta(hours=i)).isoformat(),
                end_time=(now - timedelta(hours=i) + timedelta(minutes=25)).isoformat(),
                duration_minutes=25,
                actual_focus_minutes=25,
                session_type="focus",
                status=status,
            )

        stats = logger.get_stats()

        assert stats["completion_rate"] == 25.0

    def test_total_focus_minutes_and_hours(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """total_focus_minutes and total_focus_hours are summed correctly."""
        now = datetime.now()
        for i, mins in enumerate([30, 60]):
            _insert(
                db_conn,
                id=f"time{i}",
                start_time=(now - timedelta(hours=i)).isoformat(),
                end_time=(now - timedelta(hours=i) + timedelta(minutes=mins)).isoformat(),
                duration_minutes=mins,
                actual_focus_minutes=mins,
                session_type="focus",
                status="completed",
            )

        stats = logger.get_stats()

        assert stats["total_focus_minutes"] == 90
        assert stats["total_focus_hours"] == round(90 / 60, 1)

    def test_tasks_completed_count(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """tasks_completed counts sessions where completed_task = 1."""
        now = datetime.now()
        _insert(
            db_conn,
            id="tc1",
            start_time=now.isoformat(),
            end_time=(now + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
            status="completed",
            completed_task=1,
        )
        _insert(
            db_conn,
            id="tc2",
            start_time=(now - timedelta(hours=1)).isoformat(),
            end_time=(now - timedelta(hours=1) + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
            status="completed",
            completed_task=0,
        )

        stats = logger.get_stats()

        assert stats["tasks_completed"] == 1

    def test_avg_session_length(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """avg_session_length = total_focus_minutes / total_sessions."""
        now = datetime.now()
        for i, mins in enumerate([20, 30, 40]):
            _insert(
                db_conn,
                id=f"avg{i}",
                start_time=(now - timedelta(hours=i)).isoformat(),
                end_time=(now - timedelta(hours=i) + timedelta(minutes=mins)).isoformat(),
                duration_minutes=mins,
                actual_focus_minutes=mins,
                session_type="focus",
                status="completed",
            )

        stats = logger.get_stats()

        assert stats["avg_session_length"] == round(90 / 3, 1)

    def test_days_window_excludes_old_sessions(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Sessions older than `days` are excluded from the stats."""
        now = datetime.now()
        old = now - timedelta(days=30)

        _insert(
            db_conn,
            id="recent",
            start_time=now.isoformat(),
            end_time=(now + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
            status="completed",
        )
        _insert(
            db_conn,
            id="old",
            start_time=old.isoformat(),
            end_time=(old + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
            status="completed",
        )

        stats = logger.get_stats(days=7)

        assert stats["total_sessions"] == 1


# ---------------------------------------------------------------------------
# get_daily_summary (HistoryLogger method)
# ---------------------------------------------------------------------------


class TestHistoryLoggerGetDailySummary:
    """Tests for HistoryLogger.get_daily_summary()."""

    def test_empty_db_returns_zero_totals(self, logger: HistoryLogger) -> None:
        """With no sessions, totals are 0."""
        summary = logger.get_daily_summary("2024-06-15")

        assert summary["date"] == "2024-06-15"
        assert summary["total_sessions"] == 0
        assert summary["total_minutes"] == 0
        assert summary["total_hours"] == 0.0

    def test_counts_only_focus_sessions_on_date(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """get_daily_summary counts focus sessions on the given date."""
        _insert(
            db_conn,
            id="focus-today",
            start_time="2024-06-15T09:00:00",
            end_time="2024-06-15T09:25:00",
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
            status="completed",
        )
        _insert(
            db_conn,
            id="break-today",
            start_time="2024-06-15T09:30:00",
            end_time="2024-06-15T09:35:00",
            duration_minutes=5,
            actual_focus_minutes=5,
            session_type="short_break",
            status="completed",
        )

        summary = logger.get_daily_summary("2024-06-15")

        assert summary["total_sessions"] == 1
        assert summary["total_minutes"] == 25

    def test_excludes_other_dates(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Sessions on a different date do not appear in the summary."""
        _insert(
            db_conn,
            id="other",
            start_time="2024-06-16T09:00:00",
            end_time="2024-06-16T09:25:00",
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
        )

        summary = logger.get_daily_summary("2024-06-15")

        assert summary["total_sessions"] == 0

    def test_total_hours_rounded(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """total_hours is minutes/60 rounded to 1 decimal place."""
        _insert(
            db_conn,
            id="long",
            start_time="2024-06-15T09:00:00",
            end_time="2024-06-15T10:30:00",
            duration_minutes=90,
            actual_focus_minutes=90,
            session_type="focus",
        )

        summary = logger.get_daily_summary("2024-06-15")

        assert summary["total_minutes"] == 90
        assert summary["total_hours"] == 1.5

    def test_defaults_to_today(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Calling get_daily_summary() with no args uses today's date."""
        today = datetime.now()
        _insert(
            db_conn,
            id="today",
            start_time=today.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(),
            end_time=today.replace(hour=9, minute=25, second=0, microsecond=0).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
            session_type="focus",
        )

        summary = logger.get_daily_summary()

        assert summary["date"] == today.date().isoformat()
        assert summary["total_sessions"] == 1


# ---------------------------------------------------------------------------
# delete_old_sessions
# ---------------------------------------------------------------------------


class TestDeleteOldSessions:
    """Tests for HistoryLogger.delete_old_sessions()."""

    def test_deletes_sessions_older_than_cutoff(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Sessions older than `days` are removed."""
        old = datetime.now() - timedelta(days=100)
        _insert(
            db_conn,
            id="old",
            start_time=old.isoformat(),
            end_time=(old + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
        )

        deleted = logger.delete_old_sessions(days=90)

        assert deleted == 1
        remaining = db_conn.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions"
        ).fetchone()[0]
        assert remaining == 0

    def test_keeps_recent_sessions(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Sessions within the cutoff window are preserved."""
        now = datetime.now()
        _insert(
            db_conn,
            id="recent",
            start_time=(now - timedelta(days=10)).isoformat(),
            end_time=(now - timedelta(days=10) + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
        )

        logger.delete_old_sessions(days=90)

        remaining = db_conn.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions"
        ).fetchone()[0]
        assert remaining == 1

    def test_returns_correct_count(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """The return value equals the number of sessions actually deleted."""
        now = datetime.now()
        for i in range(5):
            old = now - timedelta(days=100 + i)
            _insert(
                db_conn,
                id=f"del{i}",
                start_time=old.isoformat(),
                end_time=(old + timedelta(minutes=25)).isoformat(),
                duration_minutes=25,
                actual_focus_minutes=25,
            )
        # One recent session — should not be deleted
        _insert(
            db_conn,
            id="keeper",
            start_time=(now - timedelta(days=5)).isoformat(),
            end_time=(now - timedelta(days=5) + timedelta(minutes=25)).isoformat(),
            duration_minutes=25,
            actual_focus_minutes=25,
        )

        deleted = logger.delete_old_sessions(days=90)

        assert deleted == 5

    def test_returns_zero_when_nothing_to_delete(
        self, logger: HistoryLogger
    ) -> None:
        """Returns 0 when there are no sessions older than the cutoff."""
        result = logger.delete_old_sessions(days=90)
        assert result == 0

    def test_mixed_old_and_recent_sessions(
        self, logger: HistoryLogger, db_conn: sqlite3.Connection
    ) -> None:
        """Only old sessions are deleted; recent ones survive."""
        now = datetime.now()
        old = now - timedelta(days=200)

        for i in range(3):
            _insert(
                db_conn,
                id=f"old{i}",
                start_time=(old + timedelta(days=i)).isoformat(),
                end_time=(old + timedelta(days=i, minutes=25)).isoformat(),
                duration_minutes=25,
                actual_focus_minutes=25,
            )
        for i in range(2):
            _insert(
                db_conn,
                id=f"new{i}",
                start_time=(now - timedelta(days=i)).isoformat(),
                end_time=(now - timedelta(days=i) + timedelta(minutes=25)).isoformat(),
                duration_minutes=25,
                actual_focus_minutes=25,
            )

        deleted = logger.delete_old_sessions(days=90)

        assert deleted == 3
        remaining = db_conn.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions"
        ).fetchone()[0]
        assert remaining == 2
