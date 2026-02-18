"""Repository abstraction layer for TodoPro CLI.

This module defines the abstract base classes (interfaces) for all repository types,
following the hexagonal architecture (Ports & Adapters) pattern.

Repositories provide an abstraction over data persistence, allowing the business logic
to remain independent of the underlying storage mechanism (local SQLite, remote API, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from todopro_cli.models import (
    Context,
    ContextCreate,
    Label,
    LabelCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
)


class TaskRepository(ABC):
    """Abstract base class for task persistence operations.

    This interface defines all CRUD operations for tasks, ensuring that
    different storage backends (SQLite, REST API) implement a consistent contract.
    """

    @abstractmethod
    async def list_all(self, filters: TaskFilters) -> list[Task]:
        """List tasks with optional filtering.

        Args:
            filters: TaskFilters object specifying filter criteria

        Returns:
            List of Task objects matching the filters

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
        """
        raise NotImplementedError(
            "TaskRepository.list_all() must be implemented by adapter"
        )

    @abstractmethod
    async def get(self, task_id: str) -> Task:
        """Get a specific task by ID.

        Args:
            task_id: Unique identifier for the task

        Returns:
            Task object

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If task does not exist
        """
        raise NotImplementedError("TaskRepository.get() must be implemented by adapter")

    @abstractmethod
    async def add(self, task_data: TaskCreate) -> Task:
        """Create a new task.

        Args:
            task_data: TaskCreate object with task details

        Returns:
            Created Task object with generated ID and timestamps

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            ValidationError: If task data is invalid
        """
        raise NotImplementedError("TaskRepository.add() must be implemented by adapter")

    @abstractmethod
    async def update(self, task_id: str, updates: TaskUpdate) -> Task:
        """Update an existing task.

        Args:
            task_id: Unique identifier for the task
            updates: TaskUpdate object with fields to update

        Returns:
            Updated Task object

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If task does not exist
            ValidationError: If update data is invalid
        """
        raise NotImplementedError(
            "TaskRepository.update() must be implemented by adapter"
        )

    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Unique identifier for the task

        Returns:
            True if deletion was successful

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If task does not exist
        """
        raise NotImplementedError(
            "TaskRepository.delete() must be implemented by adapter"
        )

    @abstractmethod
    async def complete(self, task_id: str) -> Task:
        """Mark a task as completed.

        Args:
            task_id: Unique identifier for the task

        Returns:
            Updated Task object with is_completed=True and completed_at set

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If task does not exist
        """
        raise NotImplementedError(
            "TaskRepository.complete() must be implemented by adapter"
        )

    @abstractmethod
    async def bulk_update(self, task_ids: list[str], updates: TaskUpdate) -> list[Task]:
        """Update multiple tasks at once.

        Args:
            task_ids: List of task IDs to update
            updates: TaskUpdate object with fields to update

        Returns:
            List of updated Task objects

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If any task does not exist
            ValidationError: If update data is invalid
        """
        raise NotImplementedError(
            "TaskRepository.bulk_update() must be implemented by adapter"
        )


