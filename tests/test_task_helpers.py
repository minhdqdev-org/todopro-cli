"""Tests for task helper utilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.utils.task_helpers import _find_shortest_unique_suffix, resolve_task_id


def _make_task(id: str, content: str = "Task content") -> MagicMock:
    """Helper: create a mock Task object with .id and .content attributes."""
    t = MagicMock()
    t.id = id
    t.content = content
    return t


def test_find_shortest_unique_suffix():
    """Test finding the shortest unique suffix."""
    task_ids = [
        "task-abc123",
        "task-def456",
        "task-ghi789",
    ]

    # Each should be unique with just the last char
    assert _find_shortest_unique_suffix(task_ids, "task-abc123") == "3"
    assert _find_shortest_unique_suffix(task_ids, "task-def456") == "6"
    assert _find_shortest_unique_suffix(task_ids, "task-ghi789") == "9"


def test_find_shortest_unique_suffix_with_collisions():
    """Test finding unique suffix when there are partial collisions."""
    task_ids = [
        "task-abc123",
        "task-def123",  # Ends with same "123"
        "task-ghi456",
    ]

    # Need more chars to be unique
    assert _find_shortest_unique_suffix(task_ids, "task-abc123") == "c123"
    assert _find_shortest_unique_suffix(task_ids, "task-def123") == "f123"
    assert _find_shortest_unique_suffix(task_ids, "task-ghi456") == "6"


@pytest.mark.asyncio
async def test_resolve_task_id_full_id():
    """Test resolving a full task ID returns it as-is when get_task succeeds."""
    mock_service = MagicMock()
    mock_service.get_task = AsyncMock(return_value=_make_task("task-abc123def"))

    with patch("todopro_cli.services.cache_service.get_suffix_mapping", return_value={}):
        result = await resolve_task_id(mock_service, "task-abc123def")

    assert result == "task-abc123def"
    mock_service.get_task.assert_called_once_with("task-abc123def")


@pytest.mark.asyncio
async def test_resolve_task_id_suffix():
    """Test resolving a task ID suffix via the id_suffix filter."""
    mock_service = MagicMock()
    mock_service.get_task = AsyncMock(side_effect=Exception("Not found"))
    # list_tasks(id_suffix="123def", status="all") returns the matching task
    mock_service.list_tasks = AsyncMock(
        return_value=[_make_task("task-abc123def", "My task")]
    )

    with patch("todopro_cli.services.cache_service.get_suffix_mapping", return_value={}):
        result = await resolve_task_id(mock_service, "123def")

    assert result == "task-abc123def"
    mock_service.list_tasks.assert_called_once_with(id_suffix="123def", status="all")


@pytest.mark.asyncio
async def test_resolve_task_id_suffix_no_match():
    """Test resolving a suffix with no matches raises ValueError."""
    mock_service = MagicMock()
    mock_service.get_task = AsyncMock(side_effect=Exception("Not found"))
    mock_service.list_tasks = AsyncMock(return_value=[])

    with (
        patch("todopro_cli.services.cache_service.get_suffix_mapping", return_value={}),
        pytest.raises(ValueError, match="No task found with ID or suffix"),
    ):
        await resolve_task_id(mock_service, "notfound")


@pytest.mark.asyncio
async def test_resolve_task_id_suffix_multiple_matches():
    """Test resolving a suffix with multiple matches raises error with suggestions."""
    mock_service = MagicMock()
    mock_service.get_task = AsyncMock(side_effect=Exception("Not found"))

    all_tasks = [
        _make_task("task-abc123", "First task"),
        _make_task("task-def123", "Second task"),
        _make_task("task-ghi456", "Third task"),
    ]

    def list_tasks_side_effect(**kwargs):
        if kwargs.get("id_suffix"):
            # Return only the tasks matching the suffix
            suffix = kwargs["id_suffix"]
            return [t for t in all_tasks if t.id.endswith(suffix)]
        # Called for suggestions context (status="all", limit=1000)
        return all_tasks

    mock_service.list_tasks = AsyncMock(side_effect=list_tasks_side_effect)

    with (
        patch("todopro_cli.services.cache_service.get_suffix_mapping", return_value={}),
        pytest.raises(ValueError) as exc_info,
    ):
        await resolve_task_id(mock_service, "123")

    error_msg = str(exc_info.value)
    assert "Multiple tasks match suffix" in error_msg
    assert "First task" in error_msg or "Second task" in error_msg
    assert "[" in error_msg and "]" in error_msg


@pytest.mark.asyncio
async def test_resolve_task_id_with_suffix_mapping():
    """Test that suffix_mapping is checked before any service calls."""
    mock_service = MagicMock()

    with patch(
        "todopro_cli.utils.task_cache.get_suffix_mapping",
        return_value={"abc": "full-uuid-abc-123"},
    ), patch(
        "todopro_cli.services.cache_service.get_suffix_mapping",
        return_value={"abc": "full-uuid-abc-123"},
    ):
        result = await resolve_task_id(mock_service, "abc")

    assert result == "full-uuid-abc-123"
    mock_service.get_task.assert_not_called()
    mock_service.list_tasks.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_task_id_direct_match_via_get_task():
    """Test that a direct task ID match via get_task skips list_tasks entirely."""
    mock_service = MagicMock()
    mock_service.get_task = AsyncMock(return_value=_make_task("full-task-id-xyz"))

    with patch("todopro_cli.services.cache_service.get_suffix_mapping", return_value={}):
        result = await resolve_task_id(mock_service, "full-task-id-xyz")

    assert result == "full-task-id-xyz"
    mock_service.list_tasks.assert_not_called()


def test_find_shortest_unique_suffix_full_id_fallback():
    """When no unique suffix can be found, returns the full ID."""
    task_ids = ["same-id", "same-id"]
    result = _find_shortest_unique_suffix(task_ids, "same-id")
    assert result == "same-id"


@pytest.mark.asyncio
async def test_resolve_task_id_long_content_truncated():
    """Test that long content is truncated in multiple match error message."""
    mock_service = MagicMock()
    mock_service.get_task = AsyncMock(side_effect=Exception("Not found"))

    long_content = "A" * 100  # > 70 chars, should be truncated

    all_tasks = [
        _make_task("task-abc123", long_content),
        _make_task("task-def123", long_content),
    ]

    def list_tasks_side_effect(**kwargs):
        if kwargs.get("id_suffix"):
            suffix = kwargs["id_suffix"]
            return [t for t in all_tasks if t.id.endswith(suffix)]
        return all_tasks

    mock_service.list_tasks = AsyncMock(side_effect=list_tasks_side_effect)

    with (
        patch("todopro_cli.services.cache_service.get_suffix_mapping", return_value={}),
        pytest.raises(ValueError, match="Multiple tasks match"),
    ):
        await resolve_task_id(mock_service, "123")


@pytest.mark.asyncio
async def test_resolve_task_id_uses_id_suffix_filter():
    """Test that resolve_task_id passes id_suffix and status='all' to list_tasks.

    This is the regression test for the bug where limit=100 caused tasks
    beyond the first page (sorted by priority) to not be found.
    """
    mock_service = MagicMock()
    mock_service.get_task = AsyncMock(side_effect=Exception("Not found"))

    target = _make_task("e88f6869-6e3a-4629-8ae4-2f5fdc791739", "Xin chao")
    mock_service.list_tasks = AsyncMock(return_value=[target])

    with patch("todopro_cli.services.cache_service.get_suffix_mapping", return_value={}):
        result = await resolve_task_id(mock_service, "739")

    assert result == "e88f6869-6e3a-4629-8ae4-2f5fdc791739"
    mock_service.list_tasks.assert_called_once_with(id_suffix="739", status="all")
