"""Projects API endpoints."""

from typing import Any

from todopro_cli.api.client import APIClient


class ProjectsAPI:
    """Projects API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_projects(
        self,
        *,
        archived: bool | None = None,
        favorites: bool | None = None,
    ) -> dict:
        """List projects."""
        params: dict[str, Any] = {}

        if archived is not None:
            params["archived"] = archived
        if favorites is not None:
            params["favorites"] = favorites

        response = await self.client.get("/v1/projects", params=params)
        return response.json()

    async def get_project(self, project_id: str) -> dict:
        """Get a specific project by ID."""
        response = await self.client.get(f"/v1/projects/{project_id}")
        return response.json()

    async def create_project(
        self,
        name: str,
        *,
        color: str | None = None,
        favorite: bool = False,
        **kwargs: Any,
    ) -> dict:
        """Create a new project."""
        data: dict[str, Any] = {"name": name, "favorite": favorite}

        if color:
            data["color"] = color

        data.update(kwargs)

        response = await self.client.post("/v1/projects", json=data)
        return response.json()

    async def update_project(self, project_id: str, **updates: Any) -> dict:
        """Update a project."""
        response = await self.client.patch(f"/v1/projects/{project_id}", json=updates)
        return response.json()

    async def delete_project(self, project_id: str) -> None:
        """Delete a project."""
        await self.client.delete(f"/v1/projects/{project_id}")

    async def archive_project(self, project_id: str) -> dict:
        """Archive a project."""
        response = await self.client.post(f"/v1/projects/{project_id}/archive")
        return response.json()

    async def unarchive_project(self, project_id: str) -> dict:
        """Unarchive a project."""
        response = await self.client.post(f"/v1/projects/{project_id}/unarchive")
        return response.json()
