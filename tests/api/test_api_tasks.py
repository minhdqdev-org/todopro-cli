"""Tests for Tasks API."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.services.api.client import APIClient
from todopro_cli.services.api.tasks import TasksAPI


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
        sort="created_at",
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
            "sort": "created_at",
        },
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
        labels=["work", "urgent"],
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
        "eliminate": [],
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
        "is_important": True,
    }
    mock_client.patch.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.classify_task(
        "task-123", is_urgent=True, is_important=True
    )

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
        is_important=True,
    )

    assert result["updated_count"] == 3
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_all_optional_fields(mock_client):
    """Test creating a task with all optional fields populated."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-999"}
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.create_task(
        "Full task",
        description="A detailed description",
        project_id="proj-123",
        due_date="2024-12-31",
        labels=["l1"],
        is_recurring=True,
        recurrence_rule="FREQ=DAILY",
        recurrence_end="2025-01-01",
        parent_id="parent-1",
    )

    assert result["id"] == "task-999"
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs[1]["json"]
    assert payload["content"] == "Full task"
    assert payload["description"] == "A detailed description"
    assert payload["project_id"] == "proj-123"
    assert payload["due_date"] == "2024-12-31"
    assert payload["labels"] == ["l1"]
    assert payload["is_recurring"] is True
    assert payload["recurrence_rule"] == "FREQ=DAILY"
    assert payload["recurrence_end"] == "2025-01-01"
    assert payload["parent_id"] == "parent-1"


@pytest.mark.asyncio
async def test_list_subtasks(mock_client):
    """Test listing subtasks by parent_id."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"tasks": [{"id": "sub-1", "parent_id": "p-1"}]}
    mock_client.get.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.list_subtasks("p-1")

    assert result["tasks"][0]["parent_id"] == "p-1"
    mock_client.get.assert_called_once_with("/v1/tasks", params={"parent_id": "p-1"})


@pytest.mark.asyncio
async def test_list_dependencies(mock_client):
    """Test listing dependencies of a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "dep-1", "depends_on_id": "task-2"}]
    mock_client.get.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.list_dependencies("task-1")

    assert len(result) == 1
    assert result[0]["depends_on_id"] == "task-2"
    mock_client.get.assert_called_once_with("/v1/tasks/task-1/dependencies")


@pytest.mark.asyncio
async def test_add_dependency(mock_client):
    """Test adding a dependency between two tasks."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "dep-1",
        "depends_on_id": "task-2",
        "dependency_type": "blocks",
    }
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.add_dependency("task-1", "task-2", "blocks")

    assert result["dependency_type"] == "blocks"
    mock_client.post.assert_called_once_with(
        "/v1/tasks/task-1/dependencies",
        json={"depends_on_id": "task-2", "dependency_type": "blocks"},
    )


@pytest.mark.asyncio
async def test_remove_dependency(mock_client):
    """Test removing a dependency from a task."""
    mock_client.delete.return_value = MagicMock(status_code=204)

    tasks_api = TasksAPI(mock_client)
    await tasks_api.remove_dependency("task-1", "dep-1")

    mock_client.delete.assert_called_once_with("/v1/tasks/task-1/dependencies/dep-1")


@pytest.mark.asyncio
async def test_skip_task(mock_client):
    """Test skipping the current occurrence of a recurring task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-1", "skipped": True}
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.skip_task("task-1")

    assert result["skipped"] is True
    mock_client.post.assert_called_once_with("/v1/tasks/task-1/skip")


@pytest.mark.asyncio
async def test_get_reminders(mock_client):
    """Test getting all reminders for a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "reminders": [{"id": "r1", "reminder_date": "2024-12-30T09:00:00"}]
    }
    mock_client.get.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.get_reminders("task-1")

    assert result["reminders"][0]["id"] == "r1"
    mock_client.get.assert_called_once_with("/v1/tasks/task-1/reminders")


@pytest.mark.asyncio
async def test_set_reminder(mock_client):
    """Test setting a reminder for a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "r1",
        "task_id": "task-1",
        "reminder_date": "2024-12-30T09:00:00",
    }
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.set_reminder("task-1", "2024-12-30T09:00:00")

    assert result["reminder_date"] == "2024-12-30T09:00:00"
    mock_client.post.assert_called_once_with(
        "/v1/tasks/task-1/reminders",
        json={"reminder_date": "2024-12-30T09:00:00"},
    )


