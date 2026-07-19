"""Migration 004: Add deadline and recurrence_from_completion to tasks.

Adds two new task concepts to the local vault, mirroring the backend:
- `deadline` (DATETIME): a hard "must finish by" datetime, distinct from
  `due_date`. It does NOT advance on recurrence.
- `recurrence_from_completion` (BOOLEAN DEFAULT 0): when true, completing a
  recurring task re-anchors the next occurrence to completion time
  (Todoist's "every!" syntax).

Each column is added only if it doesn't already exist so the migration is
idempotent (fresh DBs already get the columns via the v1 schema).
"""

from __future__ import annotations

import sqlite3

from todopro_cli.adapters.sqlite.migrations.runner import Migration


class DeadlineRecurrenceFromCompletionMigration(Migration):
    """Add deadline and recurrence_from_completion columns to tasks."""

    @property
    def version(self) -> int:
        return 4

    @property
    def description(self) -> str:
        return "Add deadline and recurrence_from_completion columns to tasks"

    def up(self, connection: sqlite3.Connection) -> None:
        cursor = connection.cursor()

        # Determine which columns already exist (fresh DBs have them via schema)
        existing_cols = {
            row[1] for row in cursor.execute("PRAGMA table_info(tasks)").fetchall()
        }

        if "deadline" not in existing_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN deadline DATETIME")

        if "recurrence_from_completion" not in existing_cols:
            cursor.execute(
                "ALTER TABLE tasks ADD COLUMN "
                "recurrence_from_completion BOOLEAN DEFAULT 0"
            )

        # Index on deadline (mirrors idx_tasks_due_date)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)"
        )

        connection.commit()


deadline_recurrence_from_completion_migration = (
    DeadlineRecurrenceFromCompletionMigration()
)
