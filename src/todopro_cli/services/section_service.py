"""Section service – business logic for project section operations."""

from __future__ import annotations

from todopro_cli.models import Section, SectionCreate, SectionFilters, SectionUpdate
from todopro_cli.repositories.repository import SectionRepository


class SectionService:
    """Service for section business logic.

    Encapsulates rules and orchestrates section operations via the
    section repository.
    """

    def __init__(self, section_repository: SectionRepository):
        """Initialize the section service.

        Args:
            section_repository: SectionRepository implementation for data access
        """
        self.repository = section_repository

    async def list_sections(self, project_id: str) -> list[Section]:
        """List all sections for a project.

        Args:
            project_id: Project ID

        Returns:
            List of Section objects ordered by display_order
        """
        return await self.repository.list_all(project_id)

    async def get_section(self, project_id: str, section_id: str) -> Section:
        """Get a specific section by ID.

        Args:
            project_id: Parent project ID
            section_id: Section ID

        Returns:
            Section object
        """
        return await self.repository.get(project_id, section_id)

    async def create_section(
        self,
        project_id: str,
        name: str,
        *,
        display_order: int = 0,
    ) -> Section:
        """Create a new section within a project.

        Args:
            project_id: Parent project ID
            name: Section name (required)
            display_order: Optional display position

        Returns:
            Created Section object
        """
        section_data = SectionCreate(name=name, display_order=display_order)
        return await self.repository.create(project_id, section_data)

    async def update_section(
        self,
        project_id: str,
        section_id: str,
        *,
        name: str | None = None,
        display_order: int | None = None,
    ) -> Section:
        """Update an existing section.

        Args:
            project_id: Parent project ID
            section_id: Section ID to update
            name: Updated section name
            display_order: Updated display position

        Returns:
            Updated Section object
        """
        updates = SectionUpdate(name=name, display_order=display_order)
        return await self.repository.update(project_id, section_id, updates)

    async def delete_section(self, project_id: str, section_id: str) -> bool:
        """Delete a section.

        Tasks in the section remain in the project (section FK cleared server-side).

        Args:
            project_id: Parent project ID
            section_id: Section ID to delete

        Returns:
            True if deletion was successful
        """
        return await self.repository.delete(project_id, section_id)

    async def reorder_sections(
        self, project_id: str, section_orders: list[dict]
    ) -> None:
        """Reorder sections within a project.

        Args:
            project_id: Parent project ID
            section_orders: List of dicts with 'section_id' and 'display_order'
        """
        await self.repository.reorder(project_id, section_orders)


def get_section_service() -> SectionService:
    """Factory function to get a SectionService instance."""
    from todopro_cli.services.config_service import (
        get_storage_strategy_context,  # type: ignore
    )

    storage_strategy_context = get_storage_strategy_context()
    return SectionService(storage_strategy_context.section_repository)
