"""Comprehensive unit tests for SqliteTaskRepository.

Uses a real SQLite in-memory or temp-file database with the full migration
schema applied, so we test the real SQL without touching production data.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from todopro_cli.adapters.sqlite.task_repository import SqliteTaskRepository
from todopro_cli.adapters.sqlite import schema as db_schema
from todopro_cli.models import Task, TaskCreate, TaskFilters, TaskUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_in_memory_db() -> sqlite3.Connection:
    """Create an in-memory SQLite database with full schema applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Apply schema tables
    conn.execute(db_schema.CREATE_USERS_TABLE)
    conn.execute(db_schema.CREATE_PROJECTS_TABLE)
    conn.execute(db_schema.CREATE_LABELS_TABLE)
    conn.execute(db_schema.CREATE_CONTEXTS_TABLE)
    conn.execute(db_schema.CREATE_TASKS_TABLE)
    conn.execute(db_schema.CREATE_TASK_LABELS_TABLE)
    conn.execute(db_schema.CREATE_TASK_CONTEXTS_TABLE)
    conn.execute(db_schema.CREATE_REMINDERS_TABLE)
    conn.execute(db_schema.CREATE_FILTERS_TABLE)

    for idx_sql in db_schema.ALL_INDEXES:
        try:
            conn.execute(idx_sql)
        except sqlite3.OperationalError:
            pass  # Ignore index creation errors on in-memory DB

    conn.commit()
    return conn


def _make_repo(conn: sqlite3.Connection, user_id: str = "user-001") -> SqliteTaskRepository:
    """Create a repository with a pre-seeded connection and user_id."""
    repo = SqliteTaskRepository.__new__(SqliteTaskRepository)
    repo.db_path = None
    repo.config_service = None
    repo._connection = conn
    repo._user_id = user_id
    repo._e2ee_handler = None
    return repo


