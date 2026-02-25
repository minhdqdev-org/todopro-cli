"""Project service - Business logic for project operations."""

from __future__ import annotations

from todopro_cli.models import Project, ProjectCreate, ProjectFilters, ProjectUpdate
from todopro_cli.repositories import ProjectRepository


class ProjectService:
    """Service for project business logic.

    This service encapsulates business rules and orchestrates project operations
    using the project repository.
    """

    def __init__(self, project_repository: ProjectRepository):
        """Initialize the project service.

        Args:
            project_repository: ProjectRepository implementation for data access
        """
        self.repository = project_repository

    async def list_projects(
        self,
        *,
        is_favorite: bool | None = None,
        is_archived: bool | None = None,
        workspace_id: str | None = None,
        search: str | None = None,
    ) -> list[Project]:
        """List projects with filtering.

        Args:
            is_favorite: Filter by favorite status
            is_archived: Filter by archived status
            workspace_id: Filter by workspace ID
            search: Text search query

        Returns:
            List of Project objects matching the criteria
        """
        filters = ProjectFilters(
            is_favorite=is_favorite,
            is_archived=is_archived,
            workspace_id=workspace_id,
            search=search,
        )
        return await self.repository.list_all(filters)

    async def get_project(self, project_id: str) -> Project:
        """Get a specific project by ID.

        Args:
            project_id: Unique identifier for the project

        Returns:
            Project object
        """
        return await self.repository.get(project_id)

    async def create_project(
        self,
        name: str,
        *,
        color: str | None = None,
        is_favorite: bool = False,
        workspace_id: str | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name (required)
            color: Optional hex color code
            is_favorite: Whether to mark as favorite
            workspace_id: Optional parent workspace ID

        Returns:
            Created Project object
        """
        project_data = ProjectCreate(
            name=name,
            color=color,
            is_favorite=is_favorite,
            workspace_id=workspace_id,
        )
        return await self.repository.create(project_data)

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
        is_favorite: bool | None = None,
        is_archived: bool | None = None,
        workspace_id: str | None = None,
    ) -> Project:
        """Update an existing project.

        Args:
            project_id: Project ID to update
            name: Updated project name
            color: Updated hex color code
            is_favorite: Updated favorite status
            is_archived: Updated archived status
            workspace_id: Updated parent workspace ID

        Returns:
            Updated Project object
        """
        updates = ProjectUpdate(
            name=name,
            color=color,
            is_favorite=is_favorite,
            is_archived=is_archived,
            workspace_id=workspace_id,
        )
        if name is not None:
            current = await self.repository.get(project_id)
            if current.name.lower() == "inbox" and name.lower() != "inbox":
                raise ValueError("Cannot rename the Inbox project")
        return await self.repository.update(project_id, updates)

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project ID to delete

        Returns:
            True if deletion was successful
        """
        project = await self.repository.get(project_id)
        if project.name.lower() == "inbox":
            raise ValueError("Cannot delete the Inbox project")
        return await self.repository.delete(project_id)

    async def archive_project(self, project_id: str) -> Project:
        """Archive a project.

        Args:
            project_id: Project ID to archive

        Returns:
            Updated Project object with is_archived=True
        """
        project = await self.repository.get(project_id)
        if project.name.lower() == "inbox":
            raise ValueError("Cannot archive the Inbox project")
        return await self.repository.archive(project_id)

    async def favorite_project(self, project_id: str) -> Project:
        """Mark a project as favorite.

        Args:
            project_id: Project ID to favorite

        Returns:
            Updated Project object with is_favorite=True
        """
        updates = ProjectUpdate(is_favorite=True)
        return await self.repository.update(project_id, updates)

    async def unfavorite_project(self, project_id: str) -> Project:
        """Remove favorite status from a project.

        Args:
            project_id: Project ID to unfavorite

        Returns:
            Updated Project object with is_favorite=False
        """
        updates = ProjectUpdate(is_favorite=False)
        return await self.repository.update(project_id, updates)

    async def unarchive_project(self, project_id: str) -> Project:
        """Unarchive a project.

        Args:
            project_id: Project ID to unarchive

        Returns:
            Updated Project object with is_archived=False
        """
        return await self.repository.unarchive(project_id)

    async def get_project_stats(self, project_id: str) -> dict:
        """Get project statistics.

        Args:
            project_id: Project ID to get stats for

        Returns:
            Dictionary containing statistics (total_tasks, completed_tasks, etc.)
        """
        return await self.repository.get_stats(project_id)


def get_project_service():
    """Factory function to get a ProjectService instance."""
    from todopro_cli.services.config_service import (
        get_storage_strategy_context,  # type: ignore
    )

    storage_strategy_context = get_storage_strategy_context()
    return ProjectService(storage_strategy_context.project_repository)
