"""Sections API endpoints."""

from typing import Any

from todopro_cli.services.api.client import APIClient


class SectionsAPI:
    """Sections API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_sections(self, project_id: str) -> dict:
        """List all sections for a project."""
        response = await self.client.get(f"/v1/projects/{project_id}/sections")
        return response.json()

    async def get_section(self, project_id: str, section_id: str) -> dict:
        """Get a specific section by ID."""
        response = await self.client.get(
            f"/v1/projects/{project_id}/sections/{section_id}"
        )
        return response.json()

    async def create_section(
        self,
        project_id: str,
        name: str,
        *,
        display_order: int = 0,
        **kwargs: Any,
    ) -> dict:
        """Create a new section."""
        data: dict[str, Any] = {"name": name, "display_order": display_order}
        data.update(kwargs)
        response = await self.client.post(
            f"/v1/projects/{project_id}/sections", json=data
        )
        return response.json()

    async def update_section(
        self, project_id: str, section_id: str, **updates: Any
    ) -> dict:
        """Update a section."""
        response = await self.client.patch(
            f"/v1/projects/{project_id}/sections/{section_id}", json=updates
        )
        return response.json()

    async def delete_section(self, project_id: str, section_id: str) -> None:
        """Delete a section."""
        await self.client.delete(
            f"/v1/projects/{project_id}/sections/{section_id}"
        )

    async def reorder_sections(
        self, project_id: str, section_orders: list[dict]
    ) -> dict:
        """Reorder sections within a project."""
        response = await self.client.patch(
            f"/v1/projects/{project_id}/sections/reorder",
            json={"section_orders": section_orders},
        )
        return response.json()
