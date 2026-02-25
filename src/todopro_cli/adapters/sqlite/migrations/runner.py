"""Migration framework for SQLite database schema evolution.

This module provides a simple migration system with:
- Sequential version-based migrations
- Forward-only migration support
- Migration validation and tracking
- Automatic execution on startup
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from datetime import UTC, datetime


class Migration(ABC):
    """Base class for database migrations."""

    @property
    @abstractmethod
    def version(self) -> int:
        """Migration version number (sequential)."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the migration."""

    @abstractmethod
    def up(self, connection: sqlite3.Connection) -> None:
        """Execute forward migration.

        Args:
            connection: Database connection
        """


class MigrationRunner:
    """Manages and executes database migrations."""

    def __init__(self, connection: sqlite3.Connection):
        """Initialize migration runner.

        Args:
            connection: Database connection
        """
        self.connection = connection
        self._ensure_version_table()

    def _ensure_version_table(self) -> None:
        """Create schema_version table if it doesn't exist."""
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at DATETIME NOT NULL
            )
        """)
        self.connection.commit()

    def get_current_version(self) -> int:
        """Get current database schema version.

        Returns:
            Current version number (0 if no migrations applied)
        """
        cursor = self.connection.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()[0]
        return result if result is not None else 0

    def run_migration(self, migration: Migration) -> None:
        """Run a single migration.

        Args:
            migration: Migration to execute

        Raises:
            ValueError: If migration version is not greater than current version
        """
        current_version = self.get_current_version()

        if migration.version <= current_version:
            raise ValueError(
                f"Migration version {migration.version} is not greater than "
                f"current version {current_version}"
            )

        # Execute migration in a transaction
        try:
            migration.up(self.connection)

            # Record migration
            now = datetime.now(UTC).isoformat()
            self.connection.execute(
                """
                INSERT INTO schema_version (version, description, applied_at)
                VALUES (?, ?, ?)
                """,
                (migration.version, migration.description, now),
            )

            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise RuntimeError(f"Migration {migration.version} failed: {str(e)}") from e

    def run_migrations(self, migrations: list[Migration]) -> int:
        """Run all pending migrations.

        Args:
            migrations: List of migrations to potentially run

        Returns:
            Number of migrations applied
        """
        current_version = self.get_current_version()

        # Sort migrations by version
        sorted_migrations = sorted(migrations, key=lambda m: m.version)

        # Filter to only pending migrations
        pending = [m for m in sorted_migrations if m.version > current_version]

        # Run each pending migration
        for migration in pending:
            self.run_migration(migration)

        return len(pending)

    def get_migration_history(self) -> list[dict]:
        """Get history of applied migrations.

        Returns:
            List of migration records with version, description, and applied_at
        """
        cursor = self.connection.execute("""
            SELECT version, description, applied_at
            FROM schema_version
            ORDER BY version
            """)

        return [
            {"version": row[0], "description": row[1], "applied_at": row[2]}
            for row in cursor.fetchall()
        ]


def get_current_version(connection: sqlite3.Connection) -> int:
    """Helper function to get current schema version.

    Args:
        connection: Database connection

    Returns:
        Current version number
    """
    runner = MigrationRunner(connection)
    return runner.get_current_version()


def run_migrations(connection: sqlite3.Connection, migrations: list[Migration]) -> int:
    """Helper function to run migrations.

    Args:
        connection: Database connection
        migrations: List of migrations

    Returns:
        Number of migrations applied
    """
    runner = MigrationRunner(connection)
    return runner.run_migrations(migrations)
