"""Todoist API v1 client.

Defines a Protocol for testability (Dependency Inversion) and a
concrete implementation backed by httpx.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx

from .models import TodoistLabel, TodoistProject, TodoistTask

_BASE_URL = "https://api.todoist.com/api/v1"
_DEFAULT_TIMEOUT = 30.0
_MAX_LABEL_LIMIT = 200  # Todoist labels endpoint paginates incorrectly; use max


@runtime_checkable
class TodoistClientProtocol(Protocol):
    """Abstract interface for fetching data from Todoist.

    Keeping this as a Protocol (not ABC) means tests can pass any object
    that satisfies the interface without subclassing.
    """

    async def get_projects(self) -> list[TodoistProject]:
        """Return all non-archived projects."""
        ...

    async def get_tasks(self, project_id: str, *, limit: int = 500) -> list[TodoistTask]:
        """Return active (non-completed, non-deleted) tasks for a project."""
        ...

    async def get_labels(self) -> list[TodoistLabel]:
        """Return all personal labels."""
        ...


class TodoistClient:
    """Concrete Todoist API v1 client using httpx.

    Args:
        api_key: Todoist personal API token.
        base_url: Override API base URL (useful for testing).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def get_projects(self) -> list[TodoistProject]:
        """Return all non-archived Todoist projects."""
        data = await self._get("/projects")
        results = data if isinstance(data, list) else data.get("results", [])
        return [
            TodoistProject.model_validate(p)
            for p in results
            if not p.get("is_archived", False)
        ]

    async def get_tasks(self, project_id: str, *, limit: int = 500) -> list[TodoistTask]:
        """Return active tasks for a project (paginated internally)."""
        params: dict[str, str | int] = {
            "project_id": project_id,
            "limit": min(limit, 200),  # API page cap
        }
        all_tasks: list[TodoistTask] = []
        fetched = 0

        while True:
            data = await self._get("/tasks", params=params)
            items = data if isinstance(data, list) else data.get("results", [])

            for item in items:
                if item.get("is_deleted") or item.get("checked"):
                    continue
                all_tasks.append(TodoistTask.model_validate(item))
                fetched += 1
                if fetched >= limit:
                    return all_tasks

            # Respect cursor-based or offset-based pagination
            next_cursor = data.get("next_cursor") if isinstance(data, dict) else None
            if not next_cursor or not items:
                break
            params["cursor"] = next_cursor

        return all_tasks

    async def get_labels(self) -> list[TodoistLabel]:
        """Return all personal labels.

        The Todoist labels endpoint has a known pagination bug where repeated
        requests return the same page. Work around this by fetching the maximum
        allowed in a single request.
        """
        data = await self._get("/labels", params={"limit": _MAX_LABEL_LIMIT})
        results = data if isinstance(data, list) else data.get("results", [])
        return [TodoistLabel.model_validate(lbl) for lbl in results]

    async def _get(
        self,
        path: str,
        params: dict | None = None,
    ) -> list | dict:
        """Execute a GET request, raising descriptive errors on failure."""
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=self._headers, params=params)

        if response.status_code == 401:
            raise ValueError("Invalid Todoist API key — check your credentials.")
        if response.status_code == 403:
            raise PermissionError("Insufficient permissions for the requested resource.")
        response.raise_for_status()
        return response.json()
