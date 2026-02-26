"""Tests for m002_sync_compat.py (SyncCompatibilityMigration) — 0% → target 90%+."""

from __future__ import annotations

import sqlite3

import pytest

from todopro_cli.adapters.sqlite.migrations.m002_sync_compat import (
    SyncCompatibilityMigration,
)
from todopro_cli.adapters.sqlite.migrations.runner import Migration


# ---------------------------------------------------------------------------
# Helpers (same v1 schema as test_migration_v2)
# ---------------------------------------------------------------------------


def _make_v1_connection(tmp_path) -> sqlite3.Connection:
    """Create a v1 SQLite DB with the schema the migration expects."""
    conn = sqlite3.connect(str(tmp_path / "v1_m002.db"), isolation_level=None)
    conn.executescript("""
        CREATE TABLE labels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#808080',
            user_id TEXT NOT NULL,
            created_at DATETIME NOT NULL
        );

        CREATE TABLE contexts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            radius REAL NOT NULL DEFAULT 100.0,
            user_id TEXT NOT NULL,
            created_at DATETIME NOT NULL
        );

        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            description TEXT,
            is_completed BOOLEAN DEFAULT 0,
            due_date DATETIME,
            priority INTEGER DEFAULT 3,
            project_id TEXT,
            user_id TEXT NOT NULL,
            assigned_to_id TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            completed_at DATETIME,
            deleted_at DATETIME,
            version INTEGER DEFAULT 1,
            content_encrypted TEXT,
            description_encrypted TEXT,
            is_urgent BOOLEAN DEFAULT 0,
            is_important BOOLEAN DEFAULT 0,
            recurrence_rule TEXT,
            parent_task_id TEXT
        );

        CREATE TABLE reminders (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            remind_at DATETIME NOT NULL,
            is_triggered BOOLEAN DEFAULT 0,
            created_at DATETIME NOT NULL
        );

        CREATE TABLE filters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            query TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at DATETIME NOT NULL
        );

        CREATE TABLE task_labels (
            task_id TEXT NOT NULL,
            label_id TEXT NOT NULL,
            PRIMARY KEY (task_id, label_id)
        );

        CREATE TABLE task_contexts (
            task_id TEXT NOT NULL,
            context_id TEXT NOT NULL,
            PRIMARY KEY (task_id, context_id)
        );
    """)
    return conn


def _populate_v1(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO labels VALUES ('lbl-1','important','#FF0000','usr-1',datetime('now'))"
    )
    conn.execute(
        "INSERT INTO contexts VALUES ('ctx-1','office',37.77,-122.41,200.0,'usr-1',datetime('now'))"
    )
    conn.execute(
        "INSERT INTO tasks VALUES "
        "('tsk-1','Write tests',NULL,0,NULL,3,NULL,'usr-1',NULL,"
        "datetime('now'),datetime('now'),NULL,NULL,1,NULL,NULL,0,0,'FREQ=WEEKLY',NULL)"
    )
    conn.execute(
        "INSERT INTO reminders VALUES ('rem-1','tsk-1',datetime('now'),0,datetime('now'))"
    )
    conn.execute(
        "INSERT INTO filters VALUES ('fil-1','This week','due:this-week','usr-1',datetime('now'))"
    )


def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


# ---------------------------------------------------------------------------
# Class properties
# ---------------------------------------------------------------------------


class TestSyncCompatibilityMigrationProperties:
    """Verify the Migration contract (version / description)."""

    def setup_method(self):
        self.migration = SyncCompatibilityMigration()

    def test_is_migration_subclass(self):
        assert isinstance(self.migration, Migration)

    def test_version_is_2(self):
        assert self.migration.version == 2

    def test_description_is_nonempty_string(self):
        assert isinstance(self.migration.description, str)
        assert len(self.migration.description.strip()) > 0

    def test_description_mentions_sync(self):
        assert "sync" in self.migration.description.lower()


# ---------------------------------------------------------------------------
# up() – schema creation
# ---------------------------------------------------------------------------


class TestSyncCompatibilityMigrationUp:
    """Test the forward migration (up method)."""

    def test_up_runs_without_error(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        migration = SyncCompatibilityMigration()
        migration.up(conn)  # Should not raise

    def test_up_creates_labels_v2_columns(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        SyncCompatibilityMigration().up(conn)
        cols = _get_columns(conn, "labels")
        for col in ("updated_at", "deleted_at", "version", "color"):
            assert col in cols, f"labels missing column: {col}"

    def test_up_creates_contexts_v2_columns(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        SyncCompatibilityMigration().up(conn)
        cols = _get_columns(conn, "contexts")
        for col in ("updated_at", "deleted_at", "version", "color", "icon"):
            assert col in cols, f"contexts missing column: {col}"

    def test_up_creates_tasks_v2_columns(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        SyncCompatibilityMigration().up(conn)
        cols = _get_columns(conn, "tasks")
        for col in ("assigned_by_id", "assigned_at", "is_recurring", "estimated_time",
                    "actual_time", "pomodoros_completed"):
            assert col in cols, f"tasks missing column: {col}"

    def test_up_creates_reminders_v2_columns(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        SyncCompatibilityMigration().up(conn)
        cols = _get_columns(conn, "reminders")
        for col in ("is_snoozed", "snoozed_until", "snoozed_from_id"):
            assert col in cols, f"reminders missing column: {col}"

    def test_up_creates_filters_v2_columns(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        SyncCompatibilityMigration().up(conn)
        cols = _get_columns(conn, "filters")
        assert "updated_at" in cols

    def test_up_creates_junction_tables(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        SyncCompatibilityMigration().up(conn)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "task_labels" in tables
        assert "task_contexts" in tables

    def test_up_creates_indexes(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        SyncCompatibilityMigration().up(conn)
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert len(indexes) > 0

    def test_up_migrates_data_preserving_counts(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        _populate_v1(conn)
        SyncCompatibilityMigration().up(conn)
        assert conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM filters").fetchone()[0] == 1

    def test_up_remaps_priority_3_to_1(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        _populate_v1(conn)
        SyncCompatibilityMigration().up(conn)
        row = conn.execute("SELECT priority FROM tasks WHERE id='tsk-1'").fetchone()
        assert row[0] == 1

    def test_up_sets_is_recurring_for_tasks_with_recurrence_rule(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        _populate_v1(conn)
        SyncCompatibilityMigration().up(conn)
        row = conn.execute("SELECT is_recurring FROM tasks WHERE id='tsk-1'").fetchone()
        assert row[0] == 1

    def test_up_empty_db_still_runs_without_error(self, tmp_path):
        conn = _make_v1_connection(tmp_path)
        # No data – migration should still succeed
        SyncCompatibilityMigration().up(conn)
        assert conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0] == 0
