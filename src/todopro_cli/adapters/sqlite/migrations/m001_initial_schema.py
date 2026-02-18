"""Initial database schema migration.

This migration creates all initial tables for the TodoPro local vault:
- users
- projects
- labels
- contexts
- tasks
- task_labels (junction)
- task_contexts (junction)
- reminders
- filters
- schema_version (created by migration system)
"""

import sqlite3

from todopro_cli.adapters.sqlite import schema
from .runner import Migration


class InitialSchemaMigration(Migration):
    """Migration 001: Create initial database schema."""

    @property
    def version(self) -> int:
        return 1

    @property
    def description(self) -> str:
        return "Initial database schema"

    def up(self, connection: sqlite3.Connection) -> None:
        """Create all initial tables."""
        # Users table
        connection.execute(schema.CREATE_USERS_TABLE)

        # Projects table
        connection.execute(schema.CREATE_PROJECTS_TABLE)

        # Labels table
        connection.execute(schema.CREATE_LABELS_TABLE)

        # Contexts table
        connection.execute(schema.CREATE_CONTEXTS_TABLE)

        # Tasks table
        connection.execute(schema.CREATE_TASKS_TABLE)

        # Junction tables
        connection.execute(schema.CREATE_TASK_LABELS_TABLE)
        connection.execute(schema.CREATE_TASK_CONTEXTS_TABLE)

        # Future tables
        connection.execute(schema.CREATE_REMINDERS_TABLE)
        connection.execute(schema.CREATE_FILTERS_TABLE)

        # Create all indexes
        for index_sql in schema.ALL_INDEXES:
            connection.execute(index_sql)


# Export singleton instance
initial_migration = InitialSchemaMigration()