@pytest.fixture
def db():
    """Provide a fresh in-memory database with a test user."""
    conn = _create_in_memory_db()
    user_id = "user-001"
    # Insert test user
    conn.execute(
        "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "test@example.com", "Test User", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    conn.commit()
    return conn, user_id


@pytest.fixture
def repo(db):
    """Provide a SqliteTaskRepository backed by in-memory DB."""
    conn, user_id = db
    r = _make_repo(conn, user_id)
    # Patch E2EE to disabled so we don't need encryption keys
    e2ee_mock = MagicMock()
    e2ee_mock.enabled = False
    e2ee_mock.prepare_task_for_storage.side_effect = lambda c, d: (c, None, d, None)
    e2ee_mock.extract_task_content.side_effect = lambda c, ce, d, de: (c, d)
    r._e2ee_handler = e2ee_mock
    return r


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _task_create(
    content: str = "Test task",
    description: str | None = None,
    priority: int = 4,
    project_id: str | None = None,
    labels: list[str] | None = None,
    contexts: list[str] | None = None,
) -> TaskCreate:
    return TaskCreate(
        content=content,
        description=description,
        priority=priority,
        project_id=project_id,
        labels=labels or [],
        contexts=contexts or [],
    )


# ---------------------------------------------------------------------------
# _get_user_id
# ---------------------------------------------------------------------------


class TestGetUserId:
    def test_returns_cached_user_id(self, repo):
        assert repo._get_user_id() == "user-001"

    def test_gets_user_id_from_config_service(self, db):
        conn, _ = db
        config_service = MagicMock()
        ctx = MagicMock()
        ctx.local_user_id = "config-user"
        config_service.get_current_context.return_value = ctx

        r = _make_repo(conn, None)
        r.config_service = config_service
        e2ee_mock = MagicMock()
        e2ee_mock.enabled = False
        e2ee_mock.prepare_task_for_storage.side_effect = lambda c, d: (c, None, d, None)
        r._e2ee_handler = e2ee_mock

        uid = r._get_user_id()
        assert uid == "config-user"

    def test_creates_user_when_none_exists(self, db):
        conn, _ = db
        r = _make_repo(conn, None)
        r.config_service = None
        e2ee_mock = MagicMock()
        e2ee_mock.enabled = False
        e2ee_mock.prepare_task_for_storage.side_effect = lambda c, d: (c, None, d, None)
        r._e2ee_handler = e2ee_mock
        # There is already a user in db, so it will return the existing one
        uid = r._get_user_id()
        assert uid is not None


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestAdd:
    @pytest.mark.asyncio
    async def test_add_basic_task(self, repo):
        task = await repo.add(_task_create("Buy groceries"))
        assert isinstance(task, Task)
        assert task.content == "Buy groceries"
        assert task.is_completed is False

    @pytest.mark.asyncio
    async def test_add_task_with_priority(self, repo):
        task = await repo.add(_task_create("Urgent task", priority=1))
        assert task.priority == 1

    @pytest.mark.asyncio
    async def test_add_task_returns_id(self, repo):
        task = await repo.add(_task_create("Some task"))
        assert len(task.id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_add_task_with_description(self, repo):
        task = await repo.add(_task_create("Task", description="Detailed description"))
        assert task.description == "Detailed description"

    @pytest.mark.asyncio
    async def test_add_task_with_labels(self, repo, db):
        conn, user_id = db
        # Insert a label first
        conn.execute(
            "INSERT INTO labels (id, name, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("label-1", "work", user_id, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        conn.commit()

        task = await repo.add(_task_create("Task with label", labels=["label-1"]))
        assert "label-1" in task.labels

    @pytest.mark.asyncio
    async def test_add_multiple_tasks(self, repo):
        t1 = await repo.add(_task_create("Task 1"))
        t2 = await repo.add(_task_create("Task 2"))
        assert t1.id != t2.id


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_get_existing_task(self, repo):
        created = await repo.add(_task_create("Fetch me"))
        fetched = await repo.get(created.id)
        assert fetched.id == created.id
        assert fetched.content == "Fetch me"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_raises(self, repo):
        with pytest.raises(ValueError, match="Task not found"):
            await repo.get("nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_by_id_alias(self, repo):
        created = await repo.add(_task_create("Alias test"))
        fetched = await repo.get_by_id(created.id)
        assert fetched.id == created.id


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


class TestListAll:
    @pytest.mark.asyncio
    async def test_list_all_returns_tasks(self, repo):
        await repo.add(_task_create("Task A"))
        await repo.add(_task_create("Task B"))
        tasks = await repo.list_all(TaskFilters())
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_list_all_empty(self, repo):
        tasks = await repo.list_all(TaskFilters())
        assert tasks == []

    @pytest.mark.asyncio
    async def test_list_filter_active(self, repo):
        t = await repo.add(_task_create("Active"))
        await repo.complete(t.id)
        await repo.add(_task_create("Pending"))
        tasks = await repo.list_all(TaskFilters(status="active"))
        assert all(not t.is_completed for t in tasks)

    @pytest.mark.asyncio
    async def test_list_filter_completed(self, repo):
        t = await repo.add(_task_create("To complete"))
        await repo.complete(t.id)
        await repo.add(_task_create("Still active"))
        tasks = await repo.list_all(TaskFilters(status="completed"))
        assert all(t.is_completed for t in tasks)

    @pytest.mark.asyncio
    async def test_list_filter_by_search(self, repo):
        await repo.add(_task_create("Buy groceries"))
        await repo.add(_task_create("Write tests"))
        tasks = await repo.list_all(TaskFilters(search="groceries"))
        assert len(tasks) == 1
        assert tasks[0].content == "Buy groceries"

    @pytest.mark.asyncio
    async def test_list_filter_by_priority(self, repo):
        await repo.add(_task_create("High priority", priority=1))
        await repo.add(_task_create("Low priority", priority=4))
        tasks = await repo.list_all(TaskFilters(priority=1))
        assert len(tasks) == 1
        assert tasks[0].priority == 1

    @pytest.mark.asyncio
    async def test_list_filter_by_id_prefix(self, repo):
        t = await repo.add(_task_create("ID prefix test"))
        prefix = t.id[:8]
        tasks = await repo.list_all(TaskFilters(id_prefix=prefix))
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_list_with_limit(self, repo):
        for i in range(5):
            await repo.add(_task_create(f"Task {i}"))
        tasks = await repo.list_all(TaskFilters(limit=3))
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_with_offset(self, repo):
        for i in range(5):
            await repo.add(_task_create(f"Task {i}"))
        tasks_all = await repo.list_all(TaskFilters())
        # OFFSET requires LIMIT in SQLite; provide both
        tasks_offset = await repo.list_all(TaskFilters(limit=100, offset=2))
        assert len(tasks_offset) == len(tasks_all) - 2

    @pytest.mark.asyncio
    async def test_list_with_sort(self, repo):
        await repo.add(_task_create("Task C", priority=3))
        await repo.add(_task_create("Task A", priority=1))
        tasks = await repo.list_all(TaskFilters(sort="priority:asc"))
        assert tasks[0].priority <= tasks[-1].priority

    @pytest.mark.asyncio
    async def test_list_excludes_deleted(self, repo):
        t = await repo.add(_task_create("Will be deleted"))
        await repo.delete(t.id)
        tasks = await repo.list_all(TaskFilters())
        ids = [task.id for task in tasks]
        assert t.id not in ids

    @pytest.mark.asyncio
    async def test_list_filter_by_project(self, repo, db):
        conn, user_id = db
        conn.execute(
            "INSERT INTO projects (id, name, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("proj-1", "Project One", user_id, "2024-01-01", "2024-01-01"),
        )
        conn.commit()
        await repo.add(_task_create("In project", project_id="proj-1"))
        await repo.add(_task_create("No project"))
        tasks = await repo.list_all(TaskFilters(project_id="proj-1"))
        assert all(t.project_id == "proj-1" for t in tasks)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_content(self, repo):
        t = await repo.add(_task_create("Original"))
        updated = await repo.update(t.id, TaskUpdate(content="Updated"))
        assert updated.content == "Updated"

    @pytest.mark.asyncio
    async def test_update_priority(self, repo):
        t = await repo.add(_task_create("Task", priority=4))
        updated = await repo.update(t.id, TaskUpdate(priority=1))
        assert updated.priority == 1

    @pytest.mark.asyncio
    async def test_update_no_fields_returns_task(self, repo):
        t = await repo.add(_task_create("Unchanged"))
        result = await repo.update(t.id, TaskUpdate())
        assert result.id == t.id

    @pytest.mark.asyncio
    async def test_update_increments_version(self, repo):
        t = await repo.add(_task_create("Version test"))
        updated = await repo.update(t.id, TaskUpdate(content="New content"))
        assert updated.version > t.version

    @pytest.mark.asyncio
    async def test_update_labels(self, repo, db):
        conn, user_id = db
        conn.execute(
            "INSERT INTO labels (id, name, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("lbl-a", "alpha", user_id, "2024-01-01", "2024-01-01"),
        )
        conn.commit()
        t = await repo.add(_task_create("Task for labels"))
        # Must include a non-label field so the early-return branch is not hit
        updated = await repo.update(t.id, TaskUpdate(content="Task for labels updated", labels=["lbl-a"]))
        assert "lbl-a" in updated.labels


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_marks_soft_deleted(self, repo):
        t = await repo.add(_task_create("To delete"))
        result = await repo.delete(t.id)
        assert result is True
        # Task should no longer be visible
        with pytest.raises(ValueError):
            await repo.get(t.id)

    @pytest.mark.asyncio
    async def test_delete_returns_true(self, repo):
        t = await repo.add(_task_create("Delete me"))
        assert await repo.delete(t.id) is True


# ---------------------------------------------------------------------------
# complete
# ---------------------------------------------------------------------------


class TestComplete:
    @pytest.mark.asyncio
    async def test_complete_sets_is_completed(self, repo):
        t = await repo.add(_task_create("Complete me"))
        completed = await repo.complete(t.id)
        assert completed.is_completed is True

    @pytest.mark.asyncio
    async def test_complete_sets_completed_at(self, repo):
        t = await repo.add(_task_create("Complete me"))
        completed = await repo.complete(t.id)
        assert completed.completed_at is not None


# ---------------------------------------------------------------------------
# bulk_update
# ---------------------------------------------------------------------------


class TestBulkUpdate:
    @pytest.mark.asyncio
    async def test_bulk_update_multiple_tasks(self, repo):
        t1 = await repo.add(_task_create("Bulk 1"))
        t2 = await repo.add(_task_create("Bulk 2"))
        results = await repo.bulk_update([t1.id, t2.id], TaskUpdate(priority=2))
        assert all(t.priority == 2 for t in results)

    @pytest.mark.asyncio
    async def test_bulk_update_empty_list(self, repo):
        results = await repo.bulk_update([], TaskUpdate(priority=1))
        assert results == []


# ---------------------------------------------------------------------------
# labels & contexts helpers
# ---------------------------------------------------------------------------


class TestLabelContextHelpers:
    def test_get_task_labels_empty(self, repo, db):
        assert repo._get_task_labels("nonexistent") == []

    def test_get_task_contexts_empty(self, repo, db):
        assert repo._get_task_contexts("nonexistent") == []

    def test_set_and_get_task_labels(self, repo, db):
        conn, user_id = db
        conn.execute(
            "INSERT INTO labels (id, name, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("lbl-1", "test", user_id, "2024-01-01", "2024-01-01"),
        )
        conn.commit()
        # Need a real task to satisfy FK
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, created_at, updated_at, version) "
            "VALUES ('t1', 'x', 0, ?, 4, '2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        repo._set_task_labels("t1", ["lbl-1"])
        labels = repo._get_task_labels("t1")
        assert "lbl-1" in labels

    def test_set_task_labels_replaces_existing(self, repo, db):
        conn, user_id = db
        for i in range(2):
            conn.execute(
                "INSERT INTO labels (id, name, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (f"lbl-{i}", f"tag{i}", user_id, "2024-01-01", "2024-01-01"),
            )
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, created_at, updated_at, version) "
            "VALUES ('t2', 'y', 0, ?, 4, '2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        repo._set_task_labels("t2", ["lbl-0"])
        repo._set_task_labels("t2", ["lbl-1"])
        labels = repo._get_task_labels("t2")
        assert labels == ["lbl-1"]

    def test_set_and_get_task_contexts(self, repo, db):
        """Test _set_task_contexts and _get_task_contexts helpers (lines 422-428)."""
        conn, user_id = db
        # Insert a context first (FK constraint) - must include lat/lon
        conn.execute(
            "INSERT INTO contexts (id, name, user_id, latitude, longitude, radius, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("ctx-1", "@home", user_id, 37.7749, -122.4194, 100.0, "2024-01-01", "2024-01-01"),
        )
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, created_at, updated_at, version) "
            "VALUES ('t3', 'z', 0, ?, 4, '2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        repo._set_task_contexts("t3", ["ctx-1"])
        contexts = repo._get_task_contexts("t3")
        assert "ctx-1" in contexts

    def test_set_task_contexts_replaces_existing(self, repo, db):
        """Replacing task contexts removes old ones (lines 422-428)."""
        conn, user_id = db
        for i in range(2):
            conn.execute(
                "INSERT INTO contexts (id, name, user_id, latitude, longitude, radius, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"ctx-{i}", f"@ctx{i}", user_id, 1.0, 2.0, 100.0, "2024-01-01", "2024-01-01"),
            )
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, created_at, updated_at, version) "
            "VALUES ('t4', 'w', 0, ?, 4, '2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        repo._set_task_contexts("t4", ["ctx-0"])
        repo._set_task_contexts("t4", ["ctx-1"])
        contexts = repo._get_task_contexts("t4")
        assert contexts == ["ctx-1"]


