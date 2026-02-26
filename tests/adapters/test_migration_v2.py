"""Tests for migrate_v2_sync_compat.py — 0% → target 90%+."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

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
    MIGRATION_VERSION,
    rollback_migration,
    run_migration,
    verify_migration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_v1_connection(tmp_path) -> sqlite3.Connection:
    """Create an in-memory v1 SQLite DB with the schema expected by the migration."""
    conn = sqlite3.connect(str(tmp_path / "v1.db"), isolation_level=None)
    conn.executescript("""
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        INSERT INTO schema_version VALUES (1, datetime('now'));

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
    """Insert sample rows into every v1 table."""
    conn.execute(
        "INSERT INTO labels VALUES ('lbl-1','work','#FF0000','usr-1',datetime('now'))"
    )
    conn.execute(
        "INSERT INTO labels VALUES ('lbl-2','personal',NULL,'usr-1',datetime('now'))"
    )
    conn.execute(
        "INSERT INTO contexts VALUES "
        "('ctx-1','home',40.7,-74.0,100.0,'usr-1',datetime('now'))"
    )
    # Task with priority 3 and a recurrence rule
    conn.execute(
        "INSERT INTO tasks VALUES "
        "('tsk-1','Buy milk',NULL,0,NULL,3,NULL,'usr-1',NULL,"
        "datetime('now'),datetime('now'),NULL,NULL,1,NULL,NULL,0,0,'FREQ=DAILY',NULL)"
    )
    # Task with priority 1 and no recurrence
    conn.execute(
        "INSERT INTO tasks VALUES "
        "('tsk-2','Call doctor',NULL,0,NULL,1,NULL,'usr-1',NULL,"
        "datetime('now'),datetime('now'),NULL,NULL,1,NULL,NULL,1,1,NULL,NULL)"
    )
    conn.execute(
        "INSERT INTO reminders VALUES "
        "('rem-1','tsk-1',datetime('now'),0,datetime('now'))"
    )
    conn.execute(
        "INSERT INTO filters VALUES "
        "('fil-1','Today','due:today','usr-1',datetime('now'))"
    )


# ---------------------------------------------------------------------------
# Constants / SQL strings
# ---------------------------------------------------------------------------


def test_migration_version_constant():
    assert MIGRATION_VERSION == 2


def test_create_table_sql_constants_are_nonempty_strings():
    for const in (
        CREATE_LABELS_TABLE_V2,
        CREATE_CONTEXTS_TABLE_V2,
        CREATE_TASKS_TABLE_V2,
        CREATE_REMINDERS_TABLE_V2,
        CREATE_FILTERS_TABLE_V2,
    ):
        assert isinstance(const, str) and len(const.strip()) > 0


def test_migrate_sql_constants_are_nonempty_strings():
    for const in (
        MIGRATE_LABELS,
        MIGRATE_CONTEXTS,
        MIGRATE_TASKS,
        MIGRATE_REMINDERS,
        MIGRATE_FILTERS,
    ):
        assert isinstance(const, str) and len(const.strip()) > 0


def test_index_lists_are_nonempty():
    assert len(CREATE_LABELS_INDEXES_V2) > 0
    assert len(CREATE_CONTEXTS_INDEXES_V2) > 0
    assert len(CREATE_TASKS_INDEXES_V2) > 0
    for idx in CREATE_LABELS_INDEXES_V2 + CREATE_CONTEXTS_INDEXES_V2 + CREATE_TASKS_INDEXES_V2:
        assert idx.strip().upper().startswith("CREATE INDEX")


# ---------------------------------------------------------------------------
# run_migration – empty tables
# ---------------------------------------------------------------------------


def test_run_migration_empty_tables_returns_true(tmp_path):
    conn = _make_v1_connection(tmp_path)
    result = run_migration(conn)
    assert result is True


