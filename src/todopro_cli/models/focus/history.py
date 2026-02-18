"""Focus session history tracking with SQLite storage."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .state import SessionState


class HistoryLogger:
    """Manages focus session history in SQLite database."""

    def __init__(self, db_path: Path | None = None):
        """Initialize history logger."""
        if db_path is None:
            from platformdirs import user_data_dir

            data_dir = Path(user_data_dir("todopro", "minhdq"))
            db_path = data_dir / "focus_history.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
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
                """
            )

            # Create indexes
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_date 
                ON pomodoro_sessions(start_time)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_task 
                ON pomodoro_sessions(task_id)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_status 
                ON pomodoro_sessions(status)
                """
            )

            conn.commit()

    def log_session(self, session: SessionState, completed_task: bool = False) -> None:
        """
        Log a completed or cancelled session to history.

        Args:
            session: The session to log
            completed_task: Whether the task was marked as completed
        """
        # Calculate actual focus time (excluding paused time)
        total_seconds = session.duration_minutes * 60
        actual_seconds = total_seconds - session.accumulated_paused_seconds
        actual_minutes = max(0, actual_seconds // 60)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO pomodoro_sessions (
                    id, task_id, task_title, start_time, end_time,
                    duration_minutes, actual_focus_minutes, completed_task,
                    status, session_type, context, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.task_id,
                    session.task_title,
                    session.start_time,
                    session.end_time,
                    session.duration_minutes,
                    actual_minutes,
                    1 if completed_task else 0,
                    session.status,
                    session.session_type,
                    session.context,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_recent_sessions(
        self, limit: int = 20, session_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get recent focus sessions.

        Args:
            limit: Maximum number of sessions to return
            session_type: Filter by session type (focus, short_break, long_break)

        Returns:
            List of session dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if session_type:
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions 
                    WHERE session_type = ?
                    ORDER BY start_time DESC 
                    LIMIT ?
                    """,
                    (session_type, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions 
                    ORDER BY start_time DESC 
                    LIMIT ?
                    """,
                    (limit,),
                )

            return [dict(row) for row in cursor.fetchall()]

    def get_sessions_by_task(self, task_id: str) -> list[dict[str, Any]]:
        """Get all sessions for a specific task."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM pomodoro_sessions 
                WHERE task_id = ?
                ORDER BY start_time DESC
                """,
                (task_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self, days: int = 7) -> dict[str, Any]:
        """
        Get focus statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Total sessions
            total = conn.execute(
                """
                SELECT COUNT(*) FROM pomodoro_sessions 
                WHERE start_time >= ? AND session_type = 'focus'
                """,
                (cutoff,),
            ).fetchone()[0]

            # Completed sessions
            completed = conn.execute(
                """
                SELECT COUNT(*) FROM pomodoro_sessions 
                WHERE start_time >= ? 
                AND session_type = 'focus' 
                AND status = 'completed'
                """,
                (cutoff,),
            ).fetchone()[0]

            # Total focus time
            total_minutes = conn.execute(
                """
                SELECT COALESCE(SUM(actual_focus_minutes), 0) 
                FROM pomodoro_sessions 
                WHERE start_time >= ? AND session_type = 'focus'
                """,
                (cutoff,),
            ).fetchone()[0]

            # Tasks completed during focus
            tasks_completed = conn.execute(
                """
                SELECT COUNT(*) FROM pomodoro_sessions 
                WHERE start_time >= ? 
                AND session_type = 'focus' 
                AND completed_task = 1
                """,
                (cutoff,),
            ).fetchone()[0]

            return {
                "total_sessions": total,
                "completed_sessions": completed,
                "cancelled_sessions": total - completed,
                "completion_rate": round(
                    (completed / total * 100) if total > 0 else 0, 1
                ),
                "total_focus_minutes": total_minutes,
                "total_focus_hours": round(total_minutes / 60, 1),
                "tasks_completed": tasks_completed,
                "avg_session_length": round(
                    total_minutes / total if total > 0 else 0, 1
                ),
            }

    def get_daily_summary(self, date: str | None = None) -> dict[str, Any]:
        """
        Get summary for a specific day.

        Args:
            date: ISO date string (YYYY-MM-DD), defaults to today

        Returns:
            Daily summary statistics
        """
        if date is None:
            date = datetime.now().date().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Count sessions for the day
            sessions = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(actual_focus_minutes), 0)
                FROM pomodoro_sessions 
                WHERE DATE(start_time) = ? AND session_type = 'focus'
                """,
                (date,),
            ).fetchone()

            return {
                "date": date,
                "total_sessions": sessions[0],
                "total_minutes": sessions[1],
                "total_hours": round(sessions[1] / 60, 1),
            }

    def delete_old_sessions(self, days: int = 90) -> int:
        """
        Delete sessions older than N days.

        Args:
            days: Keep sessions from last N days

        Returns:
            Number of sessions deleted
        """
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM pomodoro_sessions 
                WHERE start_time < ?
                """,
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount
