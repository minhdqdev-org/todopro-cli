"""SQLite implementation of TaskRepository."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from todopro_cli.adapters.sqlite.connection import get_connection
from todopro_cli.adapters.sqlite.e2ee import E2EEHandler
from todopro_cli.adapters.sqlite.user_manager import get_or_create_local_user
from todopro_cli.adapters.sqlite.utils import generate_uuid, now_iso, row_to_dict
from todopro_cli.models import Task, TaskCreate, TaskFilters, TaskUpdate
from todopro_cli.models.config_models import AppConfig
from todopro_cli.repositories import TaskRepository


class SqliteTaskRepository(TaskRepository):
    """SQLite implementation of task repository."""

    def __init__(self, db_path: str | None = None, config_service=None):
        """Initialize SQLite task repository.

        Args:
            db_path: Optional database file path. If None, uses default location.
            config_service: Optional config manager for user ID and E2EE settings.
        """
        self.db_path = db_path
        self.config_service = config_service
        self._connection: sqlite3.Connection | None = None
        self._user_id: str | None = None
        self._e2ee_handler: E2EEHandler | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = get_connection(self.db_path)
        return self._connection

    @property
    def e2ee(self) -> E2EEHandler:
        """Get E2EE handler."""
        if self._e2ee_handler is None:
            from todopro_cli.adapters.sqlite.e2ee import get_e2ee_handler

            self._e2ee_handler = get_e2ee_handler()
        return self._e2ee_handler

    def _get_user_id(self) -> str:
        """Get current user ID from config or database."""
        if self._user_id is not None:
            return self._user_id

        # Try to get from context config first
        if self.config_service:
            try:
                current_context = self.config_service.get_current_context()
                if current_context and current_context.local_user_id:
                    self._user_id = current_context.local_user_id
                    return self._user_id
            except Exception:
                pass

        # Get or create user from database
        user_id = get_or_create_local_user(self.connection)
        self._user_id = user_id

        # Save to context config if possible
        if self.config_service:
            try:
                current_context = self.config_service.get_current_context()
                if current_context and not current_context.local_user_id:
                    self.config_service.add_context(
                        current_context.name,
                        current_context.endpoint,
                        current_context.description,
                    )
                    # Update local_user_id in context
                    config_dict = self.config_service.config.model_dump()
                    config_dict["contexts"][current_context.name]["local_user_id"] = (
                        user_id
                    )
                    self.config_service._config = AppConfig(**config_dict)
                    self.config_service.save_config()
            except Exception:
                pass

        return user_id

    async def list_all(self, filters: TaskFilters) -> list[Task]:
        """List all tasks with filtering."""
        user_id = self._get_user_id()

        # Build query
        query = """
            SELECT t.* FROM tasks t
            WHERE t.user_id = ? AND t.deleted_at IS NULL
        """
        params: list[Any] = [user_id]

        # Apply filters
        if filters.id_prefix:
            query += " AND t.id LIKE ?"
            params.append(f"{filters.id_prefix}%")

        if filters.status == "active":
            query += " AND t.is_completed = 0"
        elif filters.status == "completed":
            query += " AND t.is_completed = 1"
        # "all" means no filter on is_completed

        if filters.project_id:
            query += " AND t.project_id = ?"
            params.append(filters.project_id)

        if filters.priority is not None:
            query += " AND t.priority = ?"
            params.append(filters.priority)

        if filters.search:
            query += " AND (t.content LIKE ? OR t.description LIKE ?)"
            search_term = f"%{filters.search}%"
            params.extend([search_term, search_term])

        if filters.due_before:
            query += " AND t.due_date <= ?"
            params.append(
                filters.due_before.isoformat()
                if isinstance(filters.due_before, datetime)
                else filters.due_before
            )

        if filters.due_after:
            query += " AND t.due_date >= ?"
            params.append(
                filters.due_after.isoformat()
                if isinstance(filters.due_after, datetime)
                else filters.due_after
            )

        # Sorting
        if filters.sort:
            sort_field, *sort_dir = filters.sort.split(":")
            direction = sort_dir[0].upper() if sort_dir else "ASC"
            if sort_field in ["due_date", "priority", "created_at", "updated_at"]:
                query += f" ORDER BY t.{sort_field} {direction}"
        else:
            query += " ORDER BY t.priority ASC, t.project_id ASC, t.created_at DESC"

        # Pagination
        if filters.limit is not None:
            query += " LIMIT ?"
            params.append(filters.limit)

        if filters.offset is not None:
            query += " OFFSET ?"
            params.append(filters.offset)

        # Execute query
        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        # Convert to Task models with labels
        tasks = []
        for row in rows:
            task_dict = row_to_dict(row)

            # Decrypt content if E2EE is enabled
            if self.e2ee.enabled:
                content, description = self.e2ee.extract_task_content(
                    task_dict.get("content", ""),
                    task_dict.get("content_encrypted"),
                    task_dict.get("description", ""),
                    task_dict.get("description_encrypted"),
                )
                task_dict["content"] = content
                task_dict["description"] = description

            task_dict["labels"] = self._get_task_labels(task_dict["id"])
            task_dict["contexts"] = self._get_task_contexts(task_dict["id"])
            tasks.append(Task(**task_dict))

        return tasks

    async def get(self, task_id: str) -> Task:
        """Get a specific task by ID."""
        user_id = self._get_user_id()

        cursor = self.connection.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (task_id, user_id),
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Task not found: {task_id}")

        task_dict = row_to_dict(row)

        # Decrypt content if E2EE is enabled
        if self.e2ee.enabled:
            content, description = self.e2ee.extract_task_content(
                task_dict.get("content", ""),
                task_dict.get("content_encrypted"),
                task_dict.get("description", ""),
                task_dict.get("description_encrypted"),
            )
            task_dict["content"] = content
            task_dict["description"] = description

        task_dict["labels"] = self._get_task_labels(task_id)
        task_dict["contexts"] = self._get_task_contexts(task_id)

        return Task(**task_dict)

    async def get_by_id(self, id: str):
        """Alias for get() method for compatibility."""
        return await self.get(id)

    async def add(self, task_data: TaskCreate) -> Task:
        """Create a new task."""
        user_id = self._get_user_id()
        task_id = generate_uuid()
        now = now_iso()

        # Convert TaskCreate to dict
        data = task_data.model_dump(exclude={"labels", "contexts"})

        # Convert datetime to ISO string
        if (
            "due_date" in data
            and data["due_date"] is not None
            and isinstance(data["due_date"], datetime)
        ):
            data["due_date"] = data["due_date"].isoformat()

        # Prepare content for storage (with E2EE if enabled)
        content, content_encrypted, description, description_encrypted = (
            self.e2ee.prepare_task_for_storage(data["content"], data.get("description"))
        )

        # Insert task
        self.connection.execute(
            """INSERT INTO tasks (
                id, content, description, content_encrypted, description_encrypted,
                project_id, due_date, priority, is_completed, user_id, 
                created_at, updated_at, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                content,
                description,
                content_encrypted,
                description_encrypted,
                data.get("project_id"),
                data.get("due_date"),
                data.get("priority", 4),
                False,
                user_id,
                now,
                now,
                1,
            ),
        )

        # Add labels
        if task_data.labels:
            self._set_task_labels(task_id, task_data.labels)

        # Add contexts
        if task_data.contexts:
            self._set_task_contexts(task_id, task_data.contexts)

        self.connection.commit()

        return await self.get(task_id)

    async def update(self, task_id: str, updates: TaskUpdate) -> Task:
        """Update an existing task."""
        user_id = self._get_user_id()
        now = now_iso()

        # Build update query
        update_dict = updates.model_dump(
            exclude_none=True, exclude={"labels", "contexts"}
        )

        if not update_dict:
            return await self.get(task_id)

        # Convert datetime to ISO string
        if (
            "due_date" in update_dict
            and update_dict["due_date"] is not None
            and isinstance(update_dict["due_date"], datetime)
        ):
            update_dict["due_date"] = update_dict["due_date"].isoformat()

        # Handle E2EE for content and description updates
        if "content" in update_dict or "description" in update_dict:
            # Get current task to preserve existing content if not updating
            current_task = await self.get(task_id)
            content = update_dict.get("content", current_task.content)
            description = update_dict.get("description", current_task.description)

            # Prepare for storage
            content, content_encrypted, description, description_encrypted = (
                self.e2ee.prepare_task_for_storage(content, description)
            )

            # Replace in update dict
            if "content" in update_dict:
                update_dict["content"] = content
                update_dict["content_encrypted"] = content_encrypted
            if "description" in update_dict:
                update_dict["description"] = description
                update_dict["description_encrypted"] = description_encrypted

        set_parts = []
        params = []
        for key, value in update_dict.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        # Always update updated_at and increment version
        set_parts.append("updated_at = ?")
        set_parts.append("version = version + 1")
        params.append(now)

        query = f"UPDATE tasks SET {', '.join(set_parts)} WHERE id = ? AND user_id = ?"
        params.extend([task_id, user_id])

        self.connection.execute(query, params)

        # Update labels if provided
        if updates.labels is not None:
            self._set_task_labels(task_id, updates.labels)

        # Update contexts if provided
        if updates.contexts is not None:
            self._set_task_contexts(task_id, updates.contexts)

        self.connection.commit()

        return await self.get(task_id)

    async def delete(self, task_id: str) -> bool:
        """Delete a task (soft delete)."""
        user_id = self._get_user_id()
        now = now_iso()

        self.connection.execute(
            "UPDATE tasks SET deleted_at = ? WHERE id = ? AND user_id = ?",
            (now, task_id, user_id),
        )
        self.connection.commit()

        return True

    async def complete(self, task_id: str) -> Task:
        """Mark a task as completed."""
        user_id = self._get_user_id()
        now = now_iso()

        self.connection.execute(
            """UPDATE tasks 
               SET is_completed = 1, completed_at = ?, updated_at = ?, version = version + 1
               WHERE id = ? AND user_id = ?""",
            (now, now, task_id, user_id),
        )
        self.connection.commit()

        return await self.get(task_id)

    async def bulk_update(self, task_ids: list[str], updates: TaskUpdate) -> list[Task]:
        """Update multiple tasks at once."""
        # Use transaction for atomicity
        try:
            self.connection.execute("BEGIN")

            updated_tasks = []
            for task_id in task_ids:
                task = await self.update(task_id, updates)
                updated_tasks.append(task)

            self.connection.commit()
            return updated_tasks
        except Exception as e:
            self.connection.rollback()
            raise e

    def _get_task_labels(self, task_id: str) -> list[str]:
        """Get label IDs for a task."""
        cursor = self.connection.execute(
            "SELECT label_id FROM task_labels WHERE task_id = ?", (task_id,)
        )
        return [row[0] for row in cursor.fetchall()]

    def _get_task_contexts(self, task_id: str) -> list[str]:
        """Get context IDs for a task."""
        cursor = self.connection.execute(
            "SELECT context_id FROM task_contexts WHERE task_id = ?", (task_id,)
        )
        return [row[0] for row in cursor.fetchall()]

    def _set_task_labels(self, task_id: str, label_ids: list[str]) -> None:
        """Set labels for a task (replaces existing)."""
        # Remove existing
        self.connection.execute("DELETE FROM task_labels WHERE task_id = ?", (task_id,))

        # Add new
        for label_id in label_ids:
            self.connection.execute(
                "INSERT INTO task_labels (task_id, label_id) VALUES (?, ?)",
                (task_id, label_id),
            )

    def _set_task_contexts(self, task_id: str, context_ids: list[str]) -> None:
        """Set contexts for a task (replaces existing)."""
        # Remove existing
        self.connection.execute(
            "DELETE FROM task_contexts WHERE task_id = ?", (task_id,)
        )

        # Add new
        for context_id in context_ids:
            self.connection.execute(
                "INSERT INTO task_contexts (task_id, context_id) VALUES (?, ?)",
                (task_id, context_id),
            )