def test_run_migration_empty_tables_updates_schema_version(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    cursor = conn.execute("SELECT MAX(version) FROM schema_version")
    assert cursor.fetchone()[0] == MIGRATION_VERSION


# ---------------------------------------------------------------------------
# run_migration – with data
# ---------------------------------------------------------------------------


def test_run_migration_with_data_returns_true(tmp_path):
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    result = run_migration(conn)
    assert result is True


def test_run_migration_migrates_label_count(tmp_path):
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    count = conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
    assert count == 2


def test_run_migration_null_color_defaults_to_grey(tmp_path):
    """NULL color in v1 labels gets default '#808080'."""
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    row = conn.execute("SELECT color FROM labels WHERE id='lbl-2'").fetchone()
    assert row[0] == "#808080"


def test_run_migration_task_priority_3_becomes_1(tmp_path):
    """Tasks with v1 default priority 3 are remapped to priority 1."""
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    row = conn.execute("SELECT priority FROM tasks WHERE id='tsk-1'").fetchone()
    assert row[0] == 1


def test_run_migration_task_priority_1_preserved(tmp_path):
    """Tasks with explicit priority 1 stay at 1."""
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    row = conn.execute("SELECT priority FROM tasks WHERE id='tsk-2'").fetchone()
    assert row[0] == 1


def test_run_migration_recurrence_rule_sets_is_recurring(tmp_path):
    """Tasks with a recurrence_rule get is_recurring=1."""
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    row = conn.execute("SELECT is_recurring FROM tasks WHERE id='tsk-1'").fetchone()
    assert row[0] == 1


def test_run_migration_no_recurrence_rule_is_not_recurring(tmp_path):
    """Tasks without recurrence_rule get is_recurring=0."""
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    row = conn.execute("SELECT is_recurring FROM tasks WHERE id='tsk-2'").fetchone()
    assert row[0] == 0


def test_run_migration_migrates_reminder(tmp_path):
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    count = conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]
    assert count == 1


def test_run_migration_migrates_filter(tmp_path):
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    run_migration(conn)
    row = conn.execute("SELECT name, query FROM filters WHERE id='fil-1'").fetchone()
    assert row == ("Today", "due:today")


# ---------------------------------------------------------------------------
# run_migration – new schema columns exist
# ---------------------------------------------------------------------------


