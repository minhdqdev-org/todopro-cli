"""Labels API endpoints."""

from typing import Any, Optional

from todopro_cli.api.client import APIClient


class LabelsAPI:
    """Labels API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_labels(self) -> dict:
        """List all labels."""
        response = await self.client.get("/labels")
        return response.json()

    async def get_label(self, label_id: str) -> dict:
        """Get a specific label by ID."""
        response = await self.client.get(f"/labels/{label_id}")
        return response.json()

    async def create_label(
        self,
        name: str,
        *,
        color: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        """Create a new label."""
        data: dict[str, Any] = {"name": name}

        if color:
            data["color"] = color

        data.update(kwargs)

        response = await self.client.post("/labels", json=data)
        return response.json()

    async def update_label(self, label_id: str, **updates: Any) -> dict:
        """Update a label."""
        response = await self.client.patch(f"/labels/{label_id}", json=updates)
        return response.json()

    async def delete_label(self, label_id: str) -> None:
        """Delete a label."""
        await self.client.delete(f"/labels/{label_id}")
