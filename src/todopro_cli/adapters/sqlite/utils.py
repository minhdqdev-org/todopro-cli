"""Utility functions for SQLite adapter."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any


def generate_uuid() -> str:
    """Generate a new UUID as string.

    Returns:
        UUID string (e.g., "123e4567-e89b-12d3-a456-426614174000")
    """
    return str(uuid.uuid4())


def now_iso() -> str:
    """Get current timestamp in ISO format.

    Returns:
        ISO format datetime string
    """
    return datetime.now(UTC).isoformat()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two geographic points using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in meters
    """
    # Earth's radius in meters
    r = 6371000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def row_to_dict(row: Any) -> dict[str, Any]:
    """Convert sqlite3.Row to dictionary.

    Args:
        row: sqlite3.Row object

    Returns:
        Dictionary with column names as keys
    """
    if row is None:
        return {}
    return dict(row)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse datetime from various formats.

    Args:
        value: String, datetime object, or None

    Returns:
        datetime object or None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    return None


def build_where_clause(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """Build SQL WHERE clause from filter dictionary.

    Args:
        filters: Dictionary of field names to values

    Returns:
        Tuple of (WHERE clause string, parameters list)
    """
    conditions = []
    params = []

    for key, value in filters.items():
        if value is not None:
            conditions.append(f"{key} = ?")
            params.append(value)

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params


def build_update_clause(updates: dict[str, Any]) -> tuple[str, list[Any]]:
    """Build SQL UPDATE SET clause from updates dictionary.

    Args:
        updates: Dictionary of field names to new values

    Returns:
        Tuple of (SET clause string, parameters list)
    """
    set_parts = []
    params = []

    for key, value in updates.items():
        if value is not None:
            set_parts.append(f"{key} = ?")
            params.append(value)

    set_clause = ", ".join(set_parts)
    return set_clause, params


def is_soft_deleted(row: dict[str, Any]) -> bool:
    """Check if a row is soft-deleted.

    Args:
        row: Dictionary representing a database row

    Returns:
        True if row has deleted_at timestamp
    """
    return row.get("deleted_at") is not None