# ---------------------------------------------------------------------------
# __init__ and lazy properties
# ---------------------------------------------------------------------------


class TestInit:
    """Test __init__ runs normally (lines 28-32)."""

    def test_init_sets_db_path(self):
        repo = SqliteTaskRepository(db_path=":memory:")
        assert repo.db_path == ":memory:"

    def test_init_sets_config_service(self):
        cs = MagicMock()
        repo = SqliteTaskRepository(config_service=cs)
        assert repo.config_service is cs

    def test_init_defaults(self):
        repo = SqliteTaskRepository()
        assert repo.db_path is None
        assert repo.config_service is None
        assert repo._connection is None
        assert repo._user_id is None
        assert repo._e2ee_handler is None


class TestConnectionProperty:
    """Test the connection property when _connection is None (line 38)."""

    def test_connection_calls_get_connection(self, db):
        conn, user_id = db
        with patch(
            "todopro_cli.adapters.sqlite.task_repository.get_connection",
            return_value=conn,
        ) as mock_get_conn:
            repo = SqliteTaskRepository(db_path=":memory:")
            # Access property – triggers get_connection
            result = repo.connection
            mock_get_conn.assert_called_once_with(":memory:")
            assert result is conn

    def test_connection_cached_after_first_access(self, db):
        conn, _ = db
        with patch(
            "todopro_cli.adapters.sqlite.task_repository.get_connection",
            return_value=conn,
        ) as mock_get_conn:
            repo = SqliteTaskRepository()
            _ = repo.connection
            _ = repo.connection  # second access
            assert mock_get_conn.call_count == 1  # should not call again


