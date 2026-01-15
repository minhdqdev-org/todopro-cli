"""Tasks API endpoints."""

from typing import Any, Optional

from todopro_cli.api.client import APIClient


class TasksAPI:
    """Tasks API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
        priority: Optional[int] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort: Optional[str] = None,
        **filters: Any,
    ) -> dict:
        """List tasks with optional filters."""
        params: dict[str, Any] = {}

        if status:
            params["status"] = status
        if project_id:
            params["project_id"] = project_id
        if priority is not None:
            params["priority"] = priority
        if search:
            params["search"] = search
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if sort:
            params["sort"] = sort

        # Add any additional filters
        params.update(filters)

        response = await self.client.get("/v1/tasks", params=params)
        return response.json()

    async def get_task(self, task_id: str) -> dict:
        """Get a specific task by ID."""
        response = await self.client.get(f"/v1/tasks/{task_id}")
        return response.json()

    async def create_task(
        self,
        content: str,
        *,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[int] = None,
        labels: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict:
        """Create a new task."""
        data: dict[str, Any] = {"content": content}

        if description:
            data["description"] = description
        if project_id:
            data["project_id"] = project_id
        if due_date:
            data["due_date"] = due_date
        if priority is not None:
            data["priority"] = priority
        if labels:
            data["labels"] = labels

        # Add any additional fields
        data.update(kwargs)

        response = await self.client.post("/v1/tasks", json=data)
        return response.json()

    async def update_task(self, task_id: str, **updates: Any) -> dict:
        """Update a task."""
        response = await self.client.patch(f"/v1/tasks/{task_id}", json=updates)
        return response.json()

    async def delete_task(self, task_id: str) -> None:
        """Delete a task."""
        await self.client.delete(f"/v1/tasks/{task_id}")

    async def complete_task(self, task_id: str) -> dict:
        """Mark a task as completed."""
        response = await self.client.post(f"/v1/tasks/{task_id}/close")
        return response.json()

    async def reopen_task(self, task_id: str) -> dict:
        """Reopen a completed task."""
        response = await self.client.post(f"/v1/tasks/{task_id}/reopen")
        return response.json()

    async def get_task_comments(self, task_id: str) -> dict:
        """Get comments for a task."""
        response = await self.client.get(f"/v1/tasks/{task_id}/comments")
        return response.json()

    async def add_comment(self, task_id: str, text: str) -> dict:
        """Add a comment to a task."""
        response = await self.client.post(
            f"/v1/tasks/{task_id}/comments",
            json={"text": text},
        )
        return response.json()

    async def today_tasks(self) -> dict:
        """Get tasks for today (overdue + today's tasks)."""
        response = await self.client.get("/v1/tasks/today")
        return response.json()

    async def next_task(self) -> dict:
        """Get the next task to do right now."""
        response = await self.client.get("/v1/tasks/next")
        return response.json()

    async def reschedule_overdue(self) -> dict:
        """Reschedule all overdue tasks to today."""
        response = await self.client.post("/v1/tasks/reschedule-overdue")
        return response.json()
    
    async def quick_add(self, input_text: str) -> dict:
        """Quick add a task using natural language parsing."""
        response = await self.client.post(
            "/v1/tasks/quick-add",
            json={"input": input_text}
        )
        return response.json()
    
    async def eisenhower_matrix(self) -> dict:
        """Get Eisenhower Matrix view with insights."""
        response = await self.client.get("/v1/tasks/eisenhower")
        return response.json()
    
    async def classify_task(self, task_id: str, is_urgent: bool = None, is_important: bool = None) -> dict:
        """Classify a task in the Eisenhower Matrix."""
        data = {}
        if is_urgent is not None:
            data["is_urgent"] = is_urgent
        if is_important is not None:
            data["is_important"] = is_important
        
        response = await self.client.patch(
            f"/v1/tasks/{task_id}/eisenhower",
            json=data
        )
        return response.json()
    
    async def bulk_classify(self, task_ids: list[str], quadrant: str = None, 
                           is_urgent: bool = None, is_important: bool = None) -> dict:
        """Bulk classify tasks."""
        data = {"task_ids": task_ids}
        if quadrant:
            data["quadrant"] = quadrant
        if is_urgent is not None:
            data["is_urgent"] = is_urgent
        if is_important is not None:
            data["is_important"] = is_important
        
        response = await self.client.post(
            "/v1/tasks/eisenhower/classify",
            json=data
        )
        return response.json()
