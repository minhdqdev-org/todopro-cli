"""Gamification and achievements system for focus sessions."""

import sqlite3
from datetime import datetime
from typing import Any

from .analytics import FocusAnalytics


class Achievement:
    """Represents an achievement badge."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        icon: str,
        requirement: dict[str, Any],
    ):
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon
        self.requirement = requirement


# Define all available achievements
ACHIEVEMENTS = [
    # Streak-based
    Achievement(
        "first_session",
        "Getting Started",
        "Complete your first focus session",
        "🌱",
        {"type": "total_sessions", "value": 1},
    ),
    Achievement(
        "streak_3",
        "Building Momentum",
        "3-day focus streak",
        "🔥",
        {"type": "streak", "value": 3},
    ),
    Achievement(
        "streak_7",
        "Week Warrior",
        "7-day focus streak",
        "🔥🔥",
        {"type": "streak", "value": 7},
    ),
    Achievement(
        "streak_14",
        "Two Week Champion",
        "14-day focus streak",
        "🔥🔥🔥",
        {"type": "streak", "value": 14},
    ),
    Achievement(
        "streak_30",
        "Monthly Master",
        "30-day focus streak",
        "🏆",
        {"type": "streak", "value": 30},
    ),
    Achievement(
        "streak_100",
        "Century Club",
        "100-day focus streak",
        "💯",
        {"type": "streak", "value": 100},
    ),
    # Session count milestones
    Achievement(
        "sessions_10",
        "Decathlon",
        "Complete 10 focus sessions",
        "🎯",
        {"type": "total_sessions", "value": 10},
    ),
    Achievement(
        "sessions_50",
        "Half Century",
        "Complete 50 focus sessions",
        "⭐",
        {"type": "total_sessions", "value": 50},
    ),
    Achievement(
        "sessions_100",
        "Centurion",
        "Complete 100 focus sessions",
        "💪",
        {"type": "total_sessions", "value": 100},
    ),
    Achievement(
        "sessions_500",
        "Focus Master",
        "Complete 500 focus sessions",
        "🧘",
        {"type": "total_sessions", "value": 500},
    ),
    # Time-based
    Achievement(
        "hours_10",
        "10 Hour Hero",
        "Focus for 10 hours total",
        "⏰",
        {"type": "total_hours", "value": 10},
    ),
    Achievement(
        "hours_50",
        "50 Hour Champion",
        "Focus for 50 hours total",
        "⏱️",
        {"type": "total_hours", "value": 50},
    ),
    Achievement(
        "hours_100",
        "Century Timer",
        "Focus for 100 hours total",
        "🕐",
        {"type": "total_hours", "value": 100},
    ),
    # Daily achievements
    Achievement(
        "perfect_day",
        "Perfect Day",
        "Complete 8+ sessions in one day",
        "✨",
        {"type": "daily_sessions", "value": 8},
    ),
    Achievement(
        "marathon",
        "Marathon Focus",
        "Focus for 6+ hours in one day",
        "🏃",
        {"type": "daily_hours", "value": 6},
    ),
    # Quality-based
    Achievement(
        "perfectionist",
        "Perfectionist",
        "Complete 10 sessions with 100% completion rate",
        "💎",
        {"type": "perfect_sessions", "value": 10},
    ),
    Achievement(
        "efficiency_master",
        "Efficiency Master",
        "Maintain 95%+ focus efficiency for 20 sessions",
        "⚡",
        {"type": "high_efficiency", "value": 20},
    ),
    # Special achievements
    Achievement(
        "early_bird",
        "Early Bird",
        "Start a session before 6 AM",
        "🌅",
        {"type": "early_session", "value": 6},
    ),
    Achievement(
        "night_owl",
        "Night Owl",
        "Start a session after 10 PM",
        "🦉",
        {"type": "late_session", "value": 22},
    ),
    Achievement(
        "weekend_warrior",
        "Weekend Warrior",
        "Complete 5+ sessions on a weekend day",
        "🎮",
        {"type": "weekend_sessions", "value": 5},
    ),
]


class AchievementTracker:
    """Tracks and awards achievements based on focus session data."""

    def __init__(self):
        """Initialize achievement tracker."""
        self.analytics = FocusAnalytics()

        # # Initialize achievements storage in config
        # if not hasattr(self.config, "achievements") or self.config.achievements is None:
        #     self.config.achievements = {
        #         "earned": [],
        #         "progress": {},
        #         "last_check": None,
        #     }
        #     self.config_service.save_config(self.config)

    def check_achievements(self) -> list[Achievement]:
        """Check for newly earned achievements."""
        newly_earned = []

        for achievement in ACHIEVEMENTS:
            # Skip if already earned
            if achievement.id in self.achievements["earned"]:
                continue

            # Check if requirement is met
            if self._check_requirement(achievement.requirement):
                newly_earned.append(achievement)
                self.achievements["earned"].append(achievement.id)

        # Update last check time
        self.achievements["last_check"] = datetime.now().isoformat()

        # Save if any new achievements
        # if newly_earned:
        #     self.config_service.save_config(self.config)

        return newly_earned

    def _check_requirement(self, req: dict[str, Any]) -> bool:
        """Check if a requirement is met."""
        req_type = req["type"]
        req_value = req["value"]

        if req_type == "total_sessions":
            total = self._get_total_sessions()
            return total >= req_value

        if req_type == "streak":
            streak_data = self.analytics.get_current_streak()
            current = streak_data.get("current_streak", 0)
            longest = streak_data.get("longest_streak", 0)
            return max(current, longest) >= req_value

        if req_type == "total_hours":
            hours = self._get_total_hours()
            return hours >= req_value

        if req_type == "daily_sessions":
            max_daily = self._get_max_daily_sessions()
            return max_daily >= req_value

        if req_type == "daily_hours":
            max_daily_hours = self._get_max_daily_hours()
            return max_daily_hours >= req_value

        if req_type == "perfect_sessions":
            perfect = self._get_perfect_session_count()
            return perfect >= req_value

        if req_type == "high_efficiency":
            high_eff = self._get_high_efficiency_count()
            return high_eff >= req_value

        if req_type == "early_session":
            return self._has_early_session(req_value)

        if req_type == "late_session":
            return self._has_late_session(req_value)

        if req_type == "weekend_sessions":
            max_weekend = self._get_max_weekend_sessions()
            return max_weekend >= req_value

        return False

    def _get_total_sessions(self) -> int:
        """Get total number of completed sessions."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions WHERE status = 'completed'"
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _get_total_hours(self) -> float:
        """Get total hours of focus time."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(actual_focus_minutes) FROM pomodoro_sessions WHERE status = 'completed'"
        )
        total_minutes = cursor.fetchone()[0] or 0
        conn.close()
        return total_minutes / 60.0

    def _get_max_daily_sessions(self) -> int:
        """Get maximum sessions completed in a single day."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(start_time) as day, COUNT(*) as count
            FROM pomodoro_sessions
            WHERE status = 'completed'
            GROUP BY day
            ORDER BY count DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        return result[1] if result else 0

    def _get_max_daily_hours(self) -> float:
        """Get maximum hours focused in a single day."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(start_time) as day, SUM(actual_focus_minutes) as total
            FROM pomodoro_sessions
            WHERE status = 'completed'
            GROUP BY day
            ORDER BY total DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        return (result[1] / 60.0) if result else 0

    def _get_perfect_session_count(self) -> int:
        """Get count of sessions with 100% completion."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM pomodoro_sessions
            WHERE status = 'completed'
            AND actual_focus_minutes >= duration_minutes
        """)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _get_high_efficiency_count(self) -> int:
        """Get count of sessions with 95%+ efficiency."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM pomodoro_sessions
            WHERE status = 'completed'
            AND (actual_focus_minutes * 100.0 / duration_minutes) >= 95
        """)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _has_early_session(self, hour: int) -> bool:
        """Check if user has started a session before given hour."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pomodoro_sessions
            WHERE CAST(strftime('%H', start_time) AS INTEGER) < ?
        """,
            (hour,),
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def _has_late_session(self, hour: int) -> bool:
        """Check if user has started a session after given hour."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pomodoro_sessions
            WHERE CAST(strftime('%H', start_time) AS INTEGER) >= ?
        """,
            (hour,),
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def _get_max_weekend_sessions(self) -> int:
        """Get maximum sessions on a single weekend day."""
        from .history import HistoryLogger

        logger = HistoryLogger()

        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(start_time) as day, COUNT(*) as count
            FROM pomodoro_sessions
            WHERE status = 'completed'
            AND CAST(strftime('%w', start_time) AS INTEGER) IN (0, 6)
            GROUP BY day
            ORDER BY count DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        return result[1] if result else 0

    def get_earned_achievements(self) -> list[Achievement]:
        """Get list of earned achievements."""
        earned_ids = self.config.achievements.get("earned", [])
        return [a for a in ACHIEVEMENTS if a.id in earned_ids]

    def get_progress(self) -> dict[str, Any]:
        """Get progress toward unearned achievements."""
        progress = {}

        for achievement in ACHIEVEMENTS:
            if achievement.id in self.config.achievements.get("earned", []):
                continue

            req = achievement.requirement
            progress[achievement.id] = {
                "achievement": achievement,
                "current": self._get_current_value(req),
                "required": req["value"],
                "percentage": self._get_progress_percentage(req),
            }

        return progress

    def _get_current_value(self, req: dict[str, Any]) -> Any:
        """Get current value for a requirement type."""
        req_type = req["type"]

        if req_type == "total_sessions":
            return self._get_total_sessions()
        if req_type == "streak":
            streak_data = self.analytics.get_current_streak()
            return max(
                streak_data.get("current_streak", 0),
                streak_data.get("longest_streak", 0),
            )
        if req_type == "total_hours":
            return self._get_total_hours()
        if req_type == "daily_sessions":
            return self._get_max_daily_sessions()
        if req_type == "daily_hours":
            return self._get_max_daily_hours()
        if req_type == "perfect_sessions":
            return self._get_perfect_session_count()
        if req_type == "high_efficiency":
            return self._get_high_efficiency_count()
        if req_type == "weekend_sessions":
            return self._get_max_weekend_sessions()

        return 0

    def _get_progress_percentage(self, req: dict[str, Any]) -> float:
        """Get progress percentage toward requirement."""
        current = self._get_current_value(req)
        required = req["value"]

        if isinstance(current, bool):
            return 100.0 if current else 0.0

        return min((current / required * 100), 100.0) if required > 0 else 0.0


class AchievementCreate:
    """Data model for creating a new achievement (if we want to support custom ones in the future)."""

    def __init__(
        self,
        name: str,
        description: str,
        icon: str,
        requirement: dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.icon = icon
        self.requirement = requirement
