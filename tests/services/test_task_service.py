"""Unit tests for TaskService – focused on previously-uncovered lines.

Covered missing lines
---------------------
* 121-124  add_task with a *string* due_date (parsed via fromisoformat)
* 174      update_task with a *string* due_date
* 219-220  reopen_task (builds TaskUpdate(is_completed=False) and calls repo.update)
* 248-249  bulk_complete_tasks (builds TaskUpdate(is_completed=True) and calls repo.bulk_update)
* 254-259  bulk_update_tasks (passes arbitrary kwargs through to repo.bulk_update)
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.models import Task, TaskUpdate
from todopro_cli.services.task_service import TaskService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.get = AsyncMock()
    repo.add = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    repo.complete = AsyncMock()
    repo.bulk_update = AsyncMock(return_value=[])
    return repo


@pytest.fixture()
def service(mock_repo):
    return TaskService(mock_repo)


# ---------------------------------------------------------------------------
# add_task – string due_date branch (lines 121-124)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_task_with_string_due_date_parses_to_datetime(service, mock_repo):
    """add_task must parse an ISO-format string into a datetime before storing."""
    mock_task = MagicMock(spec=Task)
    mock_repo.add.return_value = mock_task

    result = await service.add_task("Buy milk", due_date="2024-12-31")

    assert result is mock_task
    mock_repo.add.assert_awaited_once()
    task_create = mock_repo.add.call_args[0][0]
    assert isinstance(task_create.due_date, datetime)
    assert task_create.due_date == datetime(2024, 12, 31)


@pytest.mark.asyncio
async def test_add_task_with_datetime_due_date_passes_through(service, mock_repo):
    """add_task should also accept a datetime object directly (non-string branch)."""
    dt = datetime(2025, 6, 15, 9, 0, 0)
    mock_repo.add.return_value = MagicMock(spec=Task)

    await service.add_task("Stand-up meeting", due_date=dt)

    task_create = mock_repo.add.call_args[0][0]
    assert task_create.due_date == dt


@pytest.mark.asyncio
async def test_add_task_without_due_date_stores_none(service, mock_repo):
    """add_task with no due_date stores None."""
    mock_repo.add.return_value = MagicMock(spec=Task)

    await service.add_task("No deadline task")

    task_create = mock_repo.add.call_args[0][0]
    assert task_create.due_date is None


# ---------------------------------------------------------------------------
# update_task – string due_date branch (line 174)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_task_with_string_due_date_parses_to_datetime(service, mock_repo):
    """update_task must parse an ISO-format string due_date into a datetime."""
    mock_task = MagicMock(spec=Task)
    mock_repo.update.return_value = mock_task

    result = await service.update_task("task-1", due_date="2025-01-01T10:00:00")

    assert result is mock_task
    mock_repo.update.assert_awaited_once()
    _, task_update = mock_repo.update.call_args[0]
    assert isinstance(task_update.due_date, datetime)
    assert task_update.due_date == datetime(2025, 1, 1, 10, 0, 0)


@pytest.mark.asyncio
async def test_update_task_without_due_date_stores_none(service, mock_repo):
    """update_task with no due_date leaves due_date as None in the update payload."""
    mock_repo.update.return_value = MagicMock(spec=Task)

    await service.update_task("task-1", content="Updated content")

    _, task_update = mock_repo.update.call_args[0]
    assert task_update.due_date is None


# ---------------------------------------------------------------------------
# reopen_task (lines 219-220)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reopen_task_calls_update_with_is_completed_false(service, mock_repo):
    """reopen_task should call repo.update with is_completed=False."""
    mock_task = MagicMock(spec=Task)
    mock_repo.update.return_value = mock_task

    result = await service.reopen_task("task-42")

    assert result is mock_task
    mock_repo.update.assert_awaited_once()
    task_id_arg, task_update_arg = mock_repo.update.call_args[0]
    assert task_id_arg == "task-42"
    assert isinstance(task_update_arg, TaskUpdate)
    assert task_update_arg.is_completed is False


# ---------------------------------------------------------------------------
# bulk_complete_tasks (lines 248-249)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_complete_tasks_returns_updated_list(service, mock_repo):
    """bulk_complete_tasks should pass is_completed=True to repo.bulk_update."""
    task_ids = ["t1", "t2", "t3"]
    mock_tasks = [MagicMock(spec=Task) for _ in task_ids]
    mock_repo.bulk_update.return_value = mock_tasks

    result = await service.bulk_complete_tasks(task_ids)

    assert result == mock_tasks
    mock_repo.bulk_update.assert_awaited_once()
    ids_arg, update_arg = mock_repo.bulk_update.call_args[0]
    assert ids_arg == task_ids
    assert isinstance(update_arg, TaskUpdate)
    assert update_arg.is_completed is True


@pytest.mark.asyncio
async def test_bulk_complete_tasks_with_empty_list(service, mock_repo):
    """bulk_complete_tasks with an empty list should still call repo.bulk_update."""
    mock_repo.bulk_update.return_value = []

    result = await service.bulk_complete_tasks([])

    assert result == []
    mock_repo.bulk_update.assert_awaited_once()


# ---------------------------------------------------------------------------
# bulk_update_tasks (lines 254-259)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_update_tasks_passes_kwargs_as_task_update(service, mock_repo):
    """bulk_update_tasks should forward arbitrary kwargs as a TaskUpdate."""
    task_ids = ["t10", "t11"]
    mock_tasks = [MagicMock(spec=Task) for _ in task_ids]
    mock_repo.bulk_update.return_value = mock_tasks

    result = await service.bulk_update_tasks(task_ids, priority=1, content="Urgent!")

    assert result == mock_tasks
    mock_repo.bulk_update.assert_awaited_once()
    ids_arg, update_arg = mock_repo.bulk_update.call_args[0]
    assert ids_arg == task_ids
    assert isinstance(update_arg, TaskUpdate)
    assert update_arg.priority == 1
    assert update_arg.content == "Urgent!"


@pytest.mark.asyncio
async def test_bulk_update_tasks_with_project_id(service, mock_repo):
    """bulk_update_tasks should support updating project_id."""
    mock_repo.bulk_update.return_value = []

    await service.bulk_update_tasks(["t1"], project_id="proj-99")

    _, update_arg = mock_repo.bulk_update.call_args[0]
    assert update_arg.project_id == "proj-99"


# ---------------------------------------------------------------------------
# Basic CRUD – list_tasks, get_task, delete_task, complete_task (lines 59-70, 81, 197, 208)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tasks_delegates_to_repo(service, mock_repo):
    """list_tasks should build TaskFilters and call repo.list_all."""
    mock_task = MagicMock(spec=Task)
    mock_repo.list_all.return_value = [mock_task]

    result = await service.list_tasks(status="active", priority=2, search="meeting")

    assert result == [mock_task]
    mock_repo.list_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_tasks_no_filters(service, mock_repo):
    """list_tasks with no args should call repo.list_all with empty filters."""
    mock_repo.list_all.return_value = []
    result = await service.list_tasks()
    assert result == []
    mock_repo.list_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_task_delegates_to_repo(service, mock_repo):
    """get_task should delegate to repo.get."""
    mock_task = MagicMock(spec=Task)
    mock_repo.get.return_value = mock_task

    result = await service.get_task("task-99")

    assert result is mock_task
    mock_repo.get.assert_awaited_once_with("task-99")


@pytest.mark.asyncio
async def test_delete_task_delegates_to_repo(service, mock_repo):
    """delete_task should delegate to repo.delete."""
    mock_repo.delete.return_value = True

    result = await service.delete_task("task-del")

    assert result is True
    mock_repo.delete.assert_awaited_once_with("task-del")


@pytest.mark.asyncio
async def test_complete_task_delegates_to_repo(service, mock_repo):
    """complete_task should delegate to repo.complete."""
    mock_task = MagicMock(spec=Task)
    mock_repo.complete.return_value = mock_task

    result = await service.complete_task("task-done")

    assert result is mock_task
    mock_repo.complete.assert_awaited_once_with("task-done")


# ---------------------------------------------------------------------------
# get_task_service factory (lines 254-259)
# ---------------------------------------------------------------------------


def test_get_task_service_factory(mocker):
    """get_task_service should return a TaskService wrapping the repo from context."""
    from todopro_cli.services.task_service import get_task_service

    mock_repo = MagicMock()
    mock_context = MagicMock()
    mock_context.task_repository = mock_repo

    mocker.patch(
        "todopro_cli.services.config_service.get_storage_strategy_context",
        return_value=mock_context,
    )

    service = get_task_service()
    assert isinstance(service, TaskService)
    assert service.repository is mock_repo
