"""Tests for m005_drop_workspace_id.py (DropWorkspaceIdMigration).

The column is dead everywhere — backend, API and CLI — so the migration's whole
job is to leave existing local vaults readable while it goes away. That means
the interesting cases are the boring ones: rows survive, re-running is safe, and
a database that never had the column doesn't trip over its absence.
"""

from __future__ import annotations

import sqlite3

import pytest

from todopro_cli.adapters.sqlite.migrations.m005_drop_workspace_id import (
    DropWorkspaceIdMigration,
)


def _v4_connection(tmp_path, *, with_workspace: bool = True) -> sqlite3.Connection:
    """A projects table as it stood at schema v4 (or v5, without the column)."""
    conn = sqlite3.connect(str(tmp_path / "v4.db"))
    workspace_col = "workspace_id TEXT,\n" if with_workspace else ""
    conn.executescript(f"""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE
        );

        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            is_favorite BOOLEAN DEFAULT 0,
            is_archived BOOLEAN DEFAULT 0,
            protected BOOLEAN DEFAULT 0,
            user_id TEXT NOT NULL,
            {workspace_col}
            display_order INTEGER,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            deleted_at DATETIME,
            version INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_projects_user ON projects(user_id);
        CREATE INDEX idx_projects_favorite ON projects(is_favorite);
        CREATE INDEX idx_projects_archived ON projects(is_archived);

        INSERT INTO users (id, email) VALUES ('u1', 'a@example.com');
    """)
    return conn


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}


def test_drops_the_column_and_keeps_every_row(tmp_path):
    conn = _v4_connection(tmp_path)
    conn.execute(
        """INSERT INTO projects (
            id, name, color, is_favorite, protected, user_id, workspace_id,
            display_order, created_at, updated_at, version
        ) VALUES ('p1', 'Work', '#FF0000', 1, 1, 'u1', 'ws-1', 2,
                  '2026-01-01', '2026-01-02', 7)"""
    )
    conn.commit()

    DropWorkspaceIdMigration().up(conn)

    assert "workspace_id" not in _columns(conn)
    row = conn.execute(
        "SELECT name, color, is_favorite, protected, display_order, version"
        " FROM projects WHERE id = 'p1'"
    ).fetchone()
    assert row == ("Work", "#FF0000", 1, 1, 2, 7)


def test_is_idempotent_and_safe_on_a_fresh_database(tmp_path):
    """A v5 database never had the column; re-running must not raise."""
    conn = _v4_connection(tmp_path, with_workspace=False)
    migration = DropWorkspaceIdMigration()

    migration.up(conn)
    migration.up(conn)

    assert "workspace_id" not in _columns(conn)


def test_indexes_survive(tmp_path):
    """The rebuild path drops the table, so it has to put the indexes back."""
    conn = _v4_connection(tmp_path)
    DropWorkspaceIdMigration().up(conn)

    indexes = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='projects'"
        ).fetchall()
    }
    assert {
        "idx_projects_user",
        "idx_projects_favorite",
        "idx_projects_archived",
    } <= indexes


def test_rebuild_fallback_matches_the_drop_column_path(tmp_path, monkeypatch):
    """Force the pre-3.35 branch: same end state, rows and all."""
    conn = _v4_connection(tmp_path)
    conn.execute(
        """INSERT INTO projects (
            id, name, user_id, workspace_id, created_at, updated_at
        ) VALUES ('p1', 'Work', 'u1', 'ws-1', '2026-01-01', '2026-01-02')"""
    )
    conn.commit()

    monkeypatch.setattr(
        "todopro_cli.adapters.sqlite.migrations.m005_drop_workspace_id"
        ".sqlite3.sqlite_version_info",
        (3, 34, 0),
    )
    DropWorkspaceIdMigration().up(conn)

    assert "workspace_id" not in _columns(conn)
    assert conn.execute("SELECT name FROM projects").fetchall() == [("Work",)]


def test_migration_metadata():
    migration = DropWorkspaceIdMigration()
    assert migration.version == 5
    assert "workspace_id" in migration.description


@pytest.mark.parametrize("with_workspace", [True, False])
def test_runs_through_the_runner(tmp_path, with_workspace):
    """The runner records it, so a second startup skips it entirely."""
    from todopro_cli.adapters.sqlite.migrations.runner import MigrationRunner

    conn = _v4_connection(tmp_path, with_workspace=with_workspace)
    runner = MigrationRunner(conn)
    conn.execute(
        "INSERT INTO schema_version (version, description, applied_at)"
        " VALUES (4, 'seed', '2026-01-01')"
    )
    conn.commit()

    assert runner.run_migrations([DropWorkspaceIdMigration()]) == 1
    assert runner.get_current_version() == 5
    assert runner.run_migrations([DropWorkspaceIdMigration()]) == 0
