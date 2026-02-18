"""SQLite implementation of ProjectRepository."""

from __future__ import annotations

import sqlite3
from typing import Any

from todopro_cli.adapters.sqlite.connection import get_connection
from todopro_cli.adapters.sqlite.user_manager import get_or_create_local_user
from todopro_cli.adapters.sqlite.utils import generate_uuid, now_iso, row_to_dict
from todopro_cli.repositories import ProjectRepository
from todopro_cli.models import Project, ProjectCreate, ProjectFilters, ProjectUpdate

INBOX_PROJECT_ID = "00000000-0000-0000-0000-000000000000"


class SqliteProjectRepository(ProjectRepository):
    """SQLite implementation of project repository."""

    def __init__(self, db_path: str | None = None, config_manager=None):
        """Initialize SQLite project repository.

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
        """Get current user ID and ensure default data exists."""
        if self._user_id is not None:
            return self._user_id

        self._user_id = get_or_create_local_user(self.connection)
        self._ensure_inbox_project(self._user_id)
        return self._user_id

    def _ensure_inbox_project(self, user_id: str) -> None:
        """Create the Inbox project with fixed ID if it doesn't exist, and migrate NULL project_ids."""
        now = now_iso()
        # Ensure the Inbox project exists with the fixed all-zeros ID
        cursor = self.connection.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ? AND deleted_at IS NULL LIMIT 1",
            (INBOX_PROJECT_ID, user_id),
        )
        if cursor.fetchone() is None:
            # Check for an old Inbox with a random ID and remove it if present
            self.connection.execute(
                "DELETE FROM projects WHERE user_id = ? AND LOWER(name) = 'inbox' AND id != ?",
                (user_id, INBOX_PROJECT_ID),
            )
            self.connection.execute(
                """INSERT OR IGNORE INTO projects (id, name, color, is_favorite, is_archived,
                       user_id, created_at, updated_at, version, display_order)
                   VALUES (?, 'Inbox', '#4a90d9', 0, 0, ?, ?, ?, 1, 0)""",
                (INBOX_PROJECT_ID, user_id, now, now),
            )
            self.connection.commit()
        # Migrate tasks with NULL project_id to Inbox
        self.connection.execute(
            "UPDATE tasks SET project_id = ? WHERE user_id = ? AND project_id IS NULL AND deleted_at IS NULL",
            (INBOX_PROJECT_ID, user_id),
        )
        self.connection.commit()

    async def list_all(self, filters: ProjectFilters) -> list[Project]:
        """List all projects with filtering."""
        user_id = self._get_user_id()

        query = "SELECT * FROM projects WHERE user_id = ? AND deleted_at IS NULL"
        params: list[Any] = [user_id]

        if filters.id_prefix:
            query += " AND id LIKE ?"
            params.append(f"{filters.id_prefix}%")

        if filters.is_favorite is not None:
            query += " AND is_favorite = ?"
            params.append(1 if filters.is_favorite else 0)

        if filters.is_archived is not None:
            query += " AND is_archived = ?"
            params.append(1 if filters.is_archived else 0)

        if filters.workspace_id:
            query += " AND workspace_id = ?"
            params.append(filters.workspace_id)

        if filters.search:
            query += " AND name LIKE ?"
            params.append(f"%{filters.search}%")

        query += " ORDER BY display_order, name"

        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        return [Project(**row_to_dict(row)) for row in rows]

    async def get(self, project_id: str) -> Project:
        """Get a specific project by ID."""
        user_id = self._get_user_id()

        cursor = self.connection.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (project_id, user_id),
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Project not found: {project_id}")

        return Project(**row_to_dict(row))


    async def get_by_id(self, id: str):
        """Alias for get() method for compatibility."""
        return await self.get(id)
    async def create(self, project_data: ProjectCreate) -> Project:
        """Create a new project."""
        user_id = self._get_user_id()
        project_id = generate_uuid()
        now = now_iso()

        data = project_data.model_dump()

        # Enforce case-insensitive name uniqueness per user
        cursor = self.connection.execute(
            "SELECT name FROM projects WHERE user_id = ? AND LOWER(name) = LOWER(?) AND deleted_at IS NULL LIMIT 1",
            (user_id, data["name"]),
        )
        existing = cursor.fetchone()
        if existing:
            existing_name = existing[0]
            if existing_name == data["name"]:
                raise ValueError(f"A project named '{data['name']}' already exists")
            raise ValueError(
                f"A project named '{existing_name}' already exists (project names are case-insensitive)"
            )

        self.connection.execute(
            """INSERT INTO projects (
                id, name, color, is_favorite, is_archived,
                workspace_id, user_id, created_at, updated_at, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                data["name"],
                data.get("color"),
                1 if data.get("is_favorite", False) else 0,
                0,
                data.get("workspace_id"),
                user_id,
                now,
                now,
                1,
            ),
        )
        self.connection.commit()

        return await self.get(project_id)

    async def update(self, project_id: str, updates: ProjectUpdate) -> Project:
        """Update an existing project."""
        user_id = self._get_user_id()
        now = now_iso()

        update_dict = updates.model_dump(exclude_none=True)

        if not update_dict:
            return await self.get(project_id)

        # Enforce case-insensitive name uniqueness per user when renaming
        if "name" in update_dict:
            cursor = self.connection.execute(
                "SELECT name FROM projects WHERE user_id = ? AND LOWER(name) = LOWER(?) AND id != ? AND deleted_at IS NULL LIMIT 1",
                (user_id, update_dict["name"], project_id),
            )
            existing = cursor.fetchone()
            if existing:
                existing_name = existing[0]
                if existing_name == update_dict["name"]:
                    raise ValueError(f"A project named '{update_dict['name']}' already exists")
                raise ValueError(
                    f"A project named '{existing_name}' already exists (project names are case-insensitive)"
                )

        set_parts = []
        params = []
        for key, value in update_dict.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        set_parts.append("updated_at = ?")
        set_parts.append("version = version + 1")
        params.append(now)

        query = (
            f"UPDATE projects SET {', '.join(set_parts)} WHERE id = ? AND user_id = ?"
        )
        params.extend([project_id, user_id])

        self.connection.execute(query, params)
        self.connection.commit()

        return await self.get(project_id)

    async def delete(self, project_id: str) -> bool:
        """Delete a project (soft delete)."""
        user_id = self._get_user_id()
        now = now_iso()

        self.connection.execute(
            "UPDATE projects SET deleted_at = ? WHERE id = ? AND user_id = ?",
            (now, project_id, user_id),
        )
        self.connection.commit()

        return True

    async def archive(self, project_id: str) -> Project:
        """Archive a project."""
        user_id = self._get_user_id()
        now = now_iso()

        self.connection.execute(
            """UPDATE projects 
               SET is_archived = 1, updated_at = ?, version = version + 1
               WHERE id = ? AND user_id = ?""",
            (now, project_id, user_id),
        )
        self.connection.commit()

        return await self.get(project_id)

    async def unarchive(self, project_id: str) -> Project:
        """Unarchive a project."""
        user_id = self._get_user_id()
        now = now_iso()

        self.connection.execute(
            """UPDATE projects 
               SET is_archived = 0, updated_at = ?, version = version + 1
               WHERE id = ? AND user_id = ?""",
            (now, project_id, user_id),
        )
        self.connection.commit()

        return await self.get(project_id)

    async def get_stats(self, project_id: str) -> dict:
        """Get project statistics."""
        user_id = self._get_user_id()

        # Count tasks by status
        cursor = self.connection.execute(
            """SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_tasks,
                SUM(CASE WHEN is_completed = 0 THEN 1 ELSE 0 END) as pending_tasks,
                SUM(CASE WHEN is_completed = 0 AND due_date < datetime('now') THEN 1 ELSE 0 END) as overdue_tasks
            FROM tasks 
            WHERE project_id = ? AND user_id = ? AND deleted_at IS NULL""",
            (project_id, user_id),
        )
        row = cursor.fetchone()

        if not row:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "overdue_tasks": 0,
                "completion_rate": 0,
            }

        total = row[0] or 0
        completed = row[1] or 0
        pending = row[2] or 0
        overdue = row[3] or 0

        completion_rate = int((completed / total * 100)) if total > 0 else 0

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending,
            "overdue_tasks": overdue,
            "completion_rate": completion_rate,
        }