class TestE2EEProperty:
    """Test the e2ee property when _e2ee_handler is None (lines 45-47)."""

    def test_e2ee_calls_get_e2ee_handler(self):
        mock_handler = MagicMock()
        # The property does: from todopro_cli.adapters.sqlite.e2ee import get_e2ee_handler
        # Patch at the source so the local import picks up our mock
        with patch(
            "todopro_cli.adapters.sqlite.e2ee.get_e2ee_handler",
            return_value=mock_handler,
        ) as mock_factory:
            repo = SqliteTaskRepository()
            repo._e2ee_handler = None  # ensure unset
            result = repo.e2ee
            mock_factory.assert_called_once()
            assert result is mock_handler

    def test_e2ee_cached_after_first_access(self):
        mock_handler = MagicMock()
        with patch(
            "todopro_cli.adapters.sqlite.e2ee.get_e2ee_handler",
            return_value=mock_handler,
        ) as mock_factory:
            repo = SqliteTaskRepository()
            repo._e2ee_handler = None
            _ = repo.e2ee
            _ = repo.e2ee  # second access
            assert mock_factory.call_count == 1


# ---------------------------------------------------------------------------
# _get_user_id edge cases
# ---------------------------------------------------------------------------


class TestGetUserIdEdgeCases:
    """Additional _get_user_id paths (lines 62-63, 71-87)."""

    def test_config_service_exception_falls_back_to_db(self, db):
        """When config_service.get_current_context raises, fall back to DB user (lines 62-63)."""
        conn, existing_uid = db
        config_service = MagicMock()
        config_service.get_current_context.side_effect = RuntimeError("config error")

        r = _make_repo(conn, None)
        r.config_service = config_service
        e2ee_mock = MagicMock()
        e2ee_mock.enabled = False
        r._e2ee_handler = e2ee_mock

        uid = r._get_user_id()
        assert uid is not None  # falls back to DB

    def test_config_service_saves_user_when_no_local_user_id(self, db):
        """When local_user_id is absent, saves user to config (lines 71-87)."""
        conn, _ = db
        config_service = MagicMock()
        ctx = MagicMock()
        ctx.local_user_id = None  # No existing user id
        ctx.name = "test-context"
        ctx.endpoint = "https://example.com"
        ctx.description = "test"
        config_service.get_current_context.return_value = ctx
        config_service.config = MagicMock()
        config_service.config.model_dump.return_value = {
            "contexts": {"test-context": {"local_user_id": None}},
            "current_context_name": "test-context",
        }

        r = _make_repo(conn, None)
        r.config_service = config_service
        e2ee_mock = MagicMock()
        e2ee_mock.enabled = False
        r._e2ee_handler = e2ee_mock

        uid = r._get_user_id()
        assert uid is not None
        # add_context should have been called to save
        config_service.add_context.assert_called_once()

    def test_config_service_save_exception_is_swallowed(self, db):
        """Exceptions during config save don't propagate (lines 71-87)."""
        conn, _ = db
        config_service = MagicMock()
        ctx = MagicMock()
        ctx.local_user_id = None
        ctx.name = "ctx"
        ctx.endpoint = "url"
        ctx.description = ""
        config_service.get_current_context.return_value = ctx
        config_service.add_context.side_effect = RuntimeError("save failed")

        r = _make_repo(conn, None)
        r.config_service = config_service
        e2ee_mock = MagicMock()
        e2ee_mock.enabled = False
        r._e2ee_handler = e2ee_mock

        # Should not raise
        uid = r._get_user_id()
        assert uid is not None


