"""SQLite implementation of LabelRepository."""

from __future__ import annotations

import sqlite3

from todopro_cli.adapters.sqlite.connection import get_connection
from todopro_cli.adapters.sqlite.user_manager import get_or_create_local_user
from todopro_cli.adapters.sqlite.utils import generate_uuid, now_iso, row_to_dict
from todopro_cli.models import Label, LabelCreate
from todopro_cli.repositories import LabelRepository


class SqliteLabelRepository(LabelRepository):
    """SQLite implementation of label repository."""

    def __init__(self, db_path: str | None = None, config_manager=None):
        """Initialize SQLite label repository.

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

    async def list_all(self) -> list[Label]:
        """List all labels."""
        user_id = self._get_user_id()

        cursor = self.connection.execute(
            "SELECT * FROM labels WHERE user_id = ? ORDER BY name", (user_id,)
        )
        rows = cursor.fetchall()

        return [Label(**row_to_dict(row)) for row in rows]

    async def get(self, label_id: str) -> Label:
        """Get a specific label by ID."""
        user_id = self._get_user_id()

        cursor = self.connection.execute(
            "SELECT * FROM labels WHERE id = ? AND user_id = ?", (label_id, user_id)
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Label not found: {label_id}")

        return Label(**row_to_dict(row))

    async def get_by_id(self, id: str):
        """Alias for get() method for compatibility."""
        return await self.get(id)

    async def create(self, label_data: LabelCreate) -> Label:
        """Create a new label."""
        user_id = self._get_user_id()
        label_id = generate_uuid()
        now = now_iso()

        data = label_data.model_dump()

        try:
            self.connection.execute(
                """INSERT INTO labels (id, name, color, user_id, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (label_id, data["name"], data.get("color"), user_id, now),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                raise ValueError(f"Label '{data['name']}' already exists") from e
            raise

        return await self.get(label_id)

    async def delete(self, label_id: str) -> bool:
        """Delete a label."""
        user_id = self._get_user_id()

        # Delete label (cascade will remove task_labels entries)
        self.connection.execute(
            "DELETE FROM labels WHERE id = ? AND user_id = ?", (label_id, user_id)
        )
        self.connection.commit()

        return True

    async def search(self, prefix: str) -> list[Label]:
        """Search labels by name prefix (for autocomplete)."""
        user_id = self._get_user_id()

        cursor = self.connection.execute(
            "SELECT * FROM labels WHERE user_id = ? AND name LIKE ? ORDER BY name",
            (user_id, f"{prefix}%"),
        )
        rows = cursor.fetchall()

        return [Label(**row_to_dict(row)) for row in rows]
