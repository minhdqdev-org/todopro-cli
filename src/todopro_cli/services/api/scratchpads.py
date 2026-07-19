"""Scratchpads API endpoints.

Scratchpads are project-scoped notes. The backend runs with ``APPEND_SLASH=False``
and its URL patterns are asymmetric, so the trailing slashes below are exact and
must not be "normalised":

- list / create: ``/v1/projects/<project_id>/scratchpads/``  (trailing slash)
- detail (get / patch / delete): ``/v1/scratchpads/<scratchpad_id>``  (no slash)
"""

from typing import Any

from todopro_cli.services.api.client import APIClient


class ScratchpadsAPI:
    """Scratchpads API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_scratchpads(self, project_id: str) -> list:
        """List all scratchpads for a project."""
        response = await self.client.get(f"/v1/projects/{project_id}/scratchpads/")
        return response.json()

    async def get_scratchpad(self, scratchpad_id: str) -> dict:
        """Get a specific scratchpad by ID."""
        response = await self.client.get(f"/v1/scratchpads/{scratchpad_id}")
        return response.json()

    async def create_scratchpad(
        self,
        project_id: str,
        *,
        title: str = "",
        content: str = "",
        **kwargs: Any,
    ) -> dict:
        """Create a new scratchpad within a project."""
        data: dict[str, Any] = {"title": title, "content": content}
        data.update(kwargs)
        response = await self.client.post(
            f"/v1/projects/{project_id}/scratchpads/", json=data
        )
        return response.json()

    async def update_scratchpad(self, scratchpad_id: str, **updates: Any) -> dict:
        """Update a scratchpad."""
        response = await self.client.patch(
            f"/v1/scratchpads/{scratchpad_id}", json=updates
        )
        return response.json()

    async def delete_scratchpad(self, scratchpad_id: str) -> None:
        """Delete a scratchpad."""
        await self.client.delete(f"/v1/scratchpads/{scratchpad_id}")
