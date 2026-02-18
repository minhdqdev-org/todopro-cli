"""Database connection management for SQLite local vault.

This module provides a singleton connection manager for the local SQLite database,
ensuring proper connection lifecycle, WAL mode, and foreign key enforcement.
"""

from __future__ import annotations

import atexit
import os
import sqlite3
from pathlib import Path

from platformdirs import user_data_dir

from todopro_cli.adapters.sqlite.migrations.m001_initial_schema import initial_migration
from todopro_cli.adapters.sqlite.migrations.runner import MigrationRunner


class DatabaseConnection:
    """Singleton connection manager for local SQLite vault.

    Provides:
    - Single connection per process (connection reuse)
    - WAL mode for better concurrency
    - Foreign key constraint enforcement
    - Automatic directory creation
    - Proper file permissions (owner read/write only)
    - Graceful cleanup on exit
    """

    _instance: DatabaseConnection | None = None
    _connection: sqlite3.Connection | None = None
    _db_path: Path | None = None

    def __new__(cls) -> DatabaseConnection:
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_connection(cls, db_path: str | Path | None = None) -> sqlite3.Connection:
        """Get or create database connection.

        Args:
            db_path: Path to database file. If None, uses default location.

        Returns:
            sqlite3.Connection object configured for TodoPro usage
        """
        instance = cls()

        # Determine database path
        if db_path is None:
            data_dir = Path(user_data_dir("todopro-cli"))
            db_path = data_dir / "vault.db"
        else:
            db_path = Path(db_path)

        # If connection exists and path hasn't changed, return it
        if instance._connection is not None and instance._db_path == db_path:
            return instance._connection

        # Close existing connection if path changed
        if instance._connection is not None:
            instance._connection.close()

        # Create data directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if database file exists (for first-time init detection)
        is_new_database = not db_path.exists()

        # Create connection
        connection = sqlite3.connect(
            str(db_path),
            check_same_thread=False,  # Allow multi-threaded access
            timeout=30.0,  # Wait up to 30s for locks
        )

        # Configure connection
        connection.row_factory = sqlite3.Row  # Enable dict-like access
        connection.execute("PRAGMA foreign_keys = ON")  # Enforce foreign keys
        connection.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging

        # Set file permissions (owner read/write only)
        if is_new_database:
            os.chmod(db_path, 0o600)

        # Run migrations to ensure schema is up to date
        cls._run_migrations(connection)

        # Store connection and path
        instance._connection = connection
        instance._db_path = db_path

        # Register cleanup on exit
        atexit.register(cls.close_connection)

        return connection

    @classmethod
    def _run_migrations(cls, connection: sqlite3.Connection) -> None:
        """Run database migrations.

        Args:
            connection: Database connection
        """
        # List of all migrations in order
        migrations = [
            initial_migration,
        ]

        # Run migrations
        runner = MigrationRunner(connection)
        runner.run_migrations(migrations)

    @classmethod
    def close_connection(cls) -> None:
        """Close database connection gracefully."""
        instance = cls()
        if instance._connection is not None:
            try:
                instance._connection.commit()  # Commit any pending transactions
                instance._connection.close()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                instance._connection = None
                instance._db_path = None

    @classmethod
    def get_db_path(cls) -> Path | None:
        """Get current database path."""
        instance = cls()
        return instance._db_path

    @classmethod
    def execute_with_retry(
        cls,
        connection: sqlite3.Connection,
        sql: str,
        params: tuple | dict | None = None,
        max_retries: int = 3,
    ) -> sqlite3.Cursor:
        """Execute SQL with retry logic for database locked errors.

        Args:
            connection: Database connection
            sql: SQL statement to execute
            params: Parameters for SQL statement
            max_retries: Maximum number of retry attempts

        Returns:
            Cursor after successful execution

        Raises:
            sqlite3.OperationalError: If database remains locked after retries
        """
        import time

        for attempt in range(max_retries):
            try:
                if params:
                    return connection.execute(sql, params)
                return connection.execute(sql)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    # Exponential backoff: 0.1s, 0.2s, 0.4s
                    time.sleep(0.1 * (2**attempt))
                    continue
                raise

        # Should never reach here, but satisfy type checker
        raise sqlite3.OperationalError("Max retries exceeded")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Helper function to get database connection.

    Args:
        db_path: Optional path to database file

    Returns:
        Configured sqlite3.Connection
    """
    return DatabaseConnection.get_connection(db_path)
