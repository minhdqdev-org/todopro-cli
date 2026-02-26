"""Comprehensive unit tests for REST API adapter implementations.

All API calls are mocked via AsyncMock so no real HTTP traffic is made.
Tests cover the four adapter classes:
  - RestApiTaskRepository
  - RestApiProjectRepository
  - RestApiLabelRepository
  - RestApiLocationContextRepository
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.adapters.rest_api import (
    RestApiLabelRepository,
    RestApiLocationContextRepository,
    RestApiProjectRepository,
    RestApiTaskRepository,
)
from todopro_cli.models import (
    Label,
    LabelCreate,
    LocationContext,
    LocationContextCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
)


# ---------------------------------------------------------------------------
# Shared test data factories
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 15, 9, 0, 0)


def _task_dict(**kwargs) -> dict:
    base = {
        "id": "task-001",
        "content": "Test task",
        "description": None,
        "project_id": None,
        "due_date": None,
        "priority": 4,
        "is_completed": False,
        "is_recurring": False,
        "recurrence_rule": None,
        "recurrence_end": None,
        "labels": [],
        "contexts": [],
        "created_at": _NOW.isoformat(),
        "updated_at": _NOW.isoformat(),
        "completed_at": None,
        "version": 1,
    }
    base.update(kwargs)
    return base


def _project_dict(**kwargs) -> dict:
    base = {
        "id": "proj-001",
        "name": "Test Project",
        "color": None,
        "is_favorite": False,
        "is_archived": False,
        "workspace_id": None,
        "created_at": _NOW.isoformat(),
        "updated_at": _NOW.isoformat(),
    }
    base.update(kwargs)
    return base


def _label_dict(**kwargs) -> dict:
    base = {"id": "lbl-001", "name": "work", "color": None}
    base.update(kwargs)
    return base


def _context_dict(**kwargs) -> dict:
    base = {
        "id": "ctx-001",
        "name": "@office",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 100.0,
    }
    base.update(kwargs)
    return base


def _disabled_e2ee():
    e2ee = MagicMock()
    e2ee.enabled = False
    e2ee.prepare_task_for_storage.side_effect = lambda c, d: (c, None, d, None)
    e2ee.extract_task_content.side_effect = lambda c, ce, d, de: (c, d)
    return e2ee


def _enabled_e2ee():
    e2ee = MagicMock()
    e2ee.enabled = True
    e2ee.prepare_task_for_storage.side_effect = lambda c, d: ("", f"enc({c})", "", f"enc({d or ''})")
    e2ee.extract_task_content.side_effect = lambda c, ce, d, de: ("decrypted content", "decrypted desc")
    return e2ee


# ---------------------------------------------------------------------------
# RestApiTaskRepository
# ---------------------------------------------------------------------------


class TestRestApiTaskRepositoryListAll:
    """Tests for RestApiTaskRepository.list_all."""

    def _make_repo(self, tasks_result, e2ee=None):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.list_tasks = AsyncMock(return_value={"tasks": tasks_result})
        repo._tasks_api = mock_api
        repo._e2ee_handler = e2ee or _disabled_e2ee()
        return repo

    @pytest.mark.asyncio
    async def test_list_all_returns_task_objects(self):
        repo = self._make_repo([_task_dict()])
        tasks = await repo.list_all(TaskFilters())
        assert len(tasks) == 1
        assert isinstance(tasks[0], Task)

    @pytest.mark.asyncio
    async def test_list_all_empty(self):
        repo = self._make_repo([])
        tasks = await repo.list_all(TaskFilters())
        assert tasks == []

    @pytest.mark.asyncio
    async def test_list_all_passes_filters(self):
        repo = self._make_repo([_task_dict()])
        filters = TaskFilters(status="active", project_id="proj-1", priority=1, search="foo", limit=5, offset=0, sort="priority:asc")
        await repo.list_all(filters)
        repo._tasks_api.list_tasks.assert_awaited_once()
        call_kwargs = repo._tasks_api.list_tasks.call_args.kwargs
        assert call_kwargs["status"] == "active"
        assert call_kwargs["project_id"] == "proj-1"
        assert call_kwargs["priority"] == 1
        assert call_kwargs["search"] == "foo"
        assert call_kwargs["limit"] == 5
        assert call_kwargs["sort"] == "priority:asc"

    @pytest.mark.asyncio
    async def test_list_all_handles_list_response(self):
        """API may return a list directly instead of a dict."""
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.list_tasks = AsyncMock(return_value=[_task_dict()])
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        tasks = await repo.list_all(TaskFilters())
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_list_all_with_e2ee_decrypts(self):
        task_data = _task_dict(content_encrypted="enc(hello)")
        repo = self._make_repo([task_data], e2ee=_enabled_e2ee())
        tasks = await repo.list_all(TaskFilters())
        assert tasks[0].content == "decrypted content"


class TestRestApiTaskRepositoryGet:
    @pytest.mark.asyncio
    async def test_get_returns_task(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.get_task = AsyncMock(return_value=_task_dict())
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        task = await repo.get("task-001")
        assert isinstance(task, Task)
        assert task.id == "task-001"

    @pytest.mark.asyncio
    async def test_get_with_e2ee_decrypts(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.get_task = AsyncMock(return_value=_task_dict(content_encrypted="enc(x)"))
        repo._tasks_api = mock_api
        repo._e2ee_handler = _enabled_e2ee()
        task = await repo.get("task-001")
        assert task.content == "decrypted content"


class TestRestApiTaskRepositoryAdd:
    @pytest.mark.asyncio
    async def test_add_creates_task(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.create_task = AsyncMock(return_value=_task_dict(content="New task"))
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        task = await repo.add(TaskCreate(content="New task"))
        assert task.content == "New task"

    @pytest.mark.asyncio
    async def test_add_with_e2ee_encrypts_and_decrypts(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        result = _task_dict(content_encrypted="enc(secret)")
        mock_api.create_task = AsyncMock(return_value=result)
        repo._tasks_api = mock_api
        repo._e2ee_handler = _enabled_e2ee()
        task = await repo.add(TaskCreate(content="secret"))
        assert task.content == "decrypted content"

    @pytest.mark.asyncio
    async def test_add_converts_datetime_due_date(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.create_task = AsyncMock(return_value=_task_dict())
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        task_create = TaskCreate(content="Dated task", due_date=datetime(2024, 12, 31))
        await repo.add(task_create)
        call_kwargs = mock_api.create_task.call_args.kwargs
        # due_date should be ISO string
        assert isinstance(call_kwargs.get("due_date"), str)


class TestRestApiTaskRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_task(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.update_task = AsyncMock(return_value=_task_dict(content="Updated"))
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        task = await repo.update("task-001", TaskUpdate(content="Updated"))
        assert task.content == "Updated"

    @pytest.mark.asyncio
    async def test_update_with_e2ee(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.update_task = AsyncMock(return_value=_task_dict(content_encrypted="enc(x)"))
        repo._tasks_api = mock_api
        repo._e2ee_handler = _enabled_e2ee()
        task = await repo.update("task-001", TaskUpdate(content="secret"))
        assert task.content == "decrypted content"


class TestRestApiTaskRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_true(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.delete_task = AsyncMock(return_value=None)
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        result = await repo.delete("task-001")
        assert result is True


class TestRestApiTaskRepositoryComplete:
    @pytest.mark.asyncio
    async def test_complete_marks_task(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.complete_task = AsyncMock(return_value=_task_dict(is_completed=True))
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        task = await repo.complete("task-001")
        assert task.is_completed is True

    @pytest.mark.asyncio
    async def test_complete_with_e2ee_decrypts(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.complete_task = AsyncMock(return_value=_task_dict(content_encrypted="enc(x)"))
        repo._tasks_api = mock_api
        repo._e2ee_handler = _enabled_e2ee()
        task = await repo.complete("task-001")
        assert task.content == "decrypted content"


class TestRestApiTaskRepositoryBulkUpdate:
    @pytest.mark.asyncio
    async def test_bulk_update_via_batch_complete(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        t1 = _task_dict(id="t1", is_completed=True)
        t2 = _task_dict(id="t2", is_completed=True)
        mock_api.batch_complete_tasks = AsyncMock(return_value={"tasks": [t1, t2]})
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        tasks = await repo.bulk_update(["t1", "t2"], TaskUpdate(is_completed=True))
        assert len(tasks) == 2
        assert all(t.is_completed for t in tasks)

    @pytest.mark.asyncio
    async def test_bulk_update_one_by_one(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.update_task = AsyncMock(return_value=_task_dict(priority=1))
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        tasks = await repo.bulk_update(["t1", "t2"], TaskUpdate(priority=1))
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_bulk_update_empty_list(self):
        repo = RestApiTaskRepository()
        mock_api = MagicMock()
        mock_api.update_task = AsyncMock(return_value=_task_dict())
        repo._tasks_api = mock_api
        repo._e2ee_handler = _disabled_e2ee()
        tasks = await repo.bulk_update([], TaskUpdate(priority=1))
        assert tasks == []


class TestRestApiTaskRepositoryE2EEHelpers:
    """Test _encrypt_task_fields and _decrypt_task_fields directly."""

    def test_encrypt_disabled_returns_unchanged(self):
        repo = RestApiTaskRepository()
        repo._e2ee_handler = _disabled_e2ee()
        data = {"content": "hello", "description": "world"}
        result = repo._encrypt_task_fields(data)
        assert result["content"] == "hello"

    def test_encrypt_enabled_sets_encrypted_field(self):
        repo = RestApiTaskRepository()
        repo._e2ee_handler = _enabled_e2ee()
        data = {"content": "secret", "description": "details"}
        result = repo._encrypt_task_fields(data)
        assert "content_encrypted" in result

    def test_decrypt_disabled_returns_unchanged(self):
        repo = RestApiTaskRepository()
        repo._e2ee_handler = _disabled_e2ee()
        data = {"content": "hello"}
        result = repo._decrypt_task_fields(data)
        assert result["content"] == "hello"

    def test_decrypt_enabled_decrypts(self):
        repo = RestApiTaskRepository()
        repo._e2ee_handler = _enabled_e2ee()
        data = {"content": "", "content_encrypted": "enc(hello)"}
        result = repo._decrypt_task_fields(data)
        assert result["content"] == "decrypted content"

    def test_decrypt_no_encrypted_field_unchanged(self):
        repo = RestApiTaskRepository()
        repo._e2ee_handler = _enabled_e2ee()
        data = {"content": "plain text"}
        # No content_encrypted key → should not decrypt
        result = repo._decrypt_task_fields(data)
        assert result["content"] == "plain text"


class TestRestApiTaskRepositoryLazyInit:
    """Test lazy initialization of API instances."""

    def test_tasks_api_lazy_init(self):
        repo = RestApiTaskRepository()
        assert repo._tasks_api is None
        with patch("todopro_cli.adapters.rest_api.APIClient") as MockClient:
            with patch("todopro_cli.adapters.rest_api.TasksAPI") as MockTasksAPI:
                _ = repo.tasks_api
                MockClient.assert_called_once()
                MockTasksAPI.assert_called_once()

    def test_e2ee_lazy_init(self):
        repo = RestApiTaskRepository()
        assert repo._e2ee_handler is None
        with patch("todopro_cli.adapters.sqlite.e2ee.get_e2ee_handler") as mock_get:
            mock_get.return_value = _disabled_e2ee()
            _ = repo.e2ee
            mock_get.assert_called_once()


# ---------------------------------------------------------------------------
# RestApiProjectRepository
# ---------------------------------------------------------------------------


class TestRestApiProjectRepository:
    def _make_repo(self, projects_api_mock=None):
        repo = RestApiProjectRepository()
        if projects_api_mock is not None:
            repo._projects_api = projects_api_mock
        return repo

    @pytest.mark.asyncio
    async def test_list_all_returns_projects(self):
        mock_api = MagicMock()
        mock_api.list_projects = AsyncMock(return_value={"projects": [_project_dict()]})
        repo = self._make_repo(mock_api)
        projects = await repo.list_all(ProjectFilters())
        assert len(projects) == 1
        assert isinstance(projects[0], Project)

    @pytest.mark.asyncio
    async def test_list_all_handles_list_response(self):
        mock_api = MagicMock()
        mock_api.list_projects = AsyncMock(return_value=[_project_dict()])
        repo = self._make_repo(mock_api)
        projects = await repo.list_all(ProjectFilters())
        assert len(projects) == 1

    @pytest.mark.asyncio
    async def test_list_all_filter_favorite(self):
        mock_api = MagicMock()
        mock_api.list_projects = AsyncMock(return_value={"projects": [
            _project_dict(id="p1", is_favorite=True),
            _project_dict(id="p2", is_favorite=False),
        ]})
        repo = self._make_repo(mock_api)
        projects = await repo.list_all(ProjectFilters(is_favorite=True))
        assert all(p.is_favorite for p in projects)

    @pytest.mark.asyncio
    async def test_list_all_filter_archived(self):
        mock_api = MagicMock()
        mock_api.list_projects = AsyncMock(return_value={"projects": [
            _project_dict(id="p1", is_archived=True),
            _project_dict(id="p2", is_archived=False),
        ]})
        repo = self._make_repo(mock_api)
        projects = await repo.list_all(ProjectFilters(is_archived=True))
        assert all(p.is_archived for p in projects)

    @pytest.mark.asyncio
    async def test_list_all_filter_search(self):
        mock_api = MagicMock()
        mock_api.list_projects = AsyncMock(return_value={"projects": [
            _project_dict(id="p1", name="Groceries"),
            _project_dict(id="p2", name="Work"),
        ]})
        repo = self._make_repo(mock_api)
        projects = await repo.list_all(ProjectFilters(search="groc"))
        assert len(projects) == 1
        assert projects[0].name == "Groceries"

    @pytest.mark.asyncio
    async def test_list_all_filter_workspace(self):
        mock_api = MagicMock()
        mock_api.list_projects = AsyncMock(return_value={"projects": [
            _project_dict(id="p1", workspace_id="ws-1"),
            _project_dict(id="p2", workspace_id=None),
        ]})
        repo = self._make_repo(mock_api)
        projects = await repo.list_all(ProjectFilters(workspace_id="ws-1"))
        assert all(p.workspace_id == "ws-1" for p in projects)

    @pytest.mark.asyncio
    async def test_get_returns_project(self):
        mock_api = MagicMock()
        mock_api.get_project = AsyncMock(return_value=_project_dict())
        repo = self._make_repo(mock_api)
        proj = await repo.get("proj-001")
        assert isinstance(proj, Project)

    @pytest.mark.asyncio
    async def test_create_returns_project(self):
        mock_api = MagicMock()
        mock_api.create_project = AsyncMock(return_value=_project_dict(name="New"))
        repo = self._make_repo(mock_api)
        proj = await repo.create(ProjectCreate(name="New"))
        assert proj.name == "New"

    @pytest.mark.asyncio
    async def test_update_returns_project(self):
        mock_api = MagicMock()
        mock_api.update_project = AsyncMock(return_value=_project_dict(name="Updated"))
        repo = self._make_repo(mock_api)
        proj = await repo.update("proj-001", ProjectUpdate(name="Updated"))
        assert proj.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_returns_true(self):
        mock_api = MagicMock()
        mock_api.delete_project = AsyncMock(return_value=None)
        repo = self._make_repo(mock_api)
        result = await repo.delete("proj-001")
        assert result is True

    @pytest.mark.asyncio
    async def test_archive_returns_project(self):
        mock_api = MagicMock()
        mock_api.archive_project = AsyncMock(return_value=_project_dict(is_archived=True))
        repo = self._make_repo(mock_api)
        proj = await repo.archive("proj-001")
        assert proj.is_archived is True

    @pytest.mark.asyncio
    async def test_unarchive_returns_project(self):
        mock_api = MagicMock()
        mock_api.unarchive_project = AsyncMock(return_value=_project_dict(is_archived=False))
        repo = self._make_repo(mock_api)
        proj = await repo.unarchive("proj-001")
        assert proj.is_archived is False

    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self):
        mock_api = MagicMock()
        mock_api.get_project_stats = AsyncMock(return_value={"total_tasks": 5})
        repo = self._make_repo(mock_api)
        stats = await repo.get_stats("proj-001")
        assert stats["total_tasks"] == 5

    def test_projects_api_lazy_init(self):
        repo = RestApiProjectRepository()
        assert repo._projects_api is None
        with patch("todopro_cli.adapters.rest_api.APIClient") as MockClient:
            with patch("todopro_cli.adapters.rest_api.ProjectsAPI") as MockProjectsAPI:
                _ = repo.projects_api
                MockClient.assert_called_once()
                MockProjectsAPI.assert_called_once()


# ---------------------------------------------------------------------------
# RestApiLabelRepository
# ---------------------------------------------------------------------------


class TestRestApiLabelRepository:
    def _make_repo(self, labels_api_mock=None):
        repo = RestApiLabelRepository()
        if labels_api_mock is not None:
            repo._labels_api = labels_api_mock
        return repo

    @pytest.mark.asyncio
    async def test_list_all_returns_labels(self):
        mock_api = MagicMock()
        mock_api.list_labels = AsyncMock(return_value={"labels": [_label_dict()]})
        repo = self._make_repo(mock_api)
        labels = await repo.list_all()
        assert len(labels) == 1
        assert isinstance(labels[0], Label)

    @pytest.mark.asyncio
    async def test_list_all_handles_list_response(self):
        mock_api = MagicMock()
        mock_api.list_labels = AsyncMock(return_value=[_label_dict()])
        repo = self._make_repo(mock_api)
        labels = await repo.list_all()
        assert len(labels) == 1

    @pytest.mark.asyncio
    async def test_get_returns_label(self):
        mock_api = MagicMock()
        mock_api.get_label = AsyncMock(return_value=_label_dict())
        repo = self._make_repo(mock_api)
        label = await repo.get("lbl-001")
        assert isinstance(label, Label)

    @pytest.mark.asyncio
    async def test_create_returns_label(self):
        mock_api = MagicMock()
        mock_api.create_label = AsyncMock(return_value=_label_dict(name="home"))
        repo = self._make_repo(mock_api)
        label = await repo.create(LabelCreate(name="home"))
        assert label.name == "home"

    @pytest.mark.asyncio
    async def test_delete_returns_true(self):
        mock_api = MagicMock()
        mock_api.delete_label = AsyncMock(return_value=None)
        repo = self._make_repo(mock_api)
        result = await repo.delete("lbl-001")
        assert result is True

    @pytest.mark.asyncio
    async def test_search_by_prefix(self):
        mock_api = MagicMock()
        mock_api.list_labels = AsyncMock(return_value={"labels": [
            _label_dict(id="l1", name="work"),
            _label_dict(id="l2", name="workout"),
            _label_dict(id="l3", name="home"),
        ]})
        repo = self._make_repo(mock_api)
        results = await repo.search("work")
        assert len(results) == 2
        assert all(lbl.name.startswith("work") for lbl in results)

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        mock_api = MagicMock()
        mock_api.list_labels = AsyncMock(return_value={"labels": [
            _label_dict(id="l1", name="Work"),
        ]})
        repo = self._make_repo(mock_api)
        results = await repo.search("work")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_no_match(self):
        mock_api = MagicMock()
        mock_api.list_labels = AsyncMock(return_value={"labels": [_label_dict(name="home")]})
        repo = self._make_repo(mock_api)
        results = await repo.search("xyz")
        assert results == []

    def test_labels_api_lazy_init(self):
        repo = RestApiLabelRepository()
        assert repo._labels_api is None
        with patch("todopro_cli.adapters.rest_api.APIClient") as MockClient:
            with patch("todopro_cli.adapters.rest_api.LabelsAPI") as MockLabelsAPI:
                _ = repo.labels_api
                MockClient.assert_called_once()
                MockLabelsAPI.assert_called_once()


# ---------------------------------------------------------------------------
# RestApiLocationContextRepository
# ---------------------------------------------------------------------------


class TestRestApiLocationContextRepository:
    def _make_repo(self, client_mock=None):
        repo = RestApiLocationContextRepository()
        if client_mock is not None:
            repo._client = client_mock
        return repo

    @pytest.mark.asyncio
    async def test_list_all_returns_contexts(self):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=[_context_dict()])
        repo = self._make_repo(mock_client)
        contexts = await repo.list_all()
        assert len(contexts) == 1
        assert isinstance(contexts[0], LocationContext)

    @pytest.mark.asyncio
    async def test_list_all_returns_empty_on_error(self):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))
        repo = self._make_repo(mock_client)
        contexts = await repo.list_all()
        assert contexts == []

    @pytest.mark.asyncio
    async def test_get_returns_context(self):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=_context_dict())
        repo = self._make_repo(mock_client)
        ctx = await repo.get("ctx-001")
        assert isinstance(ctx, LocationContext)
        assert ctx.id == "ctx-001"

    @pytest.mark.asyncio
    async def test_get_raises_on_error(self):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("not found"))
        repo = self._make_repo(mock_client)
        with pytest.raises(ValueError, match="not found"):
            await repo.get("ctx-001")

    @pytest.mark.asyncio
    async def test_create_returns_context(self):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_context_dict(name="@home"))
        repo = self._make_repo(mock_client)
        ctx = await repo.create(LocationContextCreate(name="@home", latitude=37.7, longitude=-122.4, radius=100.0))
        assert ctx.name == "@home"

    @pytest.mark.asyncio
    async def test_create_raises_on_error(self):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("server error"))
        repo = self._make_repo(mock_client)
        with pytest.raises(ValueError, match="Failed to create"):
            await repo.create(LocationContextCreate(name="@fail", latitude=0, longitude=0, radius=50.0))

    @pytest.mark.asyncio
    async def test_delete_returns_true(self):
        mock_client = MagicMock()
        mock_client.delete = AsyncMock(return_value=None)
        repo = self._make_repo(mock_client)
        result = await repo.delete("ctx-001")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(self):
        mock_client = MagicMock()
        mock_client.delete = AsyncMock(side_effect=Exception("error"))
        repo = self._make_repo(mock_client)
        result = await repo.delete("ctx-001")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_available_returns_contexts(self):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value={
            "available": [_context_dict()],
            "unavailable": [],
        })
        repo = self._make_repo(mock_client)
        contexts = await repo.get_available(37.7749, -122.4194)
        assert len(contexts) == 1
        assert isinstance(contexts[0], LocationContext)

    @pytest.mark.asyncio
    async def test_get_available_returns_empty_on_error(self):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("error"))
        repo = self._make_repo(mock_client)
        contexts = await repo.get_available(0.0, 0.0)
        assert contexts == []

    @pytest.mark.asyncio
    async def test_get_available_empty_available(self):
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value={"available": [], "unavailable": []})
        repo = self._make_repo(mock_client)
        contexts = await repo.get_available(37.7749, -122.4194)
        assert contexts == []

    def test_client_lazy_init(self):
        repo = RestApiLocationContextRepository()
        assert repo._client is None
        with patch("todopro_cli.adapters.rest_api.APIClient") as MockClient:
            _ = repo.client
            MockClient.assert_called_once()
