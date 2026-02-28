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
    """Resolve a short UUID, full UUID, ID suffix, or project name to a full UUID.

    Tries in order: full UUID → cached suffix → UUID prefix → case-insensitive name match.

    Args:
        short_or_full_id: Full UUID, ID suffix (from ``tp project list``), UUID prefix, or project name
        repository: ProjectRepository instance
        min_length: Minimum length for UUID prefix matching (default 8)

    Returns:
        Full UUID string

    Raises:
        ValueError: If not found or ambiguous
    """
    short_or_full_id_stripped = short_or_full_id.strip().lstrip("#")
    normalized = short_or_full_id_stripped.lower()

    # Full UUID — look up by id directly
    if is_full_uuid(normalized):
        project = await repository.get(normalized)
        if project is None:
            raise ValueError(f"Project not found: {short_or_full_id_stripped}")
        return normalized

    # Check cached suffix mapping (populated when `tp project list` is run)
    from todopro_cli.services.cache_service import get_project_suffix_mapping

    suffix_mapping = get_project_suffix_mapping()
    if short_or_full_id_stripped in suffix_mapping:
        return suffix_mapping[short_or_full_id_stripped]

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

    # Short hex string could be a UUID suffix displayed by `tp project list` (e.g. `#8`).
    # This handles cache misses (suffix cache TTL expired) by searching all projects.
    if uuid_prefix_re.match(normalized) and len(normalized) < min_length:
        from todopro_cli.models import ProjectFilters

        all_projects = await repository.list_all(ProjectFilters())
        suffix_matches = [p for p in all_projects if p.id.endswith(normalized)]
        if len(suffix_matches) == 1:
            return suffix_matches[0].id
        if len(suffix_matches) > 1:
            matches = ", ".join([shorten_uuid(p.id) for p in suffix_matches[:5]])
            if len(suffix_matches) > 5:
                matches += f", ... ({len(suffix_matches)} total)"
            raise ValueError(
                f"Ambiguous ID '{short_or_full_id_stripped}' matches {len(suffix_matches)} projects: {matches}"
            )
        # No suffix match — fall through to name search

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

    raise ValueError(f"Project not found: '{short_or_full_id_stripped}' (tried UUID, suffix cache, UUID prefix, and name)")


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


async def resolve_label_id(label_id_or_suffix: str, label_repository) -> str:
    """Resolve a label suffix, full UUID, or label name to a full label ID.

    Tries in order: cached suffix (from ``tp label list``) → full UUID → name search.

    Args:
        label_id_or_suffix: Full UUID, suffix shown by ``tp label list``, or label name.
            May be prefixed with ``#``.
        label_repository: LabelRepository instance.

    Returns:
        Full UUID string.

    Raises:
        ValueError: If not found.
    """
    from todopro_cli.services.cache_service import get_label_suffix_mapping

    stripped = label_id_or_suffix.strip().lstrip("#")

    # Check cached suffix mapping first
    suffix_mapping = get_label_suffix_mapping()
    if stripped in suffix_mapping:
        return suffix_mapping[stripped]

    # Full UUID — direct lookup
    if is_full_uuid(stripped):
        return stripped

    # Name search
    try:
        from todopro_cli.models import LabelFilters
        labels = await label_repository.list_all(LabelFilters(search=stripped))
    except Exception:
        labels = await label_repository.list_all()
        labels = [lbl for lbl in labels if lbl.name.lower() == stripped.lower()]

    name_matches = [lbl for lbl in labels if lbl.name.lower() == stripped.lower()]
    if len(name_matches) == 1:
        return name_matches[0].id
    if len(name_matches) > 1:
        matches = ", ".join(lbl.name for lbl in name_matches[:5])
        raise ValueError(f"Ambiguous label name '{stripped}' matches: {matches}")

    raise ValueError(f"Label not found: '{stripped}' (tried suffix cache, UUID, and name)")


async def resolve_section_id(
    section_id_or_suffix: str,
    section_repository,
    project_id: str | None = None,
) -> str:
    """Resolve a section suffix or full UUID to a full section ID.

    Tries in order: cached suffix (from ``tp section list``) → full UUID.

    Args:
        section_id_or_suffix: Full UUID or suffix shown by ``tp section list``.
            May be prefixed with ``#``.
        section_repository: SectionRepository instance.
        project_id: Optional project scope for the lookup (unused currently but
            kept for future DB-level filtering).

    Returns:
        Full UUID string.

    Raises:
        ValueError: If not found.
    """
    from todopro_cli.services.cache_service import get_section_suffix_mapping

    stripped = section_id_or_suffix.strip().lstrip("#")

    # Check cached suffix mapping first
    suffix_mapping = get_section_suffix_mapping()
    if stripped in suffix_mapping:
        return suffix_mapping[stripped]

    # Full UUID — accept as-is
    if is_full_uuid(stripped):
        return stripped

    raise ValueError(
        f"Section not found: '{stripped}' — run 'tp section list <project>' to populate suffix cache"
    )