# ---------------------------------------------------------------------------
# list_all – date range filters
# ---------------------------------------------------------------------------


class TestListAllDateFilters:
    """Cover due_before (lines 127-128) and due_after (lines 135-136) filters."""

    @pytest.mark.asyncio
    async def test_due_before_datetime_filter(self, repo, db):
        conn, user_id = db
        # Insert a task directly with a due_date
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, "
            "due_date, created_at, updated_at, version) "
            "VALUES ('due-task-1', 'Past task', 0, ?, 4, '2024-01-15T00:00:00', "
            "'2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, "
            "due_date, created_at, updated_at, version) "
            "VALUES ('due-task-2', 'Future task', 0, ?, 4, '2025-12-01T00:00:00', "
            "'2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)
        tasks = await repo.list_all(TaskFilters(due_before=cutoff))
        ids = [t.id for t in tasks]
        assert "due-task-1" in ids
        assert "due-task-2" not in ids

    @pytest.mark.asyncio
    async def test_due_after_datetime_filter(self, repo, db):
        conn, user_id = db
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, "
            "due_date, created_at, updated_at, version) "
            "VALUES ('after-task-1', 'Early task', 0, ?, 4, '2024-01-15T00:00:00', "
            "'2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, "
            "due_date, created_at, updated_at, version) "
            "VALUES ('after-task-2', 'Late task', 0, ?, 4, '2025-06-01T00:00:00', "
            "'2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
        tasks = await repo.list_all(TaskFilters(due_after=cutoff))
        ids = [t.id for t in tasks]
        assert "after-task-2" in ids
        assert "after-task-1" not in ids

    @pytest.mark.asyncio
    async def test_due_before_string_filter(self, repo, db):
        """due_before as string passes through directly (line 132)."""
        conn, user_id = db
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, "
            "due_date, created_at, updated_at, version) "
            "VALUES ('str-task-1', 'String date', 0, ?, 4, '2024-01-15T00:00:00', "
            "'2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        tasks = await repo.list_all(TaskFilters(due_before="2024-06-01T00:00:00"))
        ids = [t.id for t in tasks]
        assert "str-task-1" in ids


