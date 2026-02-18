"""Goals and targets for focus sessions."""

from typing import Any

from todopro_cli.focus.analytics import FocusAnalytics
from todopro_cli.services.context_manager import get_context_manager


class GoalsManager:
    """Manage focus goals and track progress."""

    def __init__(self, profile: str = "default"):
        """Initialize goals manager."""
        self.context_manager = get_context_manager(profile)
        self.config = self.context_manager.load_config()
        self.analytics = FocusAnalytics()

    def get_goals(self) -> dict[str, Any]:
        """Get current goals configuration."""
        if self.config.focus_goals:
            return self.config.focus_goals

        # Return defaults
        return {
            "daily_sessions": 8,
            "daily_minutes": 200,  # 3h 20m
            "weekly_sessions": 40,
            "weekly_minutes": 1000,  # ~16h 40m
            "streak_target": 30,
        }

    def set_goal(self, goal_type: str, value: int) -> None:
        """
        Set a specific goal.

        Args:
            goal_type: Type of goal (daily_sessions, daily_minutes, etc.)
            value: Target value
        """
        if self.config.focus_goals is None:
            self.config.focus_goals = self.get_goals()

        valid_types = [
            "daily_sessions",
            "daily_minutes",
            "weekly_sessions",
            "weekly_minutes",
            "streak_target",
        ]

        if goal_type not in valid_types:
            raise ValueError(
                f"Invalid goal type: {goal_type}. Must be one of {valid_types}"
            )

        self.config.focus_goals[goal_type] = value
        self.context_manager.save_config(self.config)

    def get_daily_progress(self) -> dict[str, Any]:
        """Get progress toward daily goals."""
        goals = self.get_goals()
        daily = self.analytics.get_daily_summary()

        sessions_progress = (
            (daily["total_sessions"] / goals["daily_sessions"] * 100)
            if goals["daily_sessions"] > 0
            else 0
        )
        minutes_progress = (
            (daily["total_focus_minutes"] / goals["daily_minutes"] * 100)
            if goals["daily_minutes"] > 0
            else 0
        )

        return {
            "sessions": {
                "current": daily["total_sessions"],
                "target": goals["daily_sessions"],
                "progress": min(sessions_progress, 100),
                "achieved": daily["total_sessions"] >= goals["daily_sessions"],
            },
            "minutes": {
                "current": daily["total_focus_minutes"],
                "target": goals["daily_minutes"],
                "progress": min(minutes_progress, 100),
                "achieved": daily["total_focus_minutes"] >= goals["daily_minutes"],
            },
        }

    def get_weekly_progress(self) -> dict[str, Any]:
        """Get progress toward weekly goals."""
        goals = self.get_goals()
        weekly = self.analytics.get_weekly_summary()

        sessions_progress = (
            (weekly["total_sessions"] / goals["weekly_sessions"] * 100)
            if goals["weekly_sessions"] > 0
            else 0
        )
        minutes_progress = (
            (weekly["total_focus_minutes"] / goals["weekly_minutes"] * 100)
            if goals["weekly_minutes"] > 0
            else 0
        )

        return {
            "sessions": {
                "current": weekly["total_sessions"],
                "target": goals["weekly_sessions"],
                "progress": min(sessions_progress, 100),
                "achieved": weekly["total_sessions"] >= goals["weekly_sessions"],
            },
            "minutes": {
                "current": weekly["total_focus_minutes"],
                "target": goals["weekly_minutes"],
                "progress": min(minutes_progress, 100),
                "achieved": weekly["total_focus_minutes"] >= goals["weekly_minutes"],
            },
        }

    def get_streak_progress(self) -> dict[str, Any]:
        """Get progress toward streak target."""
        goals = self.get_goals()
        streak = self.analytics.get_current_streak()

        current = streak["current_streak"]
        target = goals["streak_target"]
        progress = (current / target * 100) if target > 0 else 0

        return {
            "current": current,
            "target": target,
            "progress": min(progress, 100),
            "achieved": current >= target,
            "longest": streak["longest_streak"],
        }

    def get_all_progress(self) -> dict[str, Any]:
        """Get progress for all goals."""
        return {
            "daily": self.get_daily_progress(),
            "weekly": self.get_weekly_progress(),
            "streak": self.get_streak_progress(),
        }

    def check_achievements(self) -> list[str]:
        """Check for recently achieved goals."""
        achievements = []

        daily = self.get_daily_progress()
        if daily["sessions"]["achieved"]:
            achievements.append("daily_sessions")
        if daily["minutes"]["achieved"]:
            achievements.append("daily_minutes")

        weekly = self.get_weekly_progress()
        if weekly["sessions"]["achieved"]:
            achievements.append("weekly_sessions")
        if weekly["minutes"]["achieved"]:
            achievements.append("weekly_minutes")

        streak = self.get_streak_progress()
        if streak["achieved"]:
            achievements.append("streak_target")

        return achievements