class ProjectRepository(ABC):
    """Abstract base class for project persistence operations.

    This interface defines all CRUD operations for projects.
    """

    @abstractmethod
    async def list_all(self, filters: ProjectFilters) -> list[Project]:
        """List projects with optional filtering.

        Args:
            filters: ProjectFilters object specifying filter criteria

        Returns:
            List of Project objects matching the filters

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
        """
        raise NotImplementedError(
            "ProjectRepository.list_all() must be implemented by adapter"
        )

    @abstractmethod
    async def get(self, project_id: str) -> Project:
        """Get a specific project by ID.

        Args:
            project_id: Unique identifier for the project

        Returns:
            Project object

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If project does not exist
        """
        raise NotImplementedError(
            "ProjectRepository.get() must be implemented by adapter"
        )

    @abstractmethod
    async def create(self, project_data: ProjectCreate) -> Project:
        """Create a new project.

        Args:
            project_data: ProjectCreate object with project details

        Returns:
            Created Project object with generated ID and timestamps

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            ValidationError: If project data is invalid
        """
        raise NotImplementedError(
            "ProjectRepository.create() must be implemented by adapter"
        )

    @abstractmethod
    async def update(self, project_id: str, updates: ProjectUpdate) -> Project:
        """Update an existing project.

        Args:
            project_id: Unique identifier for the project
            updates: ProjectUpdate object with fields to update

        Returns:
            Updated Project object

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If project does not exist
            ValidationError: If update data is invalid
        """
        raise NotImplementedError(
            "ProjectRepository.update() must be implemented by adapter"
        )

    @abstractmethod
    async def delete(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Unique identifier for the project

        Returns:
            True if deletion was successful

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If project does not exist
        """
        raise NotImplementedError(
            "ProjectRepository.delete() must be implemented by adapter"
        )

    @abstractmethod
    async def archive(self, project_id: str) -> Project:
        """Archive a project.

        Args:
            project_id: Unique identifier for the project

        Returns:
            Updated Project object with is_archived=True

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If project does not exist
        """
        raise NotImplementedError(
            "ProjectRepository.archive() must be implemented by adapter"
        )

    @abstractmethod
    async def unarchive(self, project_id: str) -> Project:
        """Unarchive a project.

        Args:
            project_id: Unique identifier for the project

        Returns:
            Updated Project object with is_archived=False

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If project does not exist
        """
        raise NotImplementedError(
            "ProjectRepository.unarchive() must be implemented by adapter"
        )

    @abstractmethod
    async def get_stats(self, project_id: str) -> dict:
        """Get project statistics.

        Args:
            project_id: Unique identifier for the project

        Returns:
            Dictionary containing project statistics (total_tasks, completed_tasks, etc.)

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If project does not exist
        """
        raise NotImplementedError(
            "ProjectRepository.get_stats() must be implemented by adapter"
        )


class LabelRepository(ABC):
    """Abstract base class for label persistence operations.

    This interface defines CRUD operations plus search functionality for autocomplete.
    """

    @abstractmethod
    async def list_all(self) -> list[Label]:
        """List all labels.

        Returns:
            List of all Label objects

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
        """
        raise NotImplementedError(
            "LabelRepository.list_all() must be implemented by adapter"
        )

    @abstractmethod
    async def get(self, label_id: str) -> Label:
        """Get a specific label by ID.

        Args:
            label_id: Unique identifier for the label

        Returns:
            Label object

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If label does not exist
        """
        raise NotImplementedError(
            "LabelRepository.get() must be implemented by adapter"
        )

    @abstractmethod
    async def create(self, label_data: LabelCreate) -> Label:
        """Create a new label.

        Args:
            label_data: LabelCreate object with label details

        Returns:
            Created Label object with generated ID

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            ValidationError: If label data is invalid
        """
        raise NotImplementedError(
            "LabelRepository.create() must be implemented by adapter"
        )

    @abstractmethod
    async def delete(self, label_id: str) -> bool:
        """Delete a label.

        Args:
            label_id: Unique identifier for the label

        Returns:
            True if deletion was successful

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If label does not exist
        """
        raise NotImplementedError(
            "LabelRepository.delete() must be implemented by adapter"
        )

    @abstractmethod
    async def search(self, prefix: str) -> list[Label]:
        """Search labels by name prefix (for autocomplete).

        Args:
            prefix: Text prefix to match against label names

        Returns:
            List of Label objects with names starting with prefix

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
        """
        raise NotImplementedError(
            "LabelRepository.search() must be implemented by adapter"
        )


class ContextRepository(ABC):
    """Abstract base class for context (location) persistence operations.

    This interface defines CRUD operations plus geofencing functionality.
    """

    @abstractmethod
    async def list_all(self) -> list[Context]:
        """List all contexts.

        Returns:
            List of all Context objects

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
        """
        raise NotImplementedError(
            "ContextRepository.list_all() must be implemented by adapter"
        )

    @abstractmethod
    async def get(self, context_id: str) -> Context:
        """Get a specific context by ID.

        Args:
            context_id: Unique identifier for the context

        Returns:
            Context object

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If context does not exist
        """
        raise NotImplementedError(
            "ContextRepository.get() must be implemented by adapter"
        )

    @abstractmethod
    async def create(self, context_data: ContextCreate) -> Context:
        """Create a new context.

        Args:
            context_data: ContextCreate object with context details

        Returns:
            Created Context object with generated ID

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            ValidationError: If context data is invalid
        """
        raise NotImplementedError(
            "ContextRepository.create() must be implemented by adapter"
        )

    @abstractmethod
    async def delete(self, context_id: str) -> bool:
        """Delete a context.

        Args:
            context_id: Unique identifier for the context

        Returns:
            True if deletion was successful

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
            NotFoundError: If context does not exist
        """
        raise NotImplementedError(
            "ContextRepository.delete() must be implemented by adapter"
        )

    @abstractmethod
    async def get_available(self, latitude: float, longitude: float) -> list[Context]:
        """Get contexts available at a specific location (within geofence).

        Uses haversine formula to calculate distance and filter contexts
        where the given location is within their radius.

        Args:
            latitude: Geographic latitude of current location
            longitude: Geographic longitude of current location

        Returns:
            List of Context objects where location is within geofence

        Raises:
            NotImplementedError: Must be implemented by concrete adapter
        """
        raise NotImplementedError(
            "ContextRepository.get_available() must be implemented by adapter"
        )
