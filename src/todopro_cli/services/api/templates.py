"""Templates API service for TodoPro CLI."""

from __future__ import annotations

from typing import Any

from todopro_cli.services.api.client import APIClient


class TemplatesAPI:
    """Client for the task templates API."""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    async def list_templates(self) -> list[dict]:
        """List all task templates."""
        response = await self.client.get("/v1/templates")
        return response.json()

    async def create_template(
        self,
        name: str,
        content: str,
        *,
        description: str | None = None,
        priority: int = 4,
        labels: list[str] | None = None,
        recurrence_rule: str | None = None,
    ) -> dict:
        """Create a new task template."""
        data: dict[str, Any] = {"name": name, "content": content, "priority": priority}
        if description:
            data["description"] = description
        if labels:
            data["labels"] = labels
        if recurrence_rule:
            data["recurrence_rule"] = recurrence_rule
        response = await self.client.post("/v1/templates", json=data)
        return response.json()

    async def get_template(self, template_id: str) -> dict:
        """Get a specific template by ID."""
        response = await self.client.get(f"/v1/templates/{template_id}")
        return response.json()

    async def delete_template(self, template_id: str) -> None:
        """Delete a template."""
        await self.client.delete(f"/v1/templates/{template_id}")

    async def apply_template(
        self,
        template_id: str,
        *,
        content: str | None = None,
        project_id: str | None = None,
        due_date: str | None = None,
        priority: int | None = None,
    ) -> dict:
        """Create a task from a template."""
        data: dict[str, Any] = {}
        if content:
            data["content"] = content
        if project_id:
            data["project_id"] = project_id
        if due_date:
            data["due_date"] = due_date
        if priority is not None:
            data["priority"] = priority
        response = await self.client.post(
            f"/v1/templates/{template_id}/apply", json=data
        )
        return response.json()

    async def find_template_by_name(self, name_or_id: str) -> dict | None:
        """Find a template by name or ID (UUID-shaped input treated as ID)."""
        # Try as ID first
        import re

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
        )
        if uuid_pattern.match(name_or_id):
            try:
                return await self.get_template(name_or_id)
            except Exception:
                pass

        # Search by name
        templates = await self.list_templates()
        for t in templates:
            if t.get("name", "").lower() == name_or_id.lower():
                return t
        return None
