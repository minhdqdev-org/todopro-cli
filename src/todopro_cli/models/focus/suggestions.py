"""Smart task suggestions for focus sessions."""

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from todopro_cli.models.config_models import AppConfig

from .analytics import FocusAnalytics
from .history import HistoryLogger


class TaskSuggestionEngine:
    """Generate smart task suggestions based on multiple factors."""

    def __init__(self, config: AppConfig, profile: str = "default"):
        """Initialize suggestion engine.

        Args:
            config: Current application configuration.
            profile: Suggestion profile name (reserved for future use).
        """
        self.config = config
        self.analytics = FocusAnalytics()

    def _get_priority_score(self, task: dict[str, Any]) -> int:
        """Get priority score (higher is more urgent)."""
        priority = task.get("priority", 3)
        # Convert to score: priority 1 (highest) = 3, priority 3 (lowest) = 1
        return 4 - priority

    def _get_due_date_score(self, task: dict[str, Any]) -> float:
        """Get due date urgency score."""
        due_date_str = task.get("due_date")
        if not due_date_str:
            return 0.0  # No due date = low urgency

        try:
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
            now = datetime.now()
            # Handle timezone-aware due dates
            if due_date.tzinfo is not None:
                now = now.astimezone()
            days_until_due = (due_date - now).days

            if days_until_due < 0:
                return 10.0  # Overdue
            if days_until_due == 0:
                return 8.0  # Due today
            if days_until_due == 1:
                return 6.0  # Due tomorrow
            if days_until_due <= 3:
                return 4.0  # Due this week
            if days_until_due <= 7:
                return 2.0  # Due next week
            return 1.0  # Due later
        except (ValueError, AttributeError):
            return 0.0

    def _get_eisenhower_score(self, task: dict[str, Any]) -> float:
        """Get Eisenhower matrix score (urgent + important)."""
        # This is a simplified version - assumes priority 1-2 are important
        priority = task.get("priority", 3)
        is_important = priority <= 2

        # Has due date soon = urgent
        due_score = self._get_due_date_score(task)
        is_urgent = due_score >= 4.0

        if is_important and is_urgent:
            return 4.0  # Do first
        if is_important and not is_urgent:
            return 3.0  # Schedule
        if not is_important and is_urgent:
            return 2.0  # Delegate (or do quickly)
        return 1.0  # Eliminate (or do last)

    def _get_time_estimate_score(self, task: dict[str, Any]) -> float:
        """Prefer tasks that match current time of day."""
        # Get current hour
        hour = datetime.now().hour

        # Morning (6-12): prefer longer, complex tasks
        # Afternoon (12-18): prefer medium tasks
        # Evening (18-24): prefer quick tasks

        estimate = task.get("estimated_minutes", 25)

        if 6 <= hour < 12:
            # Morning: prefer 45-90 min tasks
            if 45 <= estimate <= 90:
                return 2.0
            if estimate > 90:
                return 1.5
            return 1.0
        if 12 <= hour < 18:
            # Afternoon: prefer 25-45 min tasks
            if 25 <= estimate <= 45:
                return 2.0
            return 1.0
        # Evening: prefer quick 15-25 min tasks
        if 15 <= estimate <= 25:
            return 2.0
        return 1.0

    def _was_recently_worked_on(self, task_id: str) -> bool:
        """Check if task was worked on in last 24 hours."""

        logger = HistoryLogger()
        # Query recent sessions for this task

        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()

        with sqlite3.connect(logger.db_path) as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM pomodoro_sessions WHERE task_id = ? AND start_time >= ?",
                (task_id, yesterday),
            ).fetchone()

            return result[0] > 0 if result else False

    def suggest_tasks(
        self, tasks: list[dict[str, Any]], limit: int = 5, label: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Score and rank pre-fetched tasks for focus.

        Args:
            tasks: List of task dicts (fetched by the caller).
            limit: Maximum number of suggestions.
            label: Optional label filter applied client-side.

        Returns:
            List of task dicts with scores.
        """
        # Get weights from config
        suggestions_config = self.config.focus_suggestions or {}
        weight_due = suggestions_config.get("weight_due_date", 0.4)
        weight_priority = suggestions_config.get("weight_priority", 0.3)
        weight_eisenhower = suggestions_config.get("weight_eisenhower", 0.2)
        weight_time = suggestions_config.get("weight_time_estimate", 0.1)

        if not isinstance(tasks, list) or not tasks:
            return []

        # Apply optional label filter client-side
        if label:
            tasks = [t for t in tasks if label in (t.get("labels") or [])]

        scored_tasks = []
        for task in tasks:
            # Skip recently worked on tasks
            if self._was_recently_worked_on(task["id"]):
                continue

            # Calculate component scores
            due_score = self._get_due_date_score(task)
            priority_score = self._get_priority_score(task)
            eisenhower_score = self._get_eisenhower_score(task)
            time_score = self._get_time_estimate_score(task)

            # Weighted total
            total_score = (
                due_score * weight_due
                + priority_score * weight_priority
                + eisenhower_score * weight_eisenhower
                + time_score * weight_time
            )

            scored_tasks.append(
                {
                    "task": task,
                    "score": total_score,
                    "components": {
                        "due_date": due_score,
                        "priority": priority_score,
                        "eisenhower": eisenhower_score,
                        "time_estimate": time_score,
                    },
                }
            )

        # Sort by score (highest first)
        scored_tasks.sort(key=lambda x: x["score"], reverse=True)

        return scored_tasks[:limit]
