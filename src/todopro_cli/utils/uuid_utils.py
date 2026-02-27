"""UUID utility functions for TodoPro CLI.

Provides UUID validation, short UUID display, and UUID resolution.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.repository import ProjectRepository, TaskRepository

# UUID v4 pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Relaxed UUID pattern (any version)
UUID_RELAXED_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID.

    Args:
        value: String to validate

    Returns:
        True if value is a valid UUID
    """
    if not isinstance(value, str):
        return False
    return UUID_RELAXED_PATTERN.match(value) is not None


def is_full_uuid(value: str) -> bool:
    """Check if string is a full UUID (36 characters).

    Args:
        value: String to check

    Returns:
        True if value is 36 characters and matches UUID pattern
    """
    return len(value) == 36 and is_valid_uuid(value)


def shorten_uuid(uuid: str, length: int = 8) -> str:
    """Get shortened version of UUID.

    Args:
        uuid: Full UUID string
        length: Number of characters to return (default 8)

    Returns:
        First N characters of UUID
    """
    return uuid[:length]


def format_uuid_short(uuid: str) -> str:
    """Format UUID for display in lists (first 8 chars).

    Args:
        uuid: Full UUID string

    Returns:
        Shortened UUID (8 characters)
    """
    return shorten_uuid(uuid, 8)


async def resolve_task_uuid(
    short_or_full_id: str, repository: TaskRepository, min_length: int = 8
) -> str:
    """Resolve a short or full UUID to a full UUID for tasks.

    Args:
        short_or_full_id: Either full UUID or prefix (min 8 chars)
        repository: TaskRepository instance
        min_length: Minimum length for short UUIDs (default 8)

    Returns:
        Full UUID string

    Raises:
        ValueError: If ID is too short, not found, or ambiguous
    """
    # Normalize to lowercase
    short_or_full_id = short_or_full_id.lower().strip()

    # If it's a full UUID, validate and return
    if is_full_uuid(short_or_full_id):
        # Verify it exists
        task = await repository.get(short_or_full_id)
        if task is None:
            raise ValueError(f"Task not found: {short_or_full_id}")
        return short_or_full_id

    # Must be at least min_length characters
    if len(short_or_full_id) < min_length:
        raise ValueError(
            f"ID must be at least {min_length} characters. "
            f"Got: {short_or_full_id} ({len(short_or_full_id)} chars)"
        )

    # Search for tasks with this prefix
    from todopro_cli.models import TaskFilters

    tasks = await repository.list_all(TaskFilters(id_prefix=short_or_full_id))

    if len(tasks) == 0:
        raise ValueError(f"Task not found: {short_or_full_id}")

    if len(tasks) > 1:
        # Show first few matches
        matches = ", ".join([shorten_uuid(t.id) for t in tasks[:5]])
        if len(tasks) > 5:
            matches += f", ... ({len(tasks)} total)"
        raise ValueError(
            f"Ambiguous ID '{short_or_full_id}' matches {len(tasks)} tasks: {matches}"
        )

    return tasks[0].id


async def resolve_project_uuid(
    short_or_full_id: str, repository: ProjectRepository, min_length: int = 8
) -> str:
    """Resolve a short UUID, full UUID, or project name to a full UUID.

    Tries in order: full UUID → UUID prefix → case-insensitive name match.

    Args:
        short_or_full_id: Full UUID, UUID prefix (min 8 chars), or project name
        repository: ProjectRepository instance
        min_length: Minimum length for UUID prefix matching (default 8)

    Returns:
        Full UUID string

    Raises:
        ValueError: If not found or ambiguous
    """
    short_or_full_id_stripped = short_or_full_id.strip()
    normalized = short_or_full_id_stripped.lower()

    # Full UUID — look up by id directly
    if is_full_uuid(normalized):
        project = await repository.get(normalized)
        if project is None:
            raise ValueError(f"Project not found: {short_or_full_id_stripped}")
        return normalized

    # Looks like a UUID prefix (only hex digits and dashes) — try prefix search
    uuid_prefix_re = re.compile(r"^[0-9a-f\-]+$", re.IGNORECASE)
    if uuid_prefix_re.match(normalized) and len(normalized) >= min_length:
        from todopro_cli.models import ProjectFilters

        projects = await repository.list_all(ProjectFilters(id_prefix=normalized))
        if len(projects) == 1:
            return projects[0].id
        if len(projects) > 1:
            matches = ", ".join([shorten_uuid(p.id) for p in projects[:5]])
            if len(projects) > 5:
                matches += f", ... ({len(projects)} total)"
            raise ValueError(
                f"Ambiguous ID '{short_or_full_id_stripped}' matches {len(projects)} projects: {matches}"
            )
        # No UUID prefix match — fall through to name search

    # Try case-insensitive name search
    from todopro_cli.models import ProjectFilters

    projects = await repository.list_all(ProjectFilters(search=short_or_full_id_stripped))
    # Filter to exact case-insensitive name match
    name_matches = [p for p in projects if p.name.lower() == normalized]
    if len(name_matches) == 1:
        return name_matches[0].id
    if len(name_matches) > 1:
        matches = ", ".join([p.name for p in name_matches[:5]])
        raise ValueError(
            f"Ambiguous name '{short_or_full_id_stripped}' matches {len(name_matches)} projects: {matches}"
        )

    raise ValueError(f"Project not found: '{short_or_full_id_stripped}' (tried UUID, UUID prefix, and name)")


def validate_uuid_field(value: str | None, field_name: str = "id") -> str | None:
    """Validate a UUID field value.

    Args:
        value: UUID string to validate
        field_name: Name of field (for error messages)

    Returns:
        Validated UUID or None

    Raises:
        ValueError: If UUID is invalid
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    if not is_valid_uuid(value):
        raise ValueError(f"Invalid UUID for {field_name}: {value}")

    return value.lower()
