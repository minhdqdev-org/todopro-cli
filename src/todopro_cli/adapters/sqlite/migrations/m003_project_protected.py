"""Migration 003: Add protected column to projects table.

The Inbox project now uses a random UUID (like all other projects) and is
identified by protected=1 instead of a hard-coded all-zeros ID.  This migration:
- Adds the `protected` column (BOOLEAN DEFAULT 0) to the projects table.
- Sets protected=1 for any existing row whose name is 'Inbox' (case-insensitive).
"""

from __future__ import annotations

import sqlite3

from todopro_cli.adapters.sqlite.migrations.runner import Migration


class ProjectProtectedMigration(Migration):
    """Add protected flag to projects and mark existing Inbox rows."""

    @property
    def version(self) -> int:
        return 3

    @property
    def description(self) -> str:
        return (
            "Add protected column to projects table; "
            "mark existing Inbox projects as protected=1"
        )

    def up(self, connection: sqlite3.Connection) -> None:
        cursor = connection.cursor()

        # Add column only if it doesn't already exist (fresh DBs already have it via schema)
        existing_cols = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(projects)").fetchall()
        }
        if "protected" not in existing_cols:
            cursor.execute(
                "ALTER TABLE projects ADD COLUMN protected BOOLEAN NOT NULL DEFAULT 0"
            )

        # Mark all existing Inbox projects as protected
        cursor.execute(
            "UPDATE projects SET protected = 1 WHERE LOWER(name) = 'inbox'"
        )

        connection.commit()


project_protected_migration = ProjectProtectedMigration()
