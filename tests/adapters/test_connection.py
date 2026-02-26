"""Unit tests for DatabaseConnection (connection.py)."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from todopro_cli.adapters.sqlite.connection import (
    DatabaseConnection,
    get_connection,
)


# ---------------------------------------------------------------------------
# Helpers – reset singleton state between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset DatabaseConnection singleton state before each test."""
    # Close and clear any existing connection
    DatabaseConnection.close_connection()
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None
    DatabaseConnection._db_path = None
    yield
    # Cleanup after test
    DatabaseConnection.close_connection()
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None
    DatabaseConnection._db_path = None


# ---------------------------------------------------------------------------
# Singleton pattern
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_same_instance_returned_twice(self):
        inst1 = DatabaseConnection()
        inst2 = DatabaseConnection()
        assert inst1 is inst2

    def test_new_returns_singleton(self):
        inst = DatabaseConnection.__new__(DatabaseConnection)
        assert inst is DatabaseConnection.__new__(DatabaseConnection)


# ---------------------------------------------------------------------------
# get_connection
# ---------------------------------------------------------------------------


class TestGetConnection:
    def test_returns_sqlite_connection_for_temp_db(self, tmp_path):
        db_file = tmp_path / "test.db"
        conn = DatabaseConnection.get_connection(db_path=str(db_file))
        assert isinstance(conn, sqlite3.Connection)
        db_file.unlink(missing_ok=True)

    def test_creates_db_file(self, tmp_path):
        db_file = tmp_path / "vault.db"
        assert not db_file.exists()
        DatabaseConnection.get_connection(db_path=str(db_file))
        assert db_file.exists()

    def test_same_connection_returned_for_same_path(self, tmp_path):
        db_file = tmp_path / "test2.db"
        conn1 = DatabaseConnection.get_connection(db_path=str(db_file))
        conn2 = DatabaseConnection.get_connection(db_path=str(db_file))
        assert conn1 is conn2

    def test_new_connection_when_path_changes(self, tmp_path):
        db1 = tmp_path / "db1.db"
        db2 = tmp_path / "db2.db"
        conn1 = DatabaseConnection.get_connection(db_path=str(db1))
        conn2 = DatabaseConnection.get_connection(db_path=str(db2))
        # Different paths → different connections
        assert conn1 is not conn2

    def test_connection_has_row_factory(self, tmp_path):
        db_file = tmp_path / "row.db"
        conn = DatabaseConnection.get_connection(db_path=str(db_file))
        assert conn.row_factory is sqlite3.Row

    def test_foreign_keys_enabled(self, tmp_path):
        db_file = tmp_path / "fk.db"
        conn = DatabaseConnection.get_connection(db_path=str(db_file))
        cursor = conn.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "subdir" / "deep" / "vault.db"
        DatabaseConnection.get_connection(db_path=str(nested))
        assert nested.parent.exists()

    def test_default_path_uses_user_data_dir(self, tmp_path):
        """When db_path=None, falls back to user_data_dir location."""
        fake_dir = tmp_path / "todopro-cli"
        fake_dir.mkdir()
        with patch(
            "todopro_cli.adapters.sqlite.connection.user_data_dir",
            return_value=str(fake_dir),
        ):
            conn = DatabaseConnection.get_connection(db_path=None)
        assert isinstance(conn, sqlite3.Connection)


# ---------------------------------------------------------------------------
# close_connection
# ---------------------------------------------------------------------------


class TestCloseConnection:
    def test_close_clears_connection_and_path(self, tmp_path):
        db_file = tmp_path / "close_test.db"
        DatabaseConnection.get_connection(db_path=str(db_file))
        instance = DatabaseConnection()
        assert instance._connection is not None
        DatabaseConnection.close_connection()
        assert instance._connection is None
        assert instance._db_path is None

    def test_close_on_no_connection_is_safe(self):
        # Should not raise even if there's no connection
        DatabaseConnection.close_connection()

    def test_handles_error_during_close(self, tmp_path):
        db_file = tmp_path / "err_close.db"
        DatabaseConnection.get_connection(db_path=str(db_file))
        instance = DatabaseConnection()
        # Force the commit to raise
        original_conn = instance._connection
        bad_conn = MagicMock(spec=sqlite3.Connection)
        bad_conn.commit.side_effect = Exception("commit error")
        instance._connection = bad_conn
        # Should not raise
        DatabaseConnection.close_connection()
        assert instance._connection is None