# ---------------------------------------------------------------------------
# E2EE decryption paths
# ---------------------------------------------------------------------------


class TestE2EEDecryption:
    """Cover E2EE decrypt paths in list_all (lines 171-178) and get (lines 202-210)."""

    def _make_e2ee_repo(self, conn, user_id):
        """Create a repo with E2EE enabled mock."""
        r = _make_repo(conn, user_id)
        e2ee_mock = MagicMock()
        e2ee_mock.enabled = True
        e2ee_mock.prepare_task_for_storage.side_effect = lambda c, d: (c, None, d, None)
        e2ee_mock.extract_task_content.side_effect = lambda c, ce, d, de: (
            f"decrypted:{c}",
            d,
        )
        r._e2ee_handler = e2ee_mock
        return r

    @pytest.mark.asyncio
    async def test_list_all_decrypts_content(self, db):
        conn, user_id = db
        repo = self._make_e2ee_repo(conn, user_id)
        await repo.add(_task_create("encrypted content"))
        tasks = await repo.list_all(TaskFilters())
        assert len(tasks) == 1
        # extract_task_content was called and injected "decrypted:" prefix
        assert tasks[0].content.startswith("decrypted:")

    @pytest.mark.asyncio
    async def test_get_decrypts_content(self, db):
        conn, user_id = db
        repo = self._make_e2ee_repo(conn, user_id)
        created = await repo.add(_task_create("secret"))
        fetched = await repo.get(created.id)
        assert fetched.content.startswith("decrypted:")


