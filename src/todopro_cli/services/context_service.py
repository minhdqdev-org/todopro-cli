"""Context service - Business logic for context (location) operations."""

from __future__ import annotations

from todopro_cli.models import Context, ContextCreate
from todopro_cli.repositories.repository import ContextRepository


class ContextService:
    """Service for context business logic.

    This service encapsulates business rules and orchestrates context operations
    using the context repository.
    """

    def __init__(self, context_repository: ContextRepository):
        """Initialize the context service"""
        self.repository = context_repository

    async def list_contexts(self) -> list[Context]:
        """List all contexts"""
        return await self.repository.list_all()

    async def get_context(self, context_id: str) -> Context:
        """Get a specific context by ID"""
        return await self.repository.get(context_id)

    async def create_context(
        self,
        name: str,
        latitude: float,
        longitude: float,
        *,
        radius: float = 100.0,
    ) -> Context:
        """Create a new context.

        Args:
            name: Context name (required, e.g., "@office", "@home")
            latitude: Geographic latitude (-90 to 90)
            longitude: Geographic longitude (-180 to 180)
            radius: Geofence radius in meters (default: 100m)

        Returns:
            Created Context object
        """
        context_data = ContextCreate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
        )
        return await self.repository.create(context_data)

    async def delete_context(self, context_id: str) -> bool:
        """Delete a context.

        Args:
            context_id: Context ID to delete

        Returns:
            True if deletion was successful
        """
        return await self.repository.delete(context_id)

    async def get_available_contexts(
        self,
        latitude: float,
        longitude: float,
    ) -> list[Context]:
        """Get contexts available at a specific location.

        Returns all contexts where the given location falls within their geofence.

        Args:
            latitude: Current geographic latitude
            longitude: Current geographic longitude

        Returns:
            List of Context objects available at the location
        """
        return await self.repository.get_available(latitude, longitude)

    async def get_or_create_context(
        self,
        name: str,
        latitude: float,
        longitude: float,
        radius: float = 100.0,
    ) -> Context:
        """Get a context by name, or create it if it doesn't exist.

        This is useful for commands that reference contexts by name rather than ID.

        Args:
            name: Context name
            latitude: Geographic latitude (used if creating)
            longitude: Geographic longitude (used if creating)
            radius: Geofence radius in meters (used if creating)

        Returns:
            Existing or newly created Context object
        """
        # Search for existing context with exact name match
        contexts = await self.list_contexts()
        for context in contexts:
            if context.name.lower() == name.lower():
                return context

        # Create new context if not found
        return await self.create_context(name, latitude, longitude, radius=radius)
