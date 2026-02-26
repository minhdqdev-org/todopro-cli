"""Tests for task helper utilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.utils.task_helpers import _find_shortest_unique_suffix, resolve_task_id


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
    """Test resolving a full task ID returns it as-is."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(return_value={"id": "task-abc123def"})

    result = await resolve_task_id(mock_tasks_api, "task-abc123def")

    assert result == "task-abc123def"
    mock_tasks_api.get_task.assert_called_once_with("task-abc123def")


@pytest.mark.asyncio
async def test_resolve_task_id_suffix():
    """Test resolving a task ID suffix."""
    mock_tasks_api = MagicMock()
    # First call fails (not a full ID)
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    # Second call returns list of tasks
    mock_tasks_api.list_tasks = AsyncMock(
        return_value={
            "items": [
                {"id": "task-xyz789"},
                {"id": "task-abc123def"},
                {"id": "task-ghi456"},
            ]
        }
    )

    result = await resolve_task_id(mock_tasks_api, "123def")

    assert result == "task-abc123def"


@pytest.mark.asyncio
async def test_resolve_task_id_suffix_no_match():
    """Test resolving a suffix with no matches raises error."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    mock_tasks_api.list_tasks = AsyncMock(
        return_value={
            "items": [
                {"id": "task-xyz789"},
                {"id": "task-ghi456"},
            ]
        }
    )

    with pytest.raises(ValueError, match="No task found with ID or suffix"):
        await resolve_task_id(mock_tasks_api, "notfound")


@pytest.mark.asyncio
async def test_resolve_task_id_suffix_multiple_matches():
    """Test resolving a suffix with multiple matches raises error with suggestions."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    mock_tasks_api.list_tasks = AsyncMock(
        return_value={
            "items": [
                {"id": "task-abc123", "content": "First task"},
                {"id": "task-def123", "content": "Second task"},
                {"id": "task-ghi456", "content": "Third task"},
            ]
        }
    )

    with pytest.raises(ValueError) as exc_info:
        await resolve_task_id(mock_tasks_api, "123")

    error_msg = str(exc_info.value)
    assert "Multiple tasks match suffix" in error_msg
    assert "First task" in error_msg or "Second task" in error_msg
    # Should suggest unique suffixes in brackets
    assert "[" in error_msg and "]" in error_msg


@pytest.mark.asyncio
async def test_resolve_task_id_with_tasks_key():
    """Test resolving when API returns 'tasks' instead of 'items'."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    mock_tasks_api.list_tasks = AsyncMock(
        return_value={
            "tasks": [
                {"id": "task-abc123def"},
                {"id": "task-ghi456"},
            ]
        }
    )

    result = await resolve_task_id(mock_tasks_api, "123def")

    assert result == "task-abc123def"


@pytest.mark.asyncio
async def test_resolve_task_id_with_list_response():
    """Test resolving when API returns a list directly."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    # API returns a list directly, not wrapped in a dict
    mock_tasks_api.list_tasks = AsyncMock(
        return_value=[
            {"id": "task-abc123def"},
            {"id": "task-ghi456"},
        ]
    )

    result = await resolve_task_id(mock_tasks_api, "123def")

    assert result == "task-abc123def"


@pytest.mark.asyncio
async def test_resolve_task_id_with_object_tasks():
    """Test resolving when tasks are objects (not dicts)."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    class FakeTask:
        def __init__(self, id, content):
            self.id = id
            self.content = content

    mock_tasks_api.list_tasks = AsyncMock(
        return_value=[
            FakeTask("task-abc123def", "Task one"),
            FakeTask("task-ghi456789", "Task two"),
        ]
    )

    result = await resolve_task_id(mock_tasks_api, "123def")
    assert result == "task-abc123def"


@pytest.mark.asyncio
async def test_resolve_task_id_object_multiple_matches():
    """Test resolving when object tasks have multiple matches raises error."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    class FakeTask:
        def __init__(self, id, content):
            self.id = id
            self.content = content

    mock_tasks_api.list_tasks = AsyncMock(
        return_value=[
            FakeTask("task-abc123", "First object task"),
            FakeTask("task-def123", "Second object task"),
            FakeTask("task-ghi456", "Other task"),
        ]
    )

    with pytest.raises(ValueError, match="Multiple tasks match suffix"):
        await resolve_task_id(mock_tasks_api, "123")


@pytest.mark.asyncio
async def test_resolve_task_id_with_suffix_mapping():
    """Test that suffix_mapping is checked first."""
    mock_tasks_api = MagicMock()

    # Patch the suffix mapping in the task_cache module (lazy import location)
    with patch(
        "todopro_cli.utils.task_cache.get_suffix_mapping",
        return_value={"abc": "full-uuid-abc-123"},
    ):
        # Also patch cache_service to handle the chain
        with patch(
            "todopro_cli.services.cache_service.get_suffix_mapping",
            return_value={"abc": "full-uuid-abc-123"},
        ):
            result = await resolve_task_id(mock_tasks_api, "abc")

    assert result == "full-uuid-abc-123"
    # The API should NOT have been called since suffix was in the mapping
    mock_tasks_api.get_task.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_task_id_direct_match_via_get_task():
    """Test that a direct task ID match via get_task returns the ID."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(return_value={"id": "full-task-id-xyz"})

    with patch(
        "todopro_cli.services.cache_service.get_suffix_mapping",
        return_value={},
    ):
        result = await resolve_task_id(mock_tasks_api, "full-task-id-xyz")

    assert result == "full-task-id-xyz"


def test_find_shortest_unique_suffix_full_id_fallback():
    """When no unique suffix can be found, returns the full ID."""
    # All identical IDs - can never find a unique suffix
    task_ids = ["same-id", "same-id"]
    result = _find_shortest_unique_suffix(task_ids, "same-id")
    assert result == "same-id"


@pytest.mark.asyncio
async def test_resolve_task_id_object_multiple_matches_long_content():
    """Test truncation of long content in multiple match error message (line 95)."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))

    class FakeTask:
        def __init__(self, id, content):
            self.id = id
            self.content = content

    long_content = "A" * 100  # > 70 chars to trigger truncation

    mock_tasks_api.list_tasks = AsyncMock(
        return_value=[
            FakeTask("task-abc123", long_content),
            FakeTask("task-def123", long_content),
        ]
    )

    with patch(
        "todopro_cli.services.cache_service.get_suffix_mapping",
        return_value={},
    ):
        with pytest.raises(ValueError, match="Multiple tasks match"):
            await resolve_task_id(mock_tasks_api, "123")