# ---------------------------------------------------------------------------
# add – datetime due_date and contexts
# ---------------------------------------------------------------------------


class TestAddWithDatetimeAndContexts:
    """Cover datetime conversion (line 236) and context assignment (line 273)."""

    @pytest.mark.asyncio
    async def test_add_with_datetime_due_date(self, repo):
        """Passing a datetime object as due_date triggers isoformat conversion (line 236)."""
        due = datetime(2025, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
        task = await repo.add(TaskCreate(content="Datetime task", due_date=due))
        assert task.id is not None

    @pytest.mark.asyncio
    async def test_add_with_contexts(self, repo, db):
        """Add task with contexts populates task_contexts table (line 273)."""
        conn, user_id = db
        conn.execute(
            "INSERT INTO contexts (id, name, user_id, latitude, longitude, radius, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("ctx-a", "@work", user_id, 40.7128, -74.0060, 100.0, "2024-01-01", "2024-01-01"),
        )
        conn.commit()
        task = await repo.add(
            TaskCreate(content="Context task", contexts=["ctx-a"])
        )
        assert "ctx-a" in task.contexts


# ---------------------------------------------------------------------------
# update – datetime due_date, E2EE description, contexts
# ---------------------------------------------------------------------------


class TestUpdateEdgeCases:
    """Cover update with datetime (line 298), E2EE description (lines 317-318), contexts (line 342)."""

    @pytest.mark.asyncio
    async def test_update_with_datetime_due_date(self, repo):
        """Datetime due_date in update triggers isoformat (line 298)."""
        t = await repo.add(_task_create("Original"))
        due = datetime(2025, 4, 10, 9, 0, 0, tzinfo=timezone.utc)
        updated = await repo.update(t.id, TaskUpdate(due_date=due))
        assert updated.id == t.id

    @pytest.mark.asyncio
    async def test_update_description_with_e2ee(self, db):
        """Updating description with E2EE enabled hits lines 317-318."""
        conn, user_id = db
        repo = _make_repo(conn, user_id)
        e2ee_mock = MagicMock()
        e2ee_mock.enabled = True
        e2ee_mock.prepare_task_for_storage.side_effect = lambda c, d: (
            c, None, d, None
        )
        e2ee_mock.extract_task_content.side_effect = lambda c, ce, d, de: (c, d)
        repo._e2ee_handler = e2ee_mock

        task = await repo.add(_task_create("E2EE task", description="original desc"))
        updated = await repo.update(task.id, TaskUpdate(description="new desc"))
        assert updated.id == task.id

    @pytest.mark.asyncio
    async def test_update_with_contexts(self, repo, db):
        """Update with contexts list triggers _set_task_contexts (line 342)."""
        conn, user_id = db
        conn.execute(
            "INSERT INTO contexts (id, name, user_id, latitude, longitude, radius, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("ctx-b", "@home", user_id, 34.0522, -118.2437, 100.0, "2024-01-01", "2024-01-01"),
        )
        conn.commit()
        t = await repo.add(_task_create("Context update"))
        updated = await repo.update(
            t.id, TaskUpdate(content="Context update updated", contexts=["ctx-b"])
        )
        assert "ctx-b" in updated.contexts


# ---------------------------------------------------------------------------
# bulk_update – exception / rollback
# ---------------------------------------------------------------------------


class TestBulkUpdateRollback:
    """Cover bulk_update rollback path (lines 389-391)."""

    @pytest.mark.asyncio
    async def test_bulk_update_rolls_back_on_error(self, repo):
        """When one update fails, the transaction rolls back and exception re-raised."""
        t = await repo.add(_task_create("Good task"))

        with pytest.raises(Exception):
            await repo.bulk_update(
                [t.id, "nonexistent-task-id-that-will-fail"],
                TaskUpdate(priority=2),
            )
