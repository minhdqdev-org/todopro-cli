"""Collaboration API service for TodoPro CLI."""

from __future__ import annotations

from typing import Any

from todopro_cli.services.api.client import APIClient


class CollaborationAPI:
    """Collaboration API client."""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    # Project sharing

    async def share_project(
        self, project_id: str, email: str, permission: str = "editor"
    ) -> dict:
        """Share a project with a user by email."""
        response = await self.client.post(
            f"/v1/projects/{project_id}/share",
            json={"email": email, "permission": permission},
        )
        return response.json()

    async def get_collaborators(self, project_id: str) -> list[dict]:
        """Get all collaborators for a project."""
        response = await self.client.get(f"/v1/projects/{project_id}/collaborators")
        return response.json()

    async def update_collaborator_permission(
        self, project_id: str, user_id: str, permission: str
    ) -> dict:
        """Update a collaborator's permission on a project."""
        response = await self.client.patch(
            f"/v1/projects/{project_id}/collaborators/{user_id}",
            json={"permission": permission},
        )
        return response.json()

    async def remove_collaborator(self, project_id: str, user_id: str) -> None:
        """Remove a collaborator from a project."""
        await self.client.delete(f"/v1/projects/{project_id}/collaborators/{user_id}")

    async def leave_project(self, project_id: str) -> None:
        """Leave a project (remove self as collaborator)."""
        await self.client.delete(f"/v1/projects/{project_id}/leave")

    # Task assignment

    async def assign_task(self, task_id: str, email: str) -> dict:
        """Assign a task to a user by email."""
        response = await self.client.patch(
            f"/v1/tasks/{task_id}/assign",
            json={"email": email},
        )
        return response.json()

    async def unassign_task(self, task_id: str) -> dict:
        """Unassign a task."""
        response = await self.client.delete(f"/v1/tasks/{task_id}/assign")
        return response.json()

    # Task comments

    async def get_comments(self, task_id: str) -> list[dict]:
        """Get all comments for a task."""
        response = await self.client.get(f"/v1/tasks/{task_id}/comments")
        return response.json()

    async def add_comment(self, task_id: str, content: str) -> dict:
        """Add a comment to a task."""
        response = await self.client.post(
            f"/v1/tasks/{task_id}/comments",
            json={"content": content},
        )
        return response.json()

    async def update_comment(self, task_id: str, comment_id: str, content: str) -> dict:
        """Update an existing comment."""
        response = await self.client.patch(
            f"/v1/tasks/{task_id}/comments/{comment_id}",
            json={"content": content},
        )
        return response.json()

    async def delete_comment(self, task_id: str, comment_id: str) -> None:
        """Delete a comment from a task."""
        await self.client.delete(f"/v1/tasks/{task_id}/comments/{comment_id}")
