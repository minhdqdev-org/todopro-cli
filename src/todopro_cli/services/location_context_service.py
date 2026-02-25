"""Context service - Business logic for context (location) operations."""

from __future__ import annotations

from todopro_cli.models import LocationContext, LocationContextCreate
from todopro_cli.repositories.repository import LocationContextRepository


class LocationContextService:
    """Service for location context business logic.

    This service encapsulates business rules and orchestrates location context operations
    using the location context repository.
    """

    def __init__(self, context_repository: LocationContextRepository):
        """Initialize the location context service"""
        self.repository = context_repository

    async def list_location_contexts(self) -> list[LocationContext]:
        """List all location contexts"""
        return await self.repository.list_all()

    async def get_location_context(self, context_id: str) -> LocationContext:
        """Get a specific location context by ID"""
        return await self.repository.get(context_id)

    async def create_location_context(
        self,
        name: str,
        latitude: float,
        longitude: float,
        *,
        radius: float = 100.0,
    ) -> LocationContext:
        """Create a new location context.

        Args:
            name: Context name (required, e.g., "@office", "@home")
            latitude: Geographic latitude (-90 to 90)
            longitude: Geographic longitude (-180 to 180)
            radius: Geofence radius in meters (default: 100m)

        Returns:
            Created LocationContext object
        """
        context_data = LocationContextCreate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
        )
        return await self.repository.create(context_data)

    async def delete_location_context(self, context_id: str) -> bool:
        """Delete a location context.

        Args:
            context_id: Location context ID to delete

        Returns:
            True if deletion was successful
        """
        return await self.repository.delete(context_id)

    async def get_available_location_contexts(
        self,
        latitude: float,
        longitude: float,
    ) -> list[LocationContext]:
        """Get location contexts available at a specific location.

        Returns all location contexts where the given location falls within their geofence.

        Args:
            latitude: Current geographic latitude
            longitude: Current geographic longitude

        Returns:
            List of LocationContext objects available at the location
        """
        return await self.repository.get_available(latitude, longitude)

    async def get_or_create_location_context(
        self,
        name: str,
        latitude: float,
        longitude: float,
        radius: float = 100.0,
    ) -> LocationContext:
        """Get a location context by name, or create it if it doesn't exist.

        This is useful for commands that reference location contexts by name rather than ID.

        Args:
            name: Location context name
            latitude: Geographic latitude (used if creating)
            longitude: Geographic longitude (used if creating)
            radius: Geofence radius in meters (used if creating)

        Returns:
            Existing or newly created LocationContext object
        """
        # Search for existing location context with exact name match
        contexts = await self.list_location_contexts()
        for context in contexts:
            if context.name.lower() == name.lower():
                return context

        # Create new location context if not found
        return await self.create_location_context(
            name, latitude, longitude, radius=radius
        )


def get_location_context_service() -> LocationContextService:
    """Factory function to create a LocationContextService instance."""
    from todopro_cli.services.config_service import get_config_service

    return LocationContextService(
        get_config_service().storage_strategy_context.location_context_repository
    )