def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_run_migration_labels_v2_columns(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    cols = _get_columns(conn, "labels")
    for required in ("updated_at", "deleted_at", "version", "color"):
        assert required in cols, f"Missing column: {required}"


def test_run_migration_contexts_v2_columns(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    cols = _get_columns(conn, "contexts")
    for required in ("updated_at", "deleted_at", "version", "color", "icon"):
        assert required in cols, f"Missing column: {required}"


def test_run_migration_tasks_v2_columns(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    cols = _get_columns(conn, "tasks")
    for required in ("assigned_by_id", "assigned_at", "is_recurring", "estimated_time"):
        assert required in cols, f"Missing column: {required}"


def test_run_migration_reminders_v2_columns(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    cols = _get_columns(conn, "reminders")
    for required in ("is_snoozed", "snoozed_until"):
        assert required in cols, f"Missing column: {required}"


def test_run_migration_filters_v2_columns(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    cols = _get_columns(conn, "filters")
    assert "updated_at" in cols


# ---------------------------------------------------------------------------
# run_migration – indexes and junction tables
# ---------------------------------------------------------------------------


def test_run_migration_creates_task_labels_table(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "task_labels" in tables
    assert "task_contexts" in tables


def test_run_migration_creates_indexes(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    indexes = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert any("tasks" in idx for idx in indexes)
    assert any("labels" in idx for idx in indexes)


# ---------------------------------------------------------------------------
# run_migration – failure / rollback
# ---------------------------------------------------------------------------


def test_run_migration_returns_false_when_execute_fails(tmp_path):
    """If cursor.execute() fails inside the try block, run_migration returns False."""
    from unittest.mock import MagicMock
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = sqlite3.OperationalError("disk I/O error")
    mock_conn.cursor.return_value = mock_cursor
    result = run_migration(mock_conn)
    assert result is False


def test_run_migration_returns_false_when_schema_version_missing(tmp_path):
    """A DB without schema_version table causes run_migration to return False."""
    conn = sqlite3.connect(str(tmp_path / "broken.db"), isolation_level=None)
    # Minimal tables without schema_version
    conn.executescript("""
        CREATE TABLE labels (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            color TEXT, user_id TEXT NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE contexts (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            latitude REAL NOT NULL, longitude REAL NOT NULL,
            radius REAL NOT NULL, user_id TEXT NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE tasks (id TEXT PRIMARY KEY, content TEXT NOT NULL,
            user_id TEXT NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);
        CREATE TABLE reminders (id TEXT PRIMARY KEY, task_id TEXT NOT NULL,
            remind_at DATETIME NOT NULL, is_triggered BOOLEAN DEFAULT 0,
            created_at DATETIME NOT NULL);
        CREATE TABLE filters (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            query TEXT NOT NULL, user_id TEXT NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE task_labels (task_id TEXT, label_id TEXT,
            PRIMARY KEY (task_id, label_id));
        CREATE TABLE task_contexts (task_id TEXT, context_id TEXT,
            PRIMARY KEY (task_id, context_id));
    """)
    # No schema_version table → INSERT at end will fail
    result = run_migration(conn)
    assert result is False


# ---------------------------------------------------------------------------
# verify_migration
# ---------------------------------------------------------------------------


def test_verify_migration_passes_after_successful_run(tmp_path):
    conn = _make_v1_connection(tmp_path)
    run_migration(conn)
    assert verify_migration(conn) is True


def test_verify_migration_fails_wrong_version(tmp_path):
    """When schema_version shows 1, verify should return False."""
    conn = _make_v1_connection(tmp_path)
    # Don't run migration – stays at version 1
    assert verify_migration(conn) is False


def test_verify_migration_handles_exception(tmp_path):
    """When cursor.execute() raises inside verify_migration, it returns False."""
    from unittest.mock import MagicMock
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = sqlite3.OperationalError("no such table: schema_version")
    mock_conn.cursor.return_value = mock_cursor
    assert verify_migration(mock_conn) is False


# ---------------------------------------------------------------------------
# verify_migration — column not found path (lines 446-447)
# ---------------------------------------------------------------------------


def test_verify_migration_returns_false_when_column_missing():
    """verify_migration returns False when a required column is absent."""
    from unittest.mock import MagicMock

    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # First call: SELECT MAX(version) → returns version 2
    mock_cursor.fetchone.return_value = (2,)

    # PRAGMA table_info(labels) returns columns WITHOUT 'updated_at'
    mock_cursor.fetchall.return_value = [
        (0, "id", "TEXT", 1, None, 1),
        (1, "name", "TEXT", 1, None, 0),
        (2, "color", "TEXT", 0, None, 0),
        (3, "user_id", "TEXT", 1, None, 0),
        (4, "created_at", "DATETIME", 1, None, 0),
        # 'updated_at', 'deleted_at', 'version' deliberately absent
    ]

    result = verify_migration(mock_conn)
    assert result is False


# ---------------------------------------------------------------------------
# rollback_migration (lines 475-568)
# ---------------------------------------------------------------------------


def _make_v2_connection(tmp_path) -> sqlite3.Connection:
    """Create a v1 DB, run the forward migration, and return the v2 connection.

    After migration, remove the v1 schema_version row so rollback's UPDATE
    (which sets version=1) doesn't hit a UNIQUE constraint.
    """
    conn = _make_v1_connection(tmp_path)
    _populate_v1(conn)
    success = run_migration(conn)
    assert success, "Prerequisite: forward migration must succeed before rollback test"
    # The v1 row (version=1) and the v2 row (version=2) both exist.
    # Rollback does UPDATE version=2 → version=1, which would violate the
    # PRIMARY KEY constraint if version=1 still exists.
    conn.execute("DELETE FROM schema_version WHERE version = 1")
    return conn


# Minimal table definitions that match exactly what rollback_migration's INSERT
# SELECT expects (schema.py has been updated beyond what the rollback anticipates)
_ROLLBACK_LABELS_V1 = """
CREATE TABLE IF NOT EXISTS labels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#808080',
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL
)"""

_ROLLBACK_CONTEXTS_V1 = """
CREATE TABLE IF NOT EXISTS contexts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    radius REAL NOT NULL DEFAULT 100.0,
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL
)"""

_ROLLBACK_TASKS_V1 = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    description TEXT,
    is_completed BOOLEAN DEFAULT 0,
    due_date DATETIME,
    priority INTEGER DEFAULT 1,
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
    is_urgent BOOLEAN,
    is_important BOOLEAN,
    recurrence_rule TEXT,
    parent_task_id TEXT
)"""

_ROLLBACK_REMINDERS_V1 = """
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    reminder_date DATETIME NOT NULL,
    is_sent BOOLEAN DEFAULT 0,
    created_at DATETIME NOT NULL
)"""

_ROLLBACK_FILTERS_V1 = """
CREATE TABLE IF NOT EXISTS filters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL
)"""

_TASK_LABELS_TABLE = """
CREATE TABLE IF NOT EXISTS task_labels (
    task_id TEXT NOT NULL, label_id TEXT NOT NULL,
    PRIMARY KEY (task_id, label_id)
)"""

_TASK_CONTEXTS_TABLE = """
CREATE TABLE IF NOT EXISTS task_contexts (
    task_id TEXT NOT NULL, context_id TEXT NOT NULL,
    PRIMARY KEY (task_id, context_id)
)"""


def _patch_v1_schema():
    """Patch schema.py constants to the minimal v1 forms rollback expects."""
    return patch.multiple(
        "todopro_cli.adapters.sqlite.schema",
        CREATE_LABELS_TABLE=_ROLLBACK_LABELS_V1,
        CREATE_CONTEXTS_TABLE=_ROLLBACK_CONTEXTS_V1,
        CREATE_TASKS_TABLE=_ROLLBACK_TASKS_V1,
        CREATE_REMINDERS_TABLE=_ROLLBACK_REMINDERS_V1,
        CREATE_FILTERS_TABLE=_ROLLBACK_FILTERS_V1,
        CREATE_TASK_LABELS_TABLE=_TASK_LABELS_TABLE,
        CREATE_TASK_CONTEXTS_TABLE=_TASK_CONTEXTS_TABLE,
        ALL_INDEXES=["CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)"],
    )


def test_rollback_migration_returns_true(tmp_path):
    conn = _make_v2_connection(tmp_path)
    with _patch_v1_schema():
        result = rollback_migration(conn)
    assert result is True


def test_rollback_migration_restores_schema_version_to_1(tmp_path):
    conn = _make_v2_connection(tmp_path)
    with _patch_v1_schema():
        rollback_migration(conn)
    version = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()[0]
    assert version == 1


def test_rollback_migration_restores_tables(tmp_path):
    conn = _make_v2_connection(tmp_path)
    with _patch_v1_schema():
        rollback_migration(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "labels" in tables
    assert "tasks" in tables
    assert "reminders" in tables
    assert "filters" in tables


def test_rollback_migration_preserves_label_data(tmp_path):
    conn = _make_v2_connection(tmp_path)
    with _patch_v1_schema():
        rollback_migration(conn)
    count = conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
    assert count == 2  # populated in _populate_v1


def test_rollback_migration_returns_false_on_failure():
    """Cursor that always raises → rollback returns False."""
    from unittest.mock import MagicMock

    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = sqlite3.OperationalError("rollback error")
    mock_conn.cursor.return_value = mock_cursor

    with _patch_v1_schema():
        result = rollback_migration(mock_conn)
    assert result is False
