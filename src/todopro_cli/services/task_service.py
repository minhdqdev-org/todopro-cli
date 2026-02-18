"""Task service - Business logic for task operations.

This service layer sits between commands and repositories, providing
a clean API for task-related business logic.
"""

from __future__ import annotations

from datetime import datetime

from todopro_cli.repositories import TaskRepository
from todopro_cli.models import Task, TaskCreate, TaskFilters, TaskUpdate


class TaskService:
    """Service for task business logic.

    This service encapsulates business rules and orchestrates task operations
    using the task repository.
    """

    def __init__(self, task_repository: TaskRepository):
        """Initialize the task service.

        Args:
            task_repository: TaskRepository implementation for data access
        """
        self.repository = task_repository

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        project_id: str | None = None,
        priority: int | None = None,
        labels: list[str] | None = None,
        contexts: list[str] | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> list[Task]:
        """List tasks with filtering and pagination.

        Args:
            status: Filter by status ("active", "completed", "all")
            project_id: Filter by project ID
            priority: Filter by priority level
            labels: Filter by label IDs
            contexts: Filter by context IDs
            search: Full-text search query
            limit: Maximum number of results
            offset: Pagination offset
            sort: Sort field and direction

        Returns:
            List of Task objects matching the criteria
        """
        filters = TaskFilters(
            status=status,
            project_id=project_id,
            priority=priority,
            labels=labels,
            contexts=contexts,
            search=search,
            limit=limit,
            offset=offset,
            sort=sort,
        )
        return await self.repository.list_all(filters)

    async def get_task(self, task_id: str) -> Task:
        """Get a specific task by ID.

        Args:
            task_id: Unique identifier for the task

        Returns:
            Task object
        """
        return await self.repository.get(task_id)

    async def add_task(
        self,
        content: str,
        *,
        description: str | None = None,
        project_id: str | None = None,
        due_date: str | None = None,
        priority: int = 1,
        labels: list[str] | None = None,
        contexts: list[str] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            content: Task description (required)
            description: Detailed description
            project_id: Parent project ID
            due_date: Due date (ISO format or datetime)
            priority: Priority level (1-4)
            labels: List of label IDs
            contexts: List of context IDs

        Returns:
            Created Task object
        """
        from datetime import datetime

        # Parse due_date if provided as string
        parsed_due_date = None
        if due_date:
            if isinstance(due_date, str):
                parsed_due_date = datetime.fromisoformat(due_date)
            else:
                parsed_due_date = due_date

        task_data = TaskCreate(
            content=content,
            description=description,
            project_id=project_id,
            due_date=parsed_due_date,
            priority=priority,
            labels=labels or [],
            contexts=contexts or [],
        )
        return await self.repository.add(task_data)

    async def update_task(
        self,
        task_id: str,
        *,
        content: str | None = None,
        description: str | None = None,
        project_id: str | None = None,
        due_date: str | None = None,
        priority: int | None = None,
        is_completed: bool | None = None,
        labels: list[str] | None = None,
        contexts: list[str] | None = None,
    ) -> Task:
        """Update an existing task.

        Args:
            task_id: Task ID to update
            content: Updated task description
            description: Updated detailed description
            project_id: Updated parent project ID
            due_date: Updated due date
            priority: Updated priority level
            is_completed: Updated completion status
            labels: Updated list of label IDs
            contexts: Updated list of context IDs

        Returns:
            Updated Task object
        """

        # Parse due_date if provided as string
        parsed_due_date = None
        if due_date:
            parsed_due_date = datetime.fromisoformat(due_date)

        updates = TaskUpdate(
            content=content,
            description=description,
            project_id=project_id,
            due_date=parsed_due_date,
            priority=priority,
            is_completed=is_completed,
            labels=labels,
            contexts=contexts,
        )
        return await self.repository.update(task_id, updates)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID to delete

        Returns:
            True if deletion was successful
        """
        return await self.repository.delete(task_id)

    async def complete_task(self, task_id: str) -> Task:
        """Mark a task as completed.

        Args:
            task_id: Task ID to complete

        Returns:
            Updated Task object with completion timestamp
        """
        return await self.repository.complete(task_id)

    async def reopen_task(self, task_id: str) -> Task:
        """Reopen a completed task.

        Args:
            task_id: Task ID to reopen

        Returns:
            Updated task with is_completed=False
        """
        updates = TaskUpdate(is_completed=False, completed_at=None)
        return await self.repository.update(task_id, updates)

    async def bulk_complete_tasks(self, task_ids: list[str]) -> list[Task]:
        """Mark multiple tasks as completed.

        Args:
            task_ids: List of task IDs to complete

        Returns:
            List of updated Task objects
        """
        updates = TaskUpdate(is_completed=True)
        return await self.repository.bulk_update(task_ids, updates)

    async def bulk_update_tasks(
        self,
        task_ids: list[str],
        **updates: object,
    ) -> list[Task]:
        """Update multiple tasks at once.

        Args:
            task_ids: List of task IDs to update
            **updates: Fields to update

        Returns:
            List of updated Task objects
        """
        task_updates = TaskUpdate(**updates)
        return await self.repository.bulk_update(task_ids, task_updates)
