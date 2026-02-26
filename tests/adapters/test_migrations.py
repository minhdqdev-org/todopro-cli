"""Unit tests for the MigrationRunner and helper functions in migrations/runner.py."""

from __future__ import annotations

import sqlite3

import pytest

from todopro_cli.adapters.sqlite.migrations.runner import (
    Migration,
    MigrationRunner,
    get_current_version,
    run_migrations,
)


# ---------------------------------------------------------------------------
# Concrete test migrations
# ---------------------------------------------------------------------------


class _Migration1(Migration):
    @property
    def version(self) -> int:
        return 1

    @property
    def description(self) -> str:
        return "Create test_table_one"

    def up(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE test_table_one (id INTEGER PRIMARY KEY, name TEXT)"
        )


class _Migration2(Migration):
    @property
    def version(self) -> int:
        return 2

    @property
    def description(self) -> str:
        return "Create test_table_two"

    def up(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE test_table_two (id INTEGER PRIMARY KEY, value TEXT)"
        )


class _FailingMigration(Migration):
    @property
    def version(self) -> int:
        return 3

    @property
    def description(self) -> str:
        return "Intentionally fails"

    def up(self, connection: sqlite3.Connection) -> None:
        raise RuntimeError("Migration failure!")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mem_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def runner(mem_conn):
    return MigrationRunner(mem_conn)


# ---------------------------------------------------------------------------
# MigrationRunner._ensure_version_table
# ---------------------------------------------------------------------------


class TestEnsureVersionTable:
    def test_schema_version_table_created(self, mem_conn):
        MigrationRunner(mem_conn)  # triggers _ensure_version_table
        cursor = mem_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        assert cursor.fetchone() is not None

    def test_idempotent_on_second_instantiation(self, mem_conn):
        MigrationRunner(mem_conn)
        MigrationRunner(mem_conn)  # should not raise


# ---------------------------------------------------------------------------
# get_current_version
# ---------------------------------------------------------------------------


class TestGetCurrentVersion:
    def test_returns_zero_on_fresh_db(self, runner):
        assert runner.get_current_version() == 0

    def test_returns_version_after_migration(self, runner, mem_conn):
        runner.run_migration(_Migration1())
        assert runner.get_current_version() == 1


# ---------------------------------------------------------------------------
# run_migration
# ---------------------------------------------------------------------------


class TestRunMigration:
    def test_applies_migration(self, runner, mem_conn):
        runner.run_migration(_Migration1())
        # Check the table was created
        cursor = mem_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table_one'"
        )
        assert cursor.fetchone() is not None

    def test_records_version(self, runner):
        runner.run_migration(_Migration1())
        assert runner.get_current_version() == 1

    def test_raises_value_error_for_already_applied_version(self, runner):
        runner.run_migration(_Migration1())
        with pytest.raises(ValueError, match="not greater than current version"):
            runner.run_migration(_Migration1())  # same version again

    def test_raises_value_error_for_older_version(self, runner):
        runner.run_migration(_Migration2())
        with pytest.raises(ValueError, match="not greater than current version"):
            runner.run_migration(_Migration1())  # version 1 < current 2

    def test_failing_migration_raises_runtime_error(self, runner, mem_conn):
        # First get to version 2 so _FailingMigration (v3) is valid in order
        runner.run_migration(_Migration1())
        runner.run_migration(_Migration2())
        with pytest.raises(RuntimeError, match="Migration 3 failed"):
            runner.run_migration(_FailingMigration())

    def test_failing_migration_does_not_record_version(self, runner, mem_conn):
        runner.run_migration(_Migration1())
        runner.run_migration(_Migration2())
        try:
            runner.run_migration(_FailingMigration())
        except RuntimeError:
            pass
        assert runner.get_current_version() == 2


# ---------------------------------------------------------------------------
# run_migrations
# ---------------------------------------------------------------------------


class TestRunMigrations:
    def test_applies_all_pending(self, runner, mem_conn):
        count = runner.run_migrations([_Migration1(), _Migration2()])
        assert count == 2
        assert runner.get_current_version() == 2

    def test_skips_already_applied(self, runner):
        runner.run_migration(_Migration1())
        count = runner.run_migrations([_Migration1(), _Migration2()])
        assert count == 1  # only migration 2 was pending
        assert runner.get_current_version() == 2

    def test_empty_list_runs_zero(self, runner):
        count = runner.run_migrations([])
        assert count == 0

    def test_out_of_order_input_is_sorted(self, runner):
        # Pass in reverse order; runner should apply 1 before 2
        count = runner.run_migrations([_Migration2(), _Migration1()])
        assert count == 2
        assert runner.get_current_version() == 2

    def test_all_already_applied_runs_zero(self, runner):
        runner.run_migrations([_Migration1(), _Migration2()])
        count = runner.run_migrations([_Migration1(), _Migration2()])
        assert count == 0


# ---------------------------------------------------------------------------
# get_migration_history
# ---------------------------------------------------------------------------


class TestGetMigrationHistory:
    def test_empty_on_fresh_db(self, runner):
        history = runner.get_migration_history()
        assert history == []

    def test_records_applied_migrations(self, runner):
        runner.run_migration(_Migration1())
        runner.run_migration(_Migration2())
        history = runner.get_migration_history()
        assert len(history) == 2
        versions = [h["version"] for h in history]
        assert versions == [1, 2]

    def test_history_item_has_required_keys(self, runner):
        runner.run_migration(_Migration1())
        history = runner.get_migration_history()
        item = history[0]
        assert "version" in item
        assert "description" in item
        assert "applied_at" in item

    def test_description_matches_migration(self, runner):
        runner.run_migration(_Migration1())
        history = runner.get_migration_history()
        assert history[0]["description"] == "Create test_table_one"


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------


class TestModuleLevelHelpers:
    def test_get_current_version_helper(self, mem_conn):
        MigrationRunner(mem_conn).run_migration(_Migration1())
        assert get_current_version(mem_conn) == 1

    def test_run_migrations_helper(self, mem_conn):
        count = run_migrations(mem_conn, [_Migration1(), _Migration2()])
        assert count == 2
        assert get_current_version(mem_conn) == 2
