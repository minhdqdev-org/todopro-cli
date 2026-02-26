"""Label service - Business logic for label operations."""

from __future__ import annotations

from todopro_cli.models import Label, LabelCreate
from todopro_cli.repositories import LabelRepository


class LabelService:
    """Service for label business logic.

    This service encapsulates business rules and orchestrates label operations
    using the label repository.
    """

    def __init__(self, label_repository: LabelRepository):
        """Initialize the label service.

        Args:
            label_repository: LabelRepository implementation for data access
        """
        self.repository = label_repository

    async def list_labels(self) -> list[Label]:
        """List all labels.

        Returns:
            List of all Label objects
        """
        return await self.repository.list_all()

    async def get_label(self, label_id: str) -> Label:
        """Get a specific label by ID.

        Args:
            label_id: Unique identifier for the label

        Returns:
            Label object
        """
        return await self.repository.get(label_id)

    async def create_label(
        self,
        name: str,
        *,
        color: str | None = None,
    ) -> Label:
        """Create a new label.

        Args:
            name: Label name (required, e.g., "@work", "@home")
            color: Optional hex color code

        Returns:
            Created Label object
        """
        label_data = LabelCreate(name=name, color=color)
        return await self.repository.create(label_data)

    async def delete_label(self, label_id: str) -> bool:
        """Delete a label.

        Args:
            label_id: Label ID to delete

        Returns:
            True if deletion was successful
        """
        return await self.repository.delete(label_id)

    async def search_labels(self, prefix: str) -> list[Label]:
        """Search labels by name prefix (for autocomplete).

        Args:
            prefix: Text prefix to match against label names

        Returns:
            List of Label objects with names starting with prefix
        """
        return await self.repository.search(prefix)

    async def get_or_create_label(self, name: str, color: str | None = None) -> Label:
        """Get a label by name, or create it if it doesn't exist.

        This is useful for commands that reference labels by name rather than ID.

        Args:
            name: Label name
            color: Optional color for new labels

        Returns:
            Existing or newly created Label object
        """
        # Search for existing label with exact name match
        labels = await self.list_labels()
        for label in labels:
            if label.name.lower() == name.lower():
                return label

        # Create new label if not found
        return await self.create_label(name, color=color)


def get_label_service():
    """Factory function to get a LabelService instance."""
    from todopro_cli.services.config_service import (
        get_storage_strategy_context,  # type: ignore
    )

    return LabelService(get_storage_strategy_context().label_repository)
