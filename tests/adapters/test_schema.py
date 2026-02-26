"""Unit tests for database schema module (schema.py)."""

from __future__ import annotations

import sqlite3

import pytest

from todopro_cli.adapters.sqlite import schema as db_schema
from todopro_cli.adapters.sqlite.schema import (
    ALL_INDEXES,
    ALL_TABLES,
    SCHEMA_VERSION,
    get_schema_version,
    initialize_schema,
)


@pytest.fixture
def mem_conn():
    """Fresh in-memory SQLite connection for each test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestInitializeSchema:
    def test_creates_all_tables(self, mem_conn):
        initialize_schema(mem_conn)
        cursor = mem_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        expected = {
            "users",
            "projects",
            "labels",
            "contexts",
            "tasks",
            "task_labels",
            "task_contexts",
            "reminders",
            "filters",
            "schema_version",
        }
        assert expected.issubset(tables)

    def test_creates_all_indexes(self, mem_conn):
        initialize_schema(mem_conn)
        cursor = mem_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        created_indexes = {row[0] for row in cursor.fetchall()}
        # At least one known index should exist
        assert "idx_tasks_due_date" in created_indexes
        assert "idx_tasks_project" in created_indexes
        assert "idx_projects_user" in created_indexes

    def test_records_schema_version(self, mem_conn):
        initialize_schema(mem_conn)
        cursor = mem_conn.execute("SELECT version FROM schema_version")
        versions = [row[0] for row in cursor.fetchall()]
        assert SCHEMA_VERSION in versions

    def test_idempotent_when_called_twice(self, mem_conn):
        initialize_schema(mem_conn)
        # Should not raise on second call (IF NOT EXISTS clauses)
        initialize_schema(mem_conn)

    def test_can_insert_user_after_init(self, mem_conn):
        initialize_schema(mem_conn)
        mem_conn.execute(
            "INSERT INTO users (id, email, name, timezone, created_at, updated_at) "
            "VALUES ('u1', 'a@b.com', 'Test', 'UTC', '2024-01-01', '2024-01-01')"
        )
        mem_conn.commit()
        cursor = mem_conn.execute("SELECT id FROM users")
        row = cursor.fetchone()
        assert row[0] == "u1"


class TestGetSchemaVersion:
    def test_returns_zero_on_empty_db(self, mem_conn):
        # No schema_version table exists yet
        version = get_schema_version(mem_conn)
        assert version == 0

    def test_returns_version_after_initialize(self, mem_conn):
        initialize_schema(mem_conn)
        version = get_schema_version(mem_conn)
        assert version == SCHEMA_VERSION

    def test_returns_zero_when_table_empty(self, mem_conn):
        # Create table but don't insert any rows
        mem_conn.execute(
            "CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at DATETIME)"
        )
        mem_conn.commit()
        version = get_schema_version(mem_conn)
        assert version == 0

    def test_returns_correct_version(self, mem_conn):
        # Manually insert a version
        mem_conn.execute(
            "CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at DATETIME)"
        )
        mem_conn.execute(
            "INSERT INTO schema_version VALUES (5, '2024-01-01')"
        )
        mem_conn.commit()
        version = get_schema_version(mem_conn)
        assert version == 5


class TestSchemaConstants:
    def test_all_tables_is_non_empty_list(self):
        assert isinstance(ALL_TABLES, list)
        assert len(ALL_TABLES) > 0

    def test_all_indexes_is_non_empty_list(self):
        assert isinstance(ALL_INDEXES, list)
        assert len(ALL_INDEXES) > 0

    def test_schema_version_is_positive_int(self):
        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1

    def test_table_sql_contains_create_statements(self):
        for stmt in ALL_TABLES:
            assert "CREATE TABLE" in stmt.upper()

    def test_index_sql_contains_create_index(self):
        for stmt in ALL_INDEXES:
            assert "CREATE INDEX" in stmt.upper()
