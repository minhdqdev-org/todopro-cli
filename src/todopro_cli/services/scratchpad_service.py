"""Scratchpad service – business logic for project scratchpad operations.

Scratchpads are project-scoped free-form notes. They are a **remote-only**
concept — the local SQLite context does not implement the scratchpad port, so
these operations require an active remote context.
"""

from __future__ import annotations

from todopro_cli.models import Scratchpad, ScratchpadCreate, ScratchpadUpdate
from todopro_cli.repositories.repository import ScratchpadRepository


class ScratchpadService:
    """Service for scratchpad business logic.

    Encapsulates rules and orchestrates scratchpad operations via the
    scratchpad repository.
    """

    def __init__(self, scratchpad_repository: ScratchpadRepository):
        """Initialize the scratchpad service.

        Args:
            scratchpad_repository: ScratchpadRepository implementation for data access
        """
        self.repository = scratchpad_repository

    async def list_scratchpads(self, project_id: str) -> list[Scratchpad]:
        """List all scratchpads for a project.

        Args:
            project_id: Project ID

        Returns:
            List of Scratchpad objects ordered by display_order
        """
        return await self.repository.list_all(project_id)

    async def get_scratchpad(self, scratchpad_id: str) -> Scratchpad:
        """Get a specific scratchpad by ID.

        Args:
            scratchpad_id: Scratchpad ID

        Returns:
            Scratchpad object
        """
        return await self.repository.get(scratchpad_id)

    async def create_scratchpad(
        self,
        project_id: str,
        *,
        title: str = "",
        content: str = "",
    ) -> Scratchpad:
        """Create a new scratchpad within a project.

        Args:
            project_id: Parent project ID
            title: Optional short title
            content: Optional note body

        Returns:
            Created Scratchpad object
        """
        scratchpad_data = ScratchpadCreate(title=title, content=content)
        return await self.repository.create(project_id, scratchpad_data)

    async def update_scratchpad(
        self,
        scratchpad_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
    ) -> Scratchpad:
        """Update an existing scratchpad.

        Args:
            scratchpad_id: Scratchpad ID to update
            title: Updated title
            content: Updated note body

        Returns:
            Updated Scratchpad object
        """
        updates = ScratchpadUpdate(title=title, content=content)
        return await self.repository.update(scratchpad_id, updates)

    async def delete_scratchpad(self, scratchpad_id: str) -> bool:
        """Delete a scratchpad.

        Args:
            scratchpad_id: Scratchpad ID to delete

        Returns:
            True if deletion was successful
        """
        return await self.repository.delete(scratchpad_id)


def get_scratchpad_service() -> ScratchpadService:
    """Factory function to get a ScratchpadService instance."""
    from todopro_cli.services.config_service import (
        get_storage_strategy_context,  # type: ignore
    )

    storage_strategy_context = get_storage_strategy_context()
    return ScratchpadService(storage_strategy_context.scratchpad_repository)
