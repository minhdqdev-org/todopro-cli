"""Tests for task helper utilities."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from todopro_cli.utils.task_helpers import resolve_task_id, _find_shortest_unique_suffix


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
    mock_tasks_api.list_tasks = AsyncMock(return_value={
        "items": [
            {"id": "task-xyz789"},
            {"id": "task-abc123def"},
            {"id": "task-ghi456"},
        ]
    })
    
    result = await resolve_task_id(mock_tasks_api, "123def")
    
    assert result == "task-abc123def"


@pytest.mark.asyncio
async def test_resolve_task_id_suffix_no_match():
    """Test resolving a suffix with no matches raises error."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))
    
    mock_tasks_api.list_tasks = AsyncMock(return_value={
        "items": [
            {"id": "task-xyz789"},
            {"id": "task-ghi456"},
        ]
    })
    
    with pytest.raises(ValueError, match="No task found with ID or suffix"):
        await resolve_task_id(mock_tasks_api, "notfound")


@pytest.mark.asyncio
async def test_resolve_task_id_suffix_multiple_matches():
    """Test resolving a suffix with multiple matches raises error with suggestions."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))
    
    mock_tasks_api.list_tasks = AsyncMock(return_value={
        "items": [
            {"id": "task-abc123", "content": "First task"},
            {"id": "task-def123", "content": "Second task"},
            {"id": "task-ghi456", "content": "Third task"},
        ]
    })
    
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
    
    mock_tasks_api.list_tasks = AsyncMock(return_value={
        "tasks": [
            {"id": "task-abc123def"},
            {"id": "task-ghi456"},
        ]
    })
    
    result = await resolve_task_id(mock_tasks_api, "123def")
    
    assert result == "task-abc123def"


@pytest.mark.asyncio
async def test_resolve_task_id_with_list_response():
    """Test resolving when API returns a list directly."""
    mock_tasks_api = MagicMock()
    mock_tasks_api.get_task = AsyncMock(side_effect=Exception("Not found"))
    
    # API returns a list directly, not wrapped in a dict
    mock_tasks_api.list_tasks = AsyncMock(return_value=[
        {"id": "task-abc123def"},
        {"id": "task-ghi456"},
    ])
    
    result = await resolve_task_id(mock_tasks_api, "123def")
    
    assert result == "task-abc123def"
