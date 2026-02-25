"""Saved filters API service for TodoPro CLI."""

from typing import Any

from todopro_cli.services.api.client import APIClient


class FiltersAPI:
    """API client for saved filter/smart view management."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_filters(self) -> list[dict]:
        """List all saved filters for the current user."""
        response = await self.client.get("/v1/filters/")
        return response.json()

    async def create_filter(
        self,
        name: str,
        color: str,
        *,
        priority: list[int] | None = None,
        project_ids: list[str] | None = None,
        label_ids: list[str] | None = None,
        due_within_days: int | None = None,
    ) -> dict:
        """Create a new saved filter.

        Args:
            name: Filter name (max 100 chars, must be unique)
            color: Hex color code (e.g., "#FF5733")
            priority: List of priority values to filter on (1-4)
            project_ids: List of project IDs to filter on
            label_ids: List of label IDs to filter on (AND logic)
            due_within_days: Include tasks due within this many days

        Returns:
            Created filter object
        """
        criteria: dict[str, Any] = {}
        if priority:
            criteria["priority"] = priority
        if project_ids:
            criteria["project_ids"] = project_ids
        if label_ids:
            criteria["label_ids"] = label_ids
        if due_within_days is not None:
            criteria["due_within_days"] = due_within_days

        data = {"name": name, "color": color, "criteria": criteria}
        response = await self.client.post("/v1/filters/", json=data)
        return response.json()

    async def get_filter(self, filter_id: str) -> dict:
        """Get a specific filter by ID."""
        response = await self.client.get(f"/v1/filters/{filter_id}")
        return response.json()

    async def delete_filter(self, filter_id: str) -> None:
        """Delete a saved filter."""
        await self.client.delete(f"/v1/filters/{filter_id}")

    async def apply_filter(self, filter_id: str) -> list[dict]:
        """Apply a saved filter and return matching tasks."""
        response = await self.client.get(f"/v1/filters/{filter_id}/tasks")
        return response.json()

    async def find_filter_by_name(self, name: str) -> dict | None:
        """Find a filter by name (case-insensitive)."""
        filters = await self.list_filters()
        name_lower = name.lower()
        for f in filters:
            if f.get("name", "").lower() == name_lower:
                return f
        return None