# ---------------------------------------------------------------------------
# get_db_path
# ---------------------------------------------------------------------------


class TestGetDbPath:
    def test_returns_none_before_connection(self):
        assert DatabaseConnection.get_db_path() is None

    def test_returns_path_after_connection(self, tmp_path):
        db_file = tmp_path / "path_test.db"
        DatabaseConnection.get_connection(db_path=str(db_file))
        result = DatabaseConnection.get_db_path()
        assert result == db_file

    def test_returns_none_after_close(self, tmp_path):
        db_file = tmp_path / "close_path.db"
        DatabaseConnection.get_connection(db_path=str(db_file))
        DatabaseConnection.close_connection()
        assert DatabaseConnection.get_db_path() is None


# ---------------------------------------------------------------------------
# execute_with_retry
# ---------------------------------------------------------------------------


class TestExecuteWithRetry:
    def test_executes_simple_query(self, tmp_path):
        db_file = tmp_path / "retry.db"
        conn = DatabaseConnection.get_connection(db_path=str(db_file))
        cursor = DatabaseConnection.execute_with_retry(
            conn, "SELECT 1 AS val"
        )
        row = cursor.fetchone()
        assert row[0] == 1

    def test_executes_query_with_params(self, tmp_path):
        db_file = tmp_path / "retry_params.db"
        conn = DatabaseConnection.get_connection(db_path=str(db_file))
        cursor = DatabaseConnection.execute_with_retry(
            conn, "SELECT ? + ? AS result", (3, 4)
        )
        row = cursor.fetchone()
        assert row[0] == 7

    def test_retries_on_locked_db_and_eventually_raises(self, tmp_path):
        locked_error = sqlite3.OperationalError("database is locked")

        # Use a MagicMock connection since sqlite3.Connection.execute is read-only
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_conn.execute.side_effect = locked_error

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(sqlite3.OperationalError, match="database is locked"):
                DatabaseConnection.execute_with_retry(
                    mock_conn, "SELECT 1", max_retries=3
                )
            # Should have slept twice (retries 0 and 1, not after last attempt)
            assert mock_sleep.call_count == 2

    def test_non_locked_error_raises_immediately(self, tmp_path):
        db_file = tmp_path / "syntax_err.db"
        conn = DatabaseConnection.get_connection(db_path=str(db_file))
        with pytest.raises(sqlite3.OperationalError):
            DatabaseConnection.execute_with_retry(conn, "THIS IS NOT SQL")

    def test_succeeds_after_transient_lock(self, tmp_path):
        db_file = tmp_path / "transient.db"
        real_conn = DatabaseConnection.get_connection(db_path=str(db_file))
        real_cursor = real_conn.execute("SELECT 1")

        locked_error = sqlite3.OperationalError("database is locked")
        call_count = 0

        mock_conn = MagicMock(spec=sqlite3.Connection)

        def flaky_execute(sql, params=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise locked_error
            return real_cursor

        mock_conn.execute.side_effect = flaky_execute

        with patch("time.sleep"):
            cursor = DatabaseConnection.execute_with_retry(
                mock_conn, "SELECT 1", max_retries=3
            )
        assert cursor is real_cursor


# ---------------------------------------------------------------------------
# Module-level helper get_connection()
# ---------------------------------------------------------------------------


class TestModuleLevelGetConnection:
    def test_returns_connection(self, tmp_path):
        db_file = tmp_path / "helper.db"
        conn = get_connection(db_path=str(db_file))
        assert isinstance(conn, sqlite3.Connection)

    def test_execute_with_retry_max_retries_zero(self, tmp_path):
        """max_retries=0 triggers the dead-code safety raise on line 176."""
        mock_conn = MagicMock(spec=sqlite3.Connection)
        with pytest.raises(sqlite3.OperationalError, match="Max retries exceeded"):
            DatabaseConnection.execute_with_retry(
                mock_conn, "SELECT 1", max_retries=0
            )
