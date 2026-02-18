"""User profile management for local SQLite vault.

This module handles user profile creation, timezone detection,
and user ID persistence in context configuration.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

import tzlocal


def get_system_timezone() -> str:
    """Detect system timezone.

    Returns:
        Timezone string (e.g., "America/New_York" or "UTC" if detection fails)
    """
    tz = tzlocal.get_localzone()
    return str(tz.key) if hasattr(tz, "key") else str(tz)


def create_default_user(
    connection: sqlite3.Connection, timezone: str | None = None
) -> str:
    """Create default local user profile.

    Args:
        connection: Database connection
        timezone: Optional timezone string. If None, auto-detects system timezone.

    Returns:
        User ID (UUID string)
    """
    user_id = str(uuid.uuid4())
    email = "local@todopro.local"
    name = "Local User"

    if timezone is None:
        timezone = get_system_timezone()

    now = datetime.now(UTC).isoformat()

    connection.execute(
        """
        INSERT INTO users (id, email, name, timezone, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, email, name, timezone, now, now),
    )
    connection.commit()

    return user_id


def get_or_create_local_user(connection: sqlite3.Connection) -> str:
    """Get existing local user or create one if it doesn't exist.

    Args:
        connection: Database connection

    Returns:
        User ID (UUID string)
    """
    # Try to get existing user
    cursor = connection.execute("SELECT id FROM users LIMIT 1")
    row = cursor.fetchone()

    if row:
        return row[0]

    # No user exists, create default one
    return create_default_user(connection)


def update_user_timezone(
    connection: sqlite3.Connection, user_id: str, timezone: str
) -> None:
    """Update user timezone.

    Args:
        connection: Database connection
        user_id: User ID
        timezone: Timezone string
    """
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE users SET timezone = ?, updated_at = ? WHERE id = ?",
        (timezone, now, user_id),
    )
    connection.commit()


def get_user_info(connection: sqlite3.Connection, user_id: str) -> dict | None:
    """Get user information.

    Args:
        connection: Database connection
        user_id: User ID

    Returns:
        User info dict or None if not found
    """
    cursor = connection.execute(
        "SELECT id, email, name, timezone, created_at, updated_at FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()

    if row:
        return {
            "id": row[0],
            "email": row[1],
            "name": row[2],
            "timezone": row[3],
            "created_at": row[4],
            "updated_at": row[5],
        }

    return None
