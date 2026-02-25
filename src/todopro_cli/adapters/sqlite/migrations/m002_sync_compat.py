"""Migration 002: Sync compatibility - Add missing fields for backend sync.

This migration adds fields needed for reliable sync with the backend:
- Adds updated_at, deleted_at, version to labels and contexts
- Adds color and icon to contexts
- Adds updated_at to filters
- Fixes task priority default from 3 to 1
- Adds missing task fields (recurring, time tracking, assignment)
- Standardizes reminder field names
"""

from __future__ import annotations

import sqlite3

from todopro_cli.adapters.sqlite.migrations.runner import Migration


class SyncCompatibilityMigration(Migration):
    """Add fields for backend sync compatibility."""

    @property
    def version(self) -> int:
        """Migration version."""
        return 2

    @property
    def description(self) -> str:
        """Migration description."""
        return (
            "Add sync compatibility fields (updated_at, version, recurring tasks, etc.)"
        )

    def up(self, connection: sqlite3.Connection) -> None:
        """Execute forward migration.

        This uses the comprehensive v2 migration script to properly
        recreate tables with new schemas while preserving all data.
        """
        # Import the comprehensive migration function
        from todopro_cli.adapters.sqlite.migrations.migrate_v2_sync_compat import (
            CREATE_CONTEXTS_INDEXES_V2,
            CREATE_CONTEXTS_TABLE_V2,
            CREATE_FILTERS_TABLE_V2,
            CREATE_LABELS_INDEXES_V2,
            CREATE_LABELS_TABLE_V2,
            CREATE_REMINDERS_TABLE_V2,
            CREATE_TASKS_INDEXES_V2,
            CREATE_TASKS_TABLE_V2,
            MIGRATE_CONTEXTS,
            MIGRATE_FILTERS,
            MIGRATE_LABELS,
            MIGRATE_REMINDERS,
            MIGRATE_TASKS,
        )

        cursor = connection.cursor()

        # Create new tables
        cursor.execute(CREATE_LABELS_TABLE_V2)
        cursor.execute(CREATE_CONTEXTS_TABLE_V2)
        cursor.execute(CREATE_TASKS_TABLE_V2)
        cursor.execute(CREATE_REMINDERS_TABLE_V2)
        cursor.execute(CREATE_FILTERS_TABLE_V2)

        # Migrate data
        cursor.execute(MIGRATE_LABELS)
        cursor.execute(MIGRATE_CONTEXTS)
        cursor.execute(MIGRATE_TASKS)
        cursor.execute(MIGRATE_REMINDERS)
        cursor.execute(MIGRATE_FILTERS)

        # Create indexes
        for idx in CREATE_LABELS_INDEXES_V2:
            cursor.execute(idx)
        for idx in CREATE_CONTEXTS_INDEXES_V2:
            cursor.execute(idx)
        for idx in CREATE_TASKS_INDEXES_V2:
            cursor.execute(idx)

        # Drop old tables
        cursor.execute("DROP TABLE IF EXISTS task_labels")
        cursor.execute("DROP TABLE IF EXISTS task_contexts")
        cursor.execute("DROP TABLE IF EXISTS reminders")
        cursor.execute("DROP TABLE IF EXISTS tasks")
        cursor.execute("DROP TABLE IF EXISTS filters")
        cursor.execute("DROP TABLE IF EXISTS labels")
        cursor.execute("DROP TABLE IF EXISTS contexts")

        # Rename new tables
        cursor.execute("ALTER TABLE labels_v2 RENAME TO labels")
        cursor.execute("ALTER TABLE contexts_v2 RENAME TO contexts")
        cursor.execute("ALTER TABLE tasks_v2 RENAME TO tasks")
        cursor.execute("ALTER TABLE reminders_v2 RENAME TO reminders")
        cursor.execute("ALTER TABLE filters_v2 RENAME TO filters")

        # Recreate junction tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_labels (
                task_id TEXT NOT NULL,
                label_id TEXT NOT NULL,
                PRIMARY KEY (task_id, label_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_contexts (
                task_id TEXT NOT NULL,
                context_id TEXT NOT NULL,
                PRIMARY KEY (task_id, context_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (context_id) REFERENCES contexts(id) ON DELETE CASCADE
            )
        """)

        connection.commit()
