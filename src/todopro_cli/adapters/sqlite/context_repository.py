"""SQLite implementation of LocationContextRepository."""

from __future__ import annotations

import sqlite3

from todopro_cli.adapters.sqlite.connection import get_connection
from todopro_cli.adapters.sqlite.user_manager import get_or_create_local_user
from todopro_cli.adapters.sqlite.utils import (
    generate_uuid,
    haversine_distance,
    now_iso,
    row_to_dict,
)
from todopro_cli.models import LocationContext, LocationContextCreate
from todopro_cli.repositories import LocationContextRepository


class SqliteLocationContextRepository(LocationContextRepository):
    """SQLite implementation of context repository."""

    def __init__(self, db_path: str | None = None, config_manager=None):
        """Initialize SQLite context repository.

        Args:
            db_path: Optional database file path. If None, uses default location.
            config_manager: Optional config manager for user ID.
        """
        self.db_path = db_path
        self.config_manager = config_manager
        self._connection: sqlite3.Connection | None = None
        self._user_id: str | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = get_connection(self.db_path)
        return self._connection

    def _get_user_id(self) -> str:
        """Get current user ID."""
        if self._user_id is not None:
            return self._user_id

        self._user_id = get_or_create_local_user(self.connection)
        return self._user_id

        return self._user_id

    async def list_all(self) -> list[LocationContext]:
        """List all contexts."""
        user_id = self._get_user_id()

        cursor = self.connection.execute(
            "SELECT * FROM contexts WHERE user_id = ? ORDER BY name", (user_id,)
        )
        rows = cursor.fetchall()

        return [LocationContext(**row_to_dict(row)) for row in rows]

    async def get(self, context_id: str) -> LocationContext:
        """Get a specific context by ID."""
        user_id = self._get_user_id()

        cursor = self.connection.execute(
            "SELECT * FROM contexts WHERE id = ? AND user_id = ?", (context_id, user_id)
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Context not found: {context_id}")

        return LocationContext(**row_to_dict(row))

    async def create(self, context_data: LocationContextCreate) -> LocationContext:
        """Create a new context."""
        user_id = self._get_user_id()
        context_id = generate_uuid()
        now = now_iso()

        data = context_data.model_dump()

        self.connection.execute(
            """INSERT INTO contexts (id, name, latitude, longitude, radius, user_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                context_id,
                data["name"],
                data["latitude"],
                data["longitude"],
                data.get("radius", 100.0),
                user_id,
                now,
            ),
        )
        self.connection.commit()

        return await self.get(context_id)

    async def delete(self, context_id: str) -> bool:
        """Delete a context."""
        user_id = self._get_user_id()

        # Delete context (cascade will remove task_contexts entries)
        self.connection.execute(
            "DELETE FROM contexts WHERE id = ? AND user_id = ?", (context_id, user_id)
        )
        self.connection.commit()

        return True

    async def get_available(
        self, latitude: float, longitude: float
    ) -> list[LocationContext]:
        """Get contexts available at a specific location (within geofence).

        Uses haversine formula to calculate distance and filter contexts
        where the given location is within their radius.
        """
        user_id = self._get_user_id()

        # Get all contexts for this user
        cursor = self.connection.execute(
            "SELECT * FROM contexts WHERE user_id = ?", (user_id,)
        )
        rows = cursor.fetchall()

        # Filter by distance using haversine formula
        available_contexts = []
        for row in rows:
            context_dict = row_to_dict(row)
            distance = haversine_distance(
                latitude, longitude, context_dict["latitude"], context_dict["longitude"]
            )

            # Check if within radius
            if distance <= context_dict["radius"]:
                available_contexts.append(LocationContext(**context_dict))

        return available_contexts
