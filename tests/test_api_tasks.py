"""Tests for Tasks API."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from todopro_cli.api.tasks import TasksAPI
from todopro_cli.api.client import APIClient


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock(spec=APIClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_list_tasks_no_filters(mock_client):
    """Test listing tasks without filters."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"tasks": []}
    mock_client.get.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.list_tasks()
    
    assert result == {"tasks": []}
    mock_client.get.assert_called_once_with("/v1/tasks", params={})


@pytest.mark.asyncio
async def test_list_tasks_with_filters(mock_client):
    """Test listing tasks with filters."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"tasks": []}
    mock_client.get.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.list_tasks(
        status="open",
        project_id="proj-123",
        priority=2,
        search="test",
        limit=10,
        offset=0,
        sort="created_at"
    )
    
    mock_client.get.assert_called_once_with(
        "/v1/tasks",
        params={
            "status": "open",
            "project_id": "proj-123",
            "priority": 2,
            "search": "test",
            "limit": 10,
            "offset": 0,
            "sort": "created_at"
        }
    )


@pytest.mark.asyncio
async def test_get_task(mock_client):
    """Test getting a specific task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123", "content": "Test task"}
    mock_client.get.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.get_task("task-123")
    
    assert result["id"] == "task-123"
    mock_client.get.assert_called_once_with("/v1/tasks/task-123")


@pytest.mark.asyncio
async def test_create_task_minimal(mock_client):
    """Test creating a task with minimal data."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123", "content": "New task"}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.create_task("New task")
    
    assert result["id"] == "task-123"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_full(mock_client):
    """Test creating a task with all fields."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123"}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.create_task(
        "New task",
        description="Task description",
        project_id="proj-123",
        due_date="2024-12-31",
        priority=2,
        labels=["work", "urgent"]
    )
    
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_update_task(mock_client):
    """Test updating a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123", "content": "Updated task"}
    mock_client.patch.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.update_task("task-123", content="Updated task")
    
    assert result["content"] == "Updated task"
    mock_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_delete_task(mock_client):
    """Test deleting a task."""
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_client.delete.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    await tasks_api.delete_task("task-123")
    
    mock_client.delete.assert_called_once_with("/v1/tasks/task-123")


@pytest.mark.asyncio
async def test_complete_task(mock_client):
    """Test completing a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123", "is_completed": True}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.complete_task("task-123")
    
    assert result["is_completed"] is True
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_reopen_task(mock_client):
    """Test reopening a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123", "is_completed": False}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.reopen_task("task-123")
    
    assert result["is_completed"] is False
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_get_task_comments(mock_client):
    """Test getting task comments."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"comments": []}
    mock_client.get.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.get_task_comments("task-123")
    
    assert "comments" in result
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_add_comment(mock_client):
    """Test adding a comment to a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "comment-123", "text": "Test comment"}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.add_comment("task-123", "Test comment")
    
    assert result["text"] == "Test comment"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_today_tasks(mock_client):
    """Test getting today's tasks."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"tasks": []}
    mock_client.get.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.today_tasks()
    
    assert "tasks" in result
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_next_task(mock_client):
    """Test getting next task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123", "content": "Next task"}
    mock_client.get.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.next_task()
    
    assert result["id"] == "task-123"
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_reschedule_overdue(mock_client):
    """Test rescheduling overdue tasks."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"rescheduled_count": 5}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.reschedule_overdue()
    
    assert result["rescheduled_count"] == 5
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_quick_add(mock_client):
    """Test quick add using natural language."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-123", "content": "Buy milk"}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.quick_add("Buy milk tomorrow at 5pm")
    
    assert result["content"] == "Buy milk"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_eisenhower_matrix(mock_client):
    """Test getting Eisenhower Matrix view."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "do_first": [],
        "schedule": [],
        "delegate": [],
        "eliminate": []
    }
    mock_client.get.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.eisenhower_matrix()
    
    assert "do_first" in result
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_classify_task(mock_client):
    """Test classifying a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "task-123",
        "is_urgent": True,
        "is_important": True
    }
    mock_client.patch.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.classify_task("task-123", is_urgent=True, is_important=True)
    
    assert result["is_urgent"] is True
    mock_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_classify(mock_client):
    """Test bulk classifying tasks."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"updated_count": 3}
    mock_client.post.return_value = mock_response
    
    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.bulk_classify(
        ["task-1", "task-2", "task-3"],
        quadrant="do_first",
        is_urgent=True,
        is_important=True
    )
    
    assert result["updated_count"] == 3
    mock_client.post.assert_called_once()
