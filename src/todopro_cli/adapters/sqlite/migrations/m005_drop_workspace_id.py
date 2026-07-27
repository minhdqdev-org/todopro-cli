"""Migration 005: Drop the dead workspace_id column from projects.

The backend deleted the `workspaces` table outright (SPEC-SCHEMA-REDESIGN
phase 4 — it was a tenancy layer nothing ever used), and core-svc is the source
of truth for the data model. The API never sent or accepted a `workspace_id`,
so the local column has always been NULL for anything synced and only ever held
values a user could not have set: no CLI command exposes it.

`ALTER TABLE ... DROP COLUMN` needs SQLite 3.35 (2021). Python usually links a
newer one, but the CLI runs on whatever a user's machine has, so older builds
fall back to the table-rebuild dance. Both paths are idempotent — a fresh
database never had the column, because the v5 schema drops it too.
"""

from __future__ import annotations

import sqlite3

from todopro_cli.adapters.sqlite.migrations.runner import Migration


class DropWorkspaceIdMigration(Migration):
    """Remove projects.workspace_id, left behind by the backend's dead tenancy layer."""

    @property
    def version(self) -> int:
        return 5

    @property
    def description(self) -> str:
        return "Drop the dead workspace_id column from the projects table"

    def up(self, connection: sqlite3.Connection) -> None:
        cursor = connection.cursor()

        existing_cols = {
            row[1] for row in cursor.execute("PRAGMA table_info(projects)").fetchall()
        }
        if "workspace_id" not in existing_cols:
            return

        if sqlite3.sqlite_version_info >= (3, 35, 0):
            cursor.execute("ALTER TABLE projects DROP COLUMN workspace_id")
            connection.commit()
            return

        # Pre-3.35 fallback: rebuild the table without the column. Foreign keys
        # must be off for the rename, and they cannot be toggled inside a
        # transaction — hence the explicit commit before PRAGMA.
        connection.commit()
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            cursor.execute("""
                CREATE TABLE projects_new (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    color TEXT,
                    is_favorite BOOLEAN DEFAULT 0,
                    is_archived BOOLEAN DEFAULT 0,
                    protected BOOLEAN DEFAULT 0,
                    user_id TEXT NOT NULL,
                    display_order INTEGER,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    deleted_at DATETIME,
                    version INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                INSERT INTO projects_new (
                    id, name, color, is_favorite, is_archived, protected,
                    user_id, display_order, created_at, updated_at,
                    deleted_at, version
                )
                SELECT id, name, color, is_favorite, is_archived, protected,
                       user_id, display_order, created_at, updated_at,
                       deleted_at, version
                FROM projects
            """)
            cursor.execute("DROP TABLE projects")
            cursor.execute("ALTER TABLE projects_new RENAME TO projects")
            # DROP TABLE took the indexes with it.
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_favorite ON projects(is_favorite)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_archived ON projects(is_archived)"
            )
            connection.commit()
        finally:
            connection.execute("PRAGMA foreign_keys = ON")


drop_workspace_id_migration = DropWorkspaceIdMigration()
