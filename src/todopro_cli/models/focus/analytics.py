"""Analytics engine for focus sessions."""

import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .history import HistoryLogger


class FocusAnalytics:
    """Compute analytics from focus session history."""

    def __init__(self, history_logger: HistoryLogger | None = None):
        """Initialize analytics engine."""
        self.logger = history_logger or HistoryLogger()
        self.db_path = self.logger.db_path

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute query and return results as list of dicts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def _query_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        """Execute query and return single result."""
        results = self._query(sql, params)
        return results[0] if results else None

    def get_daily_summary(self, date: datetime | None = None) -> dict[str, Any]:
        """
        Get summary for a specific day.

        Args:
            date: Target date (defaults to today)

        Returns:
            Dict with daily metrics
        """
        if date is None:
            date = datetime.now()

        # Get start and end of day in ISO format
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Query sessions for the day
        sessions = self._query(
            """
            SELECT * FROM pomodoro_sessions
            WHERE start_time >= ? AND start_time < ?
            ORDER BY start_time
            """,
            (start_of_day.isoformat(), end_of_day.isoformat()),
        )

        # Compute metrics
        total_sessions = len(sessions)
        completed_sessions = sum(1 for s in sessions if s["status"] == "completed")
        cancelled_sessions = sum(1 for s in sessions if s["status"] == "cancelled")

        total_focus_minutes = sum(s["actual_focus_minutes"] or 0 for s in sessions)
        total_duration_minutes = sum(s["duration_minutes"] for s in sessions)
        break_minutes = total_duration_minutes - total_focus_minutes

        tasks_completed = sum(1 for s in sessions if s["completed_task"])

        # Find most focused project/context
        context_time = defaultdict(int)
        context_sessions = defaultdict(int)
        for s in sessions:
            ctx = s["context"] or "default"
            context_time[ctx] += s["actual_focus_minutes"] or 0
            context_sessions[ctx] += 1

        most_focused_context = None
        if context_time:
            most_focused_context = max(context_time.items(), key=lambda x: x[1])

        return {
            "date": date.date().isoformat(),
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "cancelled_sessions": cancelled_sessions,
            "total_focus_minutes": total_focus_minutes,
            "break_minutes": break_minutes,
            "tasks_completed": tasks_completed,
            "most_focused_context": (
                most_focused_context[0] if most_focused_context else None
            ),
            "most_focused_sessions": (
                most_focused_context[1] if most_focused_context else 0
            ),
            "sessions": sessions,
        }

    def get_weekly_summary(self, end_date: datetime | None = None) -> dict[str, Any]:
        """
        Get summary for the last 7 days.

        Args:
            end_date: End date (defaults to today)

        Returns:
            Dict with weekly metrics
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=6)  # 7 days total including end_date

        # Get daily summaries
        daily_summaries = []
        for i in range(7):
            day = start_date + timedelta(days=i)
            summary = self.get_daily_summary(day)
            daily_summaries.append(summary)

        # Aggregate weekly stats
        total_sessions = sum(d["total_sessions"] for d in daily_summaries)
        total_focus_minutes = sum(d["total_focus_minutes"] for d in daily_summaries)

        # Most productive day
        most_productive = max(daily_summaries, key=lambda x: x["total_sessions"])
        least_productive = min(daily_summaries, key=lambda x: x["total_sessions"])

        # Project distribution
        context_time = defaultdict(int)
        context_sessions = defaultdict(int)
        all_sessions = []
        for d in daily_summaries:
            all_sessions.extend(d["sessions"])

        for s in all_sessions:
            ctx = s["context"] or "default"
            context_time[ctx] += s["actual_focus_minutes"] or 0
            context_sessions[ctx] += 1

        # Peak focus hours (hour of day analysis)
        hour_sessions = defaultdict(int)
        for s in all_sessions:
            start_time = datetime.fromisoformat(s["start_time"].replace("Z", "+00:00"))
            hour = start_time.hour
            hour_sessions[hour] += 1

        peak_hours = sorted(hour_sessions.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "total_sessions": total_sessions,
            "total_focus_minutes": total_focus_minutes,
            "daily_average_sessions": round(total_sessions / 7, 1),
            "daily_average_minutes": round(total_focus_minutes / 7, 1),
            "most_productive_day": {
                "date": most_productive["date"],
                "sessions": most_productive["total_sessions"],
            },
            "least_productive_day": {
                "date": least_productive["date"],
                "sessions": least_productive["total_sessions"],
            },
            "peak_hours": [{"hour": h, "sessions": c} for h, c in peak_hours],
            "context_distribution": [
                {"context": ctx, "sessions": context_sessions[ctx], "minutes": mins}
                for ctx, mins in sorted(
                    context_time.items(), key=lambda x: x[1], reverse=True
                )
            ],
            "daily_summaries": daily_summaries,
        }

    def get_monthly_summary(
        self, year: int | None = None, month: int | None = None
    ) -> dict[str, Any]:
        """
        Get summary for a specific month.

        Args:
            year: Target year (defaults to current)
            month: Target month (defaults to current)

        Returns:
            Dict with monthly metrics
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        # First and last day of month
        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1)
        else:
            end_of_month = datetime(year, month + 1, 1)

        # Query all sessions in month
        sessions = self._query(
            """
            SELECT * FROM pomodoro_sessions
            WHERE start_time >= ? AND start_time < ?
            ORDER BY start_time
            """,
            (start_of_month.isoformat(), end_of_month.isoformat()),
        )

        total_sessions = len(sessions)
        total_focus_minutes = sum(s["actual_focus_minutes"] or 0 for s in sessions)
        completed_tasks = sum(1 for s in sessions if s["completed_task"])
        total_tasks = len(set(s["task_id"] for s in sessions if s["task_id"]))
        completion_rate = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        avg_session_length = (
            (total_focus_minutes / total_sessions) if total_sessions > 0 else 0
        )

        # Week-by-week breakdown
        weeks = []
        current = start_of_month
        while current < end_of_month:
            week_end = min(current + timedelta(days=7), end_of_month)
            week_sessions = [
                s
                for s in sessions
                if current.isoformat() <= s["start_time"] < week_end.isoformat()
            ]
            weeks.append(
                {
                    "start": current.date().isoformat(),
                    "end": (week_end - timedelta(days=1)).date().isoformat(),
                    "sessions": len(week_sessions),
                    "focus_minutes": sum(
                        s["actual_focus_minutes"] or 0 for s in week_sessions
                    ),
                }
            )
            current = week_end

        # Compare with previous month if data exists
        prev_month_start = start_of_month - timedelta(days=28)
        prev_month_start = prev_month_start.replace(day=1)
        prev_sessions = self._query(
            """
            SELECT * FROM pomodoro_sessions
            WHERE start_time >= ? AND start_time < ?
            """,
            (prev_month_start.isoformat(), start_of_month.isoformat()),
        )

        comparison = None
        if prev_sessions:
            prev_total = len(prev_sessions)
            prev_minutes = sum(s["actual_focus_minutes"] or 0 for s in prev_sessions)
            prev_completed = sum(1 for s in prev_sessions if s["completed_task"])
            prev_total_tasks = len(
                set(s["task_id"] for s in prev_sessions if s["task_id"])
            )
            prev_completion_rate = (
                (prev_completed / prev_total_tasks * 100) if prev_total_tasks > 0 else 0
            )

            comparison = {
                "sessions_change_pct": (
                    ((total_sessions - prev_total) / prev_total * 100)
                    if prev_total > 0
                    else 0
                ),
                "minutes_change_pct": (
                    ((total_focus_minutes - prev_minutes) / prev_minutes * 100)
                    if prev_minutes > 0
                    else 0
                ),
                "completion_rate_change_pct": completion_rate - prev_completion_rate,
            }

        return {
            "year": year,
            "month": month,
            "total_sessions": total_sessions,
            "total_focus_minutes": total_focus_minutes,
            "tasks_completed": completed_tasks,
            "completion_rate": round(completion_rate, 1),
            "avg_session_length": round(avg_session_length, 1),
            "weeks": weeks,
            "comparison": comparison,
        }

    def get_current_streak(self) -> dict[str, Any]:
        """
        Calculate current and longest focus streaks.

        A streak is consecutive days with at least 1 completed session.

        Returns:
            Dict with current_streak, longest_streak, and metadata
        """
        # Get all sessions ordered by date
        sessions = self._query("""
            SELECT DISTINCT DATE(start_time) as session_date
            FROM pomodoro_sessions
            WHERE status = 'completed'
            ORDER BY session_date DESC
            """)

        if not sessions:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "longest_streak_start": None,
                "longest_streak_end": None,
            }

        # Convert to date objects
        dates = [datetime.fromisoformat(s["session_date"]).date() for s in sessions]
        today = datetime.now().date()

        # Calculate current streak
        current_streak = 0
        expected_date = today
        for date in dates:
            if date == expected_date:
                current_streak += 1
                expected_date = date - timedelta(days=1)
            elif date < expected_date:
                # Gap found
                break

        # Calculate longest streak
        longest_streak = 0
        longest_start = None
        longest_end = None

        current_run = 1
        run_start = dates[-1]
        run_end = dates[-1]

        for i in range(len(dates) - 1, 0, -1):
            if (dates[i - 1] - dates[i]).days == 1:
                current_run += 1
                run_start = dates[i - 1]
            else:
                if current_run > longest_streak:
                    longest_streak = current_run
                    longest_start = run_start
                    longest_end = run_end
                current_run = 1
                run_start = dates[i - 1]
                run_end = dates[i - 1]

        # Check final run
        if current_run > longest_streak:
            longest_streak = current_run
            longest_start = run_start
            longest_end = run_end

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "longest_streak_start": (
                longest_start.isoformat() if longest_start else None
            ),
            "longest_streak_end": longest_end.isoformat() if longest_end else None,
        }

    def get_productivity_score(self, days: int = 7) -> dict[str, Any]:
        """
        Calculate productivity score (0-100) based on multiple factors.

        Score = (sessions/10 * 30) + (hours/5 * 25) + (completion_rate * 25) + (streak/7 * 20)

        Args:
            days: Number of days to analyze (default 7)

        Returns:
            Dict with score and component breakdown
        """
        # Get weekly summary
        weekly = self.get_weekly_summary()
        streak_data = self.get_current_streak()

        # Component scores (0-100 each)
        sessions_score = min((weekly["total_sessions"] / 10) * 30, 30)
        hours = weekly["total_focus_minutes"] / 60
        time_score = min((hours / 5) * 25, 25)

        # Calculate completion rate
        all_sessions = []
        for d in weekly["daily_summaries"]:
            all_sessions.extend(d["sessions"])

        total_tasks = len(set(s["task_id"] for s in all_sessions if s["task_id"]))
        completed_tasks = len(
            set(
                s["task_id"]
                for s in all_sessions
                if s["task_id"] and s["completed_task"]
            )
        )
        completion_rate = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )
        completion_score = (completion_rate / 100) * 25

        streak_score = min((streak_data["current_streak"] / 7) * 20, 20)

        total_score = round(
            sessions_score + time_score + completion_score + streak_score
        )

        # Grade
        if total_score >= 90:
            grade = "A"
        elif total_score >= 80:
            grade = "B"
        elif total_score >= 70:
            grade = "C"
        elif total_score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": total_score,
            "grade": grade,
            "components": {
                "sessions": {
                    "score": round(sessions_score, 1),
                    "value": weekly["total_sessions"],
                    "max": 10,
                },
                "focus_time": {
                    "score": round(time_score, 1),
                    "value": round(hours, 1),
                    "max": 5,
                },
                "completion": {
                    "score": round(completion_score, 1),
                    "value": round(completion_rate, 1),
                    "max": 100,
                },
                "streak": {
                    "score": round(streak_score, 1),
                    "value": streak_data["current_streak"],
                    "max": 7,
                },
            },
        }

    def get_project_stats(self, context: str, days: int = 30) -> dict[str, Any]:
        """
        Get statistics for a specific project/context.

        Args:
            context: Context/project name
            days: Number of days to analyze

        Returns:
            Dict with project-specific metrics
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        sessions = self._query(
            """
            SELECT * FROM pomodoro_sessions
            WHERE context = ? AND start_time >= ? AND start_time < ?
            ORDER BY start_time
            """,
            (context, start_date.isoformat(), end_date.isoformat()),
        )

        total_sessions = len(sessions)
        total_focus_minutes = sum(s["actual_focus_minutes"] or 0 for s in sessions)

        # Task breakdown
        task_time = defaultdict(int)
        task_titles = {}
        for s in sessions:
            if s["task_id"]:
                task_time[s["task_id"]] += s["actual_focus_minutes"] or 0
                task_titles[s["task_id"]] = s["task_title"]

        top_tasks = sorted(task_time.items(), key=lambda x: x[1], reverse=True)[:5]

        completed_tasks = len(
            set(s["task_id"] for s in sessions if s["completed_task"])
        )
        in_progress = len(
            set(s["task_id"] for s in sessions if not s["completed_task"])
        )

        avg_session = (
            (total_focus_minutes / total_sessions) if total_sessions > 0 else 0
        )

        return {
            "context": context,
            "days": days,
            "total_sessions": total_sessions,
            "total_focus_minutes": total_focus_minutes,
            "tasks_completed": completed_tasks,
            "tasks_in_progress": in_progress,
            "avg_session_minutes": round(avg_session, 1),
            "top_tasks": [
                {
                    "task_id": tid,
                    "title": task_titles.get(tid, "Unknown"),
                    "minutes": mins,
                }
                for tid, mins in top_tasks
            ],
        }

    def get_heatmap_data(self, days: int = 30) -> dict[str, Any]:
        """
        Generate time-of-day heatmap data.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with heatmap grid (day of week x hour)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        sessions = self._query(
            """
            SELECT start_time FROM pomodoro_sessions
            WHERE start_time >= ? AND start_time < ? AND status = 'completed'
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        # Build heatmap grid: [day_of_week][hour] = count
        heatmap = defaultdict(lambda: defaultdict(int))

        for s in sessions:
            dt = datetime.fromisoformat(s["start_time"].replace("Z", "+00:00"))
            day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
            hour = dt.hour
            heatmap[day_of_week][hour] += 1

        # Find peak times
        peak_times = []
        for day in range(7):
            for hour in range(24):
                count = heatmap[day][hour]
                if count > 0:
                    peak_times.append((day, hour, count))

        peak_times.sort(key=lambda x: x[2], reverse=True)

        return {
            "heatmap": {day: dict(hours) for day, hours in heatmap.items()},
            "peak_times": [
                {"day": day, "hour": hour, "sessions": count}
                for day, hour, count in peak_times[:5]
            ],
        }
