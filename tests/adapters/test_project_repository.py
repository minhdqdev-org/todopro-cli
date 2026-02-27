"""Comprehensive unit tests for SqliteProjectRepository.

Uses a real in-memory SQLite database with the full migration schema,
so SQL is exercised without touching production data.
"""

from __future__ import annotations

import sqlite3

import pytest

from todopro_cli.adapters.sqlite.project_repository import (
    SqliteProjectRepository,
)
from todopro_cli.adapters.sqlite import schema as db_schema
from todopro_cli.models import Project, ProjectCreate, ProjectFilters, ProjectUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_in_memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

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
            pass

    conn.commit()
    return conn


def _make_repo(conn: sqlite3.Connection, user_id: str) -> SqliteProjectRepository:
    repo = SqliteProjectRepository.__new__(SqliteProjectRepository)
    repo.db_path = None
    repo.config_manager = None
    repo._connection = conn
    repo._user_id = user_id
    return repo


@pytest.fixture
def db():
    conn = _create_in_memory_db()
    user_id = "user-001"
    conn.execute(
        "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "test@example.com", "Test User", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    conn.commit()
    return conn, user_id


@pytest.fixture
def repo(db):
    conn, user_id = db
    return _make_repo(conn, user_id)


@pytest.fixture
def repo_with_inbox(repo, db):
    """Repo that has Inbox project already ensured."""
    conn, user_id = db
    repo._ensure_inbox_project(user_id)
    return repo


# ---------------------------------------------------------------------------
# _ensure_inbox_project
# ---------------------------------------------------------------------------


class TestEnsureInboxProject:
    def test_creates_inbox_on_first_call(self, repo, db):
        conn, user_id = db
        repo._ensure_inbox_project(user_id)
        cursor = conn.execute(
            "SELECT id, protected FROM projects WHERE user_id = ? AND LOWER(name) = 'inbox' AND deleted_at IS NULL",
            (user_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == 1  # protected = True

    def test_idempotent_second_call(self, repo, db):
        conn, user_id = db
        repo._ensure_inbox_project(user_id)
        repo._ensure_inbox_project(user_id)  # Should not raise or duplicate
        cursor = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE user_id = ? AND LOWER(name) = 'inbox' AND deleted_at IS NULL",
            (user_id,),
        )
        assert cursor.fetchone()[0] == 1

    def test_inbox_has_random_uuid(self, repo, db):
        conn, user_id = db
        repo._ensure_inbox_project(user_id)
        cursor = conn.execute(
            "SELECT id FROM projects WHERE user_id = ? AND LOWER(name) = 'inbox' AND deleted_at IS NULL",
            (user_id,),
        )
        inbox_id = cursor.fetchone()[0]
        assert inbox_id != "00000000-0000-0000-0000-000000000000"
        assert len(inbox_id) == 36  # standard UUID format

    def test_second_call_returns_same_inbox_id(self, repo, db):
        conn, user_id = db
        repo._ensure_inbox_project(user_id)
        cursor = conn.execute(
            "SELECT id FROM projects WHERE user_id = ? AND LOWER(name) = 'inbox'",
            (user_id,),
        )
        first_id = cursor.fetchone()[0]
        repo._ensure_inbox_project(user_id)
        cursor = conn.execute(
            "SELECT id FROM projects WHERE user_id = ? AND LOWER(name) = 'inbox'",
            (user_id,),
        )
        second_id = cursor.fetchone()[0]
        assert first_id == second_id

    def test_migrates_null_project_id_tasks_to_inbox(self, repo, db):
        conn, user_id = db
        # Create a task with NULL project_id
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, priority, created_at, updated_at, version) "
            "VALUES ('t-null-proj', 'Test', 0, ?, 4, '2024-01-01', '2024-01-01', 1)",
            (user_id,),
        )
        conn.commit()
        repo._ensure_inbox_project(user_id)
        # Get inbox id
        cursor = conn.execute(
            "SELECT id FROM projects WHERE user_id = ? AND protected = 1",
            (user_id,),
        )
        inbox_id = cursor.fetchone()[0]
        cursor = conn.execute(
            "SELECT project_id FROM tasks WHERE id = 't-null-proj'",
        )
        assert cursor.fetchone()[0] == inbox_id


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_basic_project(self, repo):
        proj = await repo.create(ProjectCreate(name="My Project"))
        assert isinstance(proj, Project)
        assert proj.name == "My Project"

    @pytest.mark.asyncio
    async def test_create_with_color(self, repo):
        proj = await repo.create(ProjectCreate(name="Colored", color="#ff0000"))
        assert proj.color == "#ff0000"

    @pytest.mark.asyncio
    async def test_create_with_favorite(self, repo):
        proj = await repo.create(ProjectCreate(name="Fav", is_favorite=True))
        assert proj.is_favorite is True

    @pytest.mark.asyncio
    async def test_create_duplicate_name_raises(self, repo):
        await repo.create(ProjectCreate(name="Duplicate"))
        with pytest.raises(ValueError, match="already exists"):
            await repo.create(ProjectCreate(name="Duplicate"))

    @pytest.mark.asyncio
    async def test_create_duplicate_name_case_insensitive_raises(self, repo):
        await repo.create(ProjectCreate(name="MyProject"))
        with pytest.raises(ValueError, match="already exists"):
            await repo.create(ProjectCreate(name="myproject"))

    @pytest.mark.asyncio
    async def test_create_returns_id(self, repo):
        proj = await repo.create(ProjectCreate(name="IDTest"))
        assert len(proj.id) == 36  # UUID

    @pytest.mark.asyncio
    async def test_create_multiple_projects(self, repo):
        p1 = await repo.create(ProjectCreate(name="Alpha"))
        p2 = await repo.create(ProjectCreate(name="Beta"))
        assert p1.id != p2.id


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_get_existing_project(self, repo):
        created = await repo.create(ProjectCreate(name="Fetch Me"))
        fetched = await repo.get(created.id)
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self, repo):
        with pytest.raises(ValueError, match="Project not found"):
            await repo.get("nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_by_id_alias(self, repo):
        created = await repo.create(ProjectCreate(name="Alias"))
        fetched = await repo.get_by_id(created.id)
        assert fetched.id == created.id


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


class TestListAll:
    @pytest.mark.asyncio
    async def test_list_all_returns_projects(self, repo):
        await repo.create(ProjectCreate(name="Alpha"))
        await repo.create(ProjectCreate(name="Beta"))
        projects = await repo.list_all(ProjectFilters())
        names = [p.name for p in projects]
        assert "Alpha" in names
        assert "Beta" in names

    @pytest.mark.asyncio
    async def test_list_all_empty(self, repo):
        projects = await repo.list_all(ProjectFilters())
        assert projects == []

    @pytest.mark.asyncio
    async def test_list_filter_by_favorite(self, repo):
        await repo.create(ProjectCreate(name="Fav", is_favorite=True))
        await repo.create(ProjectCreate(name="Normal"))
        projects = await repo.list_all(ProjectFilters(is_favorite=True))
        assert all(p.is_favorite for p in projects)

    @pytest.mark.asyncio
    async def test_list_filter_by_archived(self, repo):
        p = await repo.create(ProjectCreate(name="To Archive"))
        await repo.archive(p.id)
        await repo.create(ProjectCreate(name="Active"))
        projects = await repo.list_all(ProjectFilters(is_archived=True))
        assert all(p.is_archived for p in projects)

    @pytest.mark.asyncio
    async def test_list_filter_by_search(self, repo):
        await repo.create(ProjectCreate(name="Groceries"))
        await repo.create(ProjectCreate(name="Work"))
        projects = await repo.list_all(ProjectFilters(search="Groc"))
        assert len(projects) == 1
        assert projects[0].name == "Groceries"

    @pytest.mark.asyncio
    async def test_list_excludes_deleted(self, repo):
        p = await repo.create(ProjectCreate(name="Deleted"))
        await repo.delete(p.id)
        projects = await repo.list_all(ProjectFilters())
        ids = [proj.id for proj in projects]
        assert p.id not in ids

    @pytest.mark.asyncio
    async def test_list_filter_by_id_prefix(self, repo):
        p = await repo.create(ProjectCreate(name="Prefix Test"))
        prefix = p.id[:8]
        projects = await repo.list_all(ProjectFilters(id_prefix=prefix))
        assert len(projects) == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_name(self, repo):
        p = await repo.create(ProjectCreate(name="Old Name"))
        updated = await repo.update(p.id, ProjectUpdate(name="New Name"))
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_color(self, repo):
        p = await repo.create(ProjectCreate(name="Color Test"))
        updated = await repo.update(p.id, ProjectUpdate(color="#00ff00"))
        assert updated.color == "#00ff00"

    @pytest.mark.asyncio
    async def test_update_no_fields_returns_unchanged(self, repo):
        p = await repo.create(ProjectCreate(name="No Change"))
        result = await repo.update(p.id, ProjectUpdate())
        assert result.name == "No Change"

    @pytest.mark.asyncio
    async def test_update_duplicate_name_raises(self, repo):
        await repo.create(ProjectCreate(name="Existing"))
        p2 = await repo.create(ProjectCreate(name="Other"))
        with pytest.raises(ValueError, match="already exists"):
            await repo.update(p2.id, ProjectUpdate(name="Existing"))

    @pytest.mark.asyncio
    async def test_update_duplicate_name_case_insensitive_raises(self, repo):
        await repo.create(ProjectCreate(name="UPPER"))
        p2 = await repo.create(ProjectCreate(name="Lower"))
        with pytest.raises(ValueError, match="already exists"):
            await repo.update(p2.id, ProjectUpdate(name="upper"))

    @pytest.mark.asyncio
    async def test_update_same_name_on_same_project_ok(self, repo):
        """Renaming a project to its own name should succeed."""
        p = await repo.create(ProjectCreate(name="SameName"))
        updated = await repo.update(p.id, ProjectUpdate(name="SameName"))
        assert updated.name == "SameName"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_soft_deletes(self, repo):
        p = await repo.create(ProjectCreate(name="Delete Me"))
        result = await repo.delete(p.id)
        assert result is True
        with pytest.raises(ValueError):
            await repo.get(p.id)

    @pytest.mark.asyncio
    async def test_delete_returns_true(self, repo):
        p = await repo.create(ProjectCreate(name="Gone"))
        assert await repo.delete(p.id) is True


# ---------------------------------------------------------------------------
# archive / unarchive
# ---------------------------------------------------------------------------


class TestArchiveUnarchive:
    @pytest.mark.asyncio
    async def test_archive_sets_flag(self, repo):
        p = await repo.create(ProjectCreate(name="Active"))
        archived = await repo.archive(p.id)
        assert archived.is_archived is True

    @pytest.mark.asyncio
    async def test_unarchive_clears_flag(self, repo):
        p = await repo.create(ProjectCreate(name="To Unarchive"))
        archived = await repo.archive(p.id)
        unarchived = await repo.unarchive(archived.id)
        assert unarchived.is_archived is False

    @pytest.mark.asyncio
    async def test_archive_updates_timestamp(self, repo, db):
        """Archive sets updated_at to a recent timestamp."""
        conn, user_id = db
        p = await repo.create(ProjectCreate(name="Version Check"))
        archived = await repo.archive(p.id)
        # After archive, updated_at should be >= created_at
        assert archived.updated_at >= p.created_at


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    @pytest.mark.asyncio
    async def test_get_stats_empty_project(self, repo):
        p = await repo.create(ProjectCreate(name="Empty"))
        stats = await repo.get_stats(p.id)
        assert stats["total_tasks"] == 0
        assert stats["completion_rate"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_tasks(self, repo, db):
        conn, user_id = db
        p = await repo.create(ProjectCreate(name="With Tasks"))
        # Insert tasks directly
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, project_id, priority, created_at, updated_at, version) "
            "VALUES ('task-a', 'Task A', 1, ?, ?, 4, '2024-01-01', '2024-01-01', 1)",
            (user_id, p.id),
        )
        conn.execute(
            "INSERT INTO tasks (id, content, is_completed, user_id, project_id, priority, created_at, updated_at, version) "
            "VALUES ('task-b', 'Task B', 0, ?, ?, 4, '2024-01-01', '2024-01-01', 1)",
            (user_id, p.id),
        )
        conn.commit()
        stats = await repo.get_stats(p.id)
        assert stats["total_tasks"] == 2
        assert stats["completed_tasks"] == 1
        assert stats["pending_tasks"] == 1
        assert stats["completion_rate"] == 50

    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self, repo):
        p = await repo.create(ProjectCreate(name="Stats Project"))
        stats = await repo.get_stats(p.id)
        assert isinstance(stats, dict)
        assert "total_tasks" in stats
        assert "completion_rate" in stats
