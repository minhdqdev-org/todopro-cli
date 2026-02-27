"""Unit tests for TodoistImportService.

The Todoist client and all TodoPro repositories are replaced with mocks
so these tests are pure unit tests — no network, no filesystem.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.services.todoist.importer import TodoistImportService
from todopro_cli.services.todoist.models import (
    TodoistDue,
    TodoistImportOptions,
    TodoistLabel,
    TodoistProject,
    TodoistTask,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(
    projects: list = None,
    tasks: list = None,
    labels: list = None,
) -> MagicMock:
    """Create a mock TodoistClientProtocol."""
    client = MagicMock()
    client.get_projects = AsyncMock(return_value=projects or [])
    client.get_tasks = AsyncMock(return_value=tasks or [])
    client.get_labels = AsyncMock(return_value=labels or [])
    return client


def _make_storage(
    *,
    existing_projects: list = None,
    existing_labels: list = None,
    existing_tasks: list = None,
) -> MagicMock:
    """Create a mock storage strategy context."""
    storage = MagicMock()

    # Project repository
    proj_repo = MagicMock()
    proj_repo.list_all = AsyncMock(return_value=existing_projects or [])
    proj_repo.create = AsyncMock(side_effect=lambda data: MagicMock(id="new-proj-id", name=data.name))
    storage.project_repository = proj_repo

    # Label repository
    lbl_repo = MagicMock()
    lbl_repo.list_all = AsyncMock(return_value=existing_labels or [])
    lbl_repo.create = AsyncMock(side_effect=lambda data: MagicMock(id="new-lbl-id", name=data.name))
    storage.label_repository = lbl_repo

    # Task repository
    task_repo = MagicMock()
    task_repo.list_all = AsyncMock(return_value=existing_tasks or [])
    task_repo.add = AsyncMock(return_value=MagicMock(id="new-task-id"))
    storage.task_repository = task_repo

    return storage


def _default_options(**overrides) -> TodoistImportOptions:
    return TodoistImportOptions(**{"project_name_prefix": "[Todoist]", **overrides})


def _project(pid="p1", name="Inbox") -> TodoistProject:
    return TodoistProject(id=pid, name=name)


def _task(tid="t1", content="Buy milk", project_id="p1") -> TodoistTask:
    return TodoistTask(id=tid, content=content, project_id=project_id)


def _label(name="@home", color="blue") -> TodoistLabel:
    return TodoistLabel(id=1, name=name, color=color)


# ---------------------------------------------------------------------------
# import_all — happy path
# ---------------------------------------------------------------------------


class TestImportAll:
    @pytest.mark.asyncio
    async def test_returns_import_result(self):
        client = _make_client(
            projects=[_project()],
            tasks=[_task()],
            labels=[_label()],
        )
        # Task list_all returns empty (no duplicates)
        storage = _make_storage()
        service = TodoistImportService(client, storage)
        result = await service.import_all(_default_options())

        assert result.projects_created == 1
        assert result.labels_created == 1
        assert result.tasks_created == 1
        assert result.projects_skipped == 0
        assert result.tasks_skipped == 0
        assert not result.has_errors

    @pytest.mark.asyncio
    async def test_fetches_tasks_for_each_project(self):
        projects = [_project("p1", "Inbox"), _project("p2", "Work")]
        client = _make_client(projects=projects, tasks=[_task(project_id="p1")])
        storage = _make_storage()
        service = TodoistImportService(client, storage)

        await service.import_all(_default_options())

        assert client.get_tasks.call_count == 2

    @pytest.mark.asyncio
    async def test_project_name_uses_prefix(self):
        client = _make_client(projects=[_project("p1", "Work")])
        storage = _make_storage()
        service = TodoistImportService(client, storage)

        await service.import_all(_default_options(project_name_prefix="[T]"))

        created_name = storage.project_repository.create.call_args[0][0].name
        assert created_name == "[T] Work"

    @pytest.mark.asyncio
    async def test_empty_prefix_no_leading_space(self):
        client = _make_client(projects=[_project("p1", "Work")])
        storage = _make_storage()
        service = TodoistImportService(client, storage)

        await service.import_all(_default_options(project_name_prefix=""))

        created_name = storage.project_repository.create.call_args[0][0].name
        assert created_name == "Work"  # no leading space


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_does_not_write_projects(self):
        client = _make_client(projects=[_project()], tasks=[], labels=[])
        storage = _make_storage()
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options(dry_run=True))

        storage.project_repository.create.assert_not_called()
        assert result.projects_created == 1  # still counted

    @pytest.mark.asyncio
    async def test_dry_run_does_not_write_labels(self):
        client = _make_client(projects=[], tasks=[], labels=[_label()])
        storage = _make_storage()
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options(dry_run=True))

        storage.label_repository.create.assert_not_called()
        assert result.labels_created == 1

    @pytest.mark.asyncio
    async def test_dry_run_does_not_write_tasks(self):
        client = _make_client(
            projects=[_project()],
            tasks=[_task()],
            labels=[],
        )
        storage = _make_storage()
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options(dry_run=True))

        storage.task_repository.add.assert_not_called()
        assert result.tasks_created == 1


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_skips_existing_project_by_exact_name(self):
        existing = MagicMock()
        existing.name = "[Todoist] Inbox"
        client = _make_client(projects=[_project("p1", "Inbox")])
        storage = _make_storage(existing_projects=[existing])
        storage.project_repository.list_all = AsyncMock(return_value=[existing])
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options())

        storage.project_repository.create.assert_not_called()
        assert result.projects_skipped == 1
        assert result.projects_created == 0

    @pytest.mark.asyncio
    async def test_skips_task_with_identical_content(self):
        existing_task = MagicMock()
        existing_task.content = "Buy milk"
        client = _make_client(projects=[_project()], tasks=[_task(content="Buy milk")])
        storage = _make_storage(existing_tasks=[existing_task])
        storage.task_repository.list_all = AsyncMock(return_value=[existing_task])
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options())

        storage.task_repository.add.assert_not_called()
        assert result.tasks_skipped == 1

    @pytest.mark.asyncio
    async def test_skips_existing_label_case_insensitive(self):
        existing_lbl = MagicMock()
        existing_lbl.name = "@Home"
        existing_lbl.id = "existing-id"
        client = _make_client(labels=[_label(name="@home")])
        storage = _make_storage(existing_labels=[existing_lbl])
        storage.label_repository.list_all = AsyncMock(return_value=[existing_lbl])
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options())

        storage.label_repository.create.assert_not_called()
        assert result.labels_skipped == 1


# ---------------------------------------------------------------------------
# Due date parsing
# ---------------------------------------------------------------------------


class TestParseDueDate:
    def test_parses_date_only(self):
        task = _task()
        task.due = TodoistDue(date="2025-12-31")
        result = TodoistImportService._parse_due_date(task)
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 31

    def test_parses_datetime(self):
        task = _task()
        task.due = TodoistDue(date="2025-12-31T10:00:00")
        result = TodoistImportService._parse_due_date(task)
        assert result is not None
        assert result.hour == 10

    def test_returns_none_when_no_due(self):
        task = _task()
        task.due = None
        assert TodoistImportService._parse_due_date(task) is None

    def test_returns_none_for_invalid_format(self):
        task = _task()
        task.due = TodoistDue(date="not-a-date")
        assert TodoistImportService._parse_due_date(task) is None


# ---------------------------------------------------------------------------
# Label resolution
# ---------------------------------------------------------------------------


class TestResolveLabelIds:
    def test_resolves_known_labels(self):
        label_map = {"@home": "id-home", "@work": "id-work"}
        result = TodoistImportService._resolve_label_ids(["@home", "@work"], label_map)
        assert result == ["id-home", "id-work"]

    def test_skips_unknown_labels(self):
        label_map = {"@home": "id-home"}
        result = TodoistImportService._resolve_label_ids(["@home", "@unknown"], label_map)
        assert result == ["id-home"]

    def test_returns_empty_for_no_labels(self):
        assert TodoistImportService._resolve_label_ids([], {}) == []


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_project_repo_error_is_captured(self):
        client = _make_client(projects=[_project()])
        storage = _make_storage()
        storage.project_repository.list_all = AsyncMock(return_value=[])
        storage.project_repository.create = AsyncMock(side_effect=Exception("DB error"))
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options())

        assert result.has_errors
        assert any("DB error" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_task_repo_error_is_captured(self):
        client = _make_client(projects=[_project()], tasks=[_task()])
        storage = _make_storage()
        storage.task_repository.add = AsyncMock(side_effect=Exception("Write fail"))
        service = TodoistImportService(client, storage)

        result = await service.import_all(_default_options())

        assert result.has_errors
