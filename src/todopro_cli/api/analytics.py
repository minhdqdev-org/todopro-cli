"""Analytics API endpoints for TodoPro CLI.

US-010: Analytics commands for CLI.
"""

from typing import Any

from todopro_cli.api.client import APIClient


class AnalyticsAPI:
    """Analytics API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def get_productivity_score(self) -> dict[str, Any]:
        """Get productivity score and breakdown.

        Returns:
            dict with score, trend, and breakdown fields
        """
        response = await self.client.get("/v1/analytics/productivity-score")
        return response.json()

    async def get_streaks(self) -> dict[str, Any]:
        """Get task completion streaks.

        Returns:
            dict with current_streak, longest_streak, and streak_history
        """
        response = await self.client.get("/v1/analytics/streaks")
        return response.json()

    async def get_completion_stats(self) -> dict[str, Any]:
        """Get completion statistics.

        Returns:
            dict with total_completed, completion_rate, etc.
        """
        response = await self.client.get("/v1/analytics/completion-stats")
        return response.json()

    async def export_data(self, format: str = "csv") -> bytes:
        """Export analytics data in specified format.

        Args:
            format: Export format ("csv" or "json")

        Returns:
            Raw bytes of exported file
        """
        response = await self.client.get(f"/v1/analytics/export?format={format}")
        return response.content