@pytest.mark.asyncio
async def test_reschedule_task(mock_client):
    """Test rescheduling a task to a new due date."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "task-1", "due_date": "2025-01-15"}
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.reschedule_task("task-1", "2025-01-15")

    assert result["due_date"] == "2025-01-15"
    mock_client.post.assert_called_once_with(
        "/v1/tasks/task-1/reschedule",
        json={"due_date": "2025-01-15"},
    )


@pytest.mark.asyncio
async def test_batch_complete_tasks(mock_client):
    """Test marking multiple tasks as completed in one call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"completed_count": 3}
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.batch_complete_tasks(["task-1", "task-2", "task-3"])

    assert result["completed_count"] == 3
    mock_client.post.assert_called_once_with(
        "/v1/tasks/batch/complete",
        json={"task_ids": ["task-1", "task-2", "task-3"]},
    )


@pytest.mark.asyncio
async def test_bulk_classify_task_ids_only(mock_client):
    """Test bulk_classify with only task_ids (no optional quadrant/urgency params)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"updated_count": 2}
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.bulk_classify(["task-1", "task-2"])

    assert result["updated_count"] == 2
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs[1]["json"]
    # Only task_ids should be present when no optional args are given
    assert payload == {"task_ids": ["task-1", "task-2"]}
    assert "quadrant" not in payload
    assert "is_urgent" not in payload
    assert "is_important" not in payload


@pytest.mark.asyncio
async def test_quick_add_exception_with_response(mock_client):
    """Test quick_add returns parsed error response when exception has .response."""
    error_body = {"detail": "Parse failed", "suggestions": []}

    mock_error_response = MagicMock()
    mock_error_response.json.return_value = error_body

    exc = Exception("Unprocessable entity")
    exc.response = mock_error_response

    mock_client.post.side_effect = exc

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.quick_add("garbage input ???")

    assert result == error_body
    mock_error_response.json.assert_called_once()


@pytest.mark.asyncio
async def test_quick_add_exception_without_response_reraises(mock_client):
    """Test quick_add re-raises when exception has no .response attribute."""
    exc = Exception("Network error")
    # No .response attribute on this exception
    mock_client.post.side_effect = exc

    tasks_api = TasksAPI(mock_client)
    with pytest.raises(Exception, match="Network error"):
        await tasks_api.quick_add("some text")


@pytest.mark.asyncio
async def test_quick_add_response_json_raises_reraises_original(mock_client):
    """Test quick_add swallows inner json parse error and re-raises original exception."""
    mock_error_response = MagicMock()
    mock_error_response.json.side_effect = ValueError("not json")

    exc = Exception("API error")
    exc.response = mock_error_response

    mock_client.post.side_effect = exc

    tasks_api = TasksAPI(mock_client)
    with pytest.raises(Exception, match="API error"):
        await tasks_api.quick_add("some input")


@pytest.mark.asyncio
async def test_delete_reminder(mock_client):
    """Test deleting a reminder from a task."""
    mock_client.delete.return_value = MagicMock()

    tasks_api = TasksAPI(mock_client)
    await tasks_api.delete_reminder("task-123", "reminder-456")

    mock_client.delete.assert_called_once_with(
        "/v1/tasks/task-123/reminders/reminder-456"
    )


@pytest.mark.asyncio
async def test_snooze_reminder(mock_client):
    """Test snoozing a reminder for a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "reminder-456", "snoozed_until": "2024-12-31T10:00:00"}
    mock_client.post.return_value = mock_response

    tasks_api = TasksAPI(mock_client)
    result = await tasks_api.snooze_reminder("task-123", "reminder-456", 30)

    assert result["id"] == "reminder-456"
    mock_client.post.assert_called_once_with(
        "/v1/tasks/task-123/reminders/reminder-456/snooze",
        json={"duration_minutes": 30},
    )
