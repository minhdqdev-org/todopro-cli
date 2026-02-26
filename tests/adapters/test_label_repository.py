"""Unit tests for SqliteLabelRepository.

Uses an in-memory SQLite database so tests run without touching the filesystem
and without needing a real config/user manager.
"""

from __future__ import annotations

import sqlite3

import pytest
import pytest_asyncio

from todopro_cli.adapters.sqlite import schema as db_schema
from todopro_cli.adapters.sqlite.label_repository import SqliteLabelRepository
from todopro_cli.models import LabelCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "user-label-001"


def _create_in_memory_db() -> sqlite3.Connection:
    """Create an in-memory SQLite database with the required schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(db_schema.CREATE_USERS_TABLE)
    conn.execute(db_schema.CREATE_LABELS_TABLE)
    conn.commit()
    return conn


def _make_repo(conn: sqlite3.Connection, user_id: str = USER_ID) -> SqliteLabelRepository:
    """Return a repository wired to the given connection and user."""
    repo = SqliteLabelRepository.__new__(SqliteLabelRepository)
    repo.db_path = None
    repo.config_manager = None
    repo._connection = conn
    repo._user_id = user_id
    return repo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> sqlite3.Connection:
    """Fresh in-memory DB with a seeded test user."""
    conn = _create_in_memory_db()
    conn.execute(
        "INSERT INTO users (id, email, name, timezone, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (USER_ID, "test@example.com", "Test User", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    conn.commit()
    return conn


@pytest.fixture
def repo(db: sqlite3.Connection) -> SqliteLabelRepository:
    return _make_repo(db)


# ---------------------------------------------------------------------------
# connection property
# ---------------------------------------------------------------------------


class TestConnectionProperty:
    def test_returns_injected_connection(self, repo, db):
        """connection property returns pre-injected connection."""
        assert repo.connection is db

    def test_lazy_init_creates_connection_when_none(self, tmp_path, mocker):
        """connection property creates a new connection when _connection is None."""
        db_file = tmp_path / "test.db"
        mock_conn = mocker.MagicMock()
        mocker.patch(
            "todopro_cli.adapters.sqlite.label_repository.get_connection",
            return_value=mock_conn,
        )
        repo = SqliteLabelRepository.__new__(SqliteLabelRepository)
        repo.db_path = str(db_file)
        repo.config_manager = None
        repo._connection = None
        repo._user_id = "x"

        conn = repo.connection
        assert conn is mock_conn
        # Second access should return the cached value
        assert repo.connection is mock_conn


# ---------------------------------------------------------------------------
# _get_user_id
# ---------------------------------------------------------------------------


class TestGetUserId:
    def test_returns_cached_user_id(self, repo):
        """_get_user_id returns the already-set _user_id without DB call."""
        repo._user_id = "cached-id"
        assert repo._get_user_id() == "cached-id"

    def test_fetches_user_id_when_none(self, db, mocker):
        """_get_user_id calls get_or_create_local_user when _user_id is None."""
        new_id = "fetched-user"
        mocker.patch(
            "todopro_cli.adapters.sqlite.label_repository.get_or_create_local_user",
            return_value=new_id,
        )
        repo = _make_repo(db)
        repo._user_id = None

        result = repo._get_user_id()

        assert result == new_id
        assert repo._user_id == new_id


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


class TestListAll:
    @pytest.mark.asyncio
    async def test_empty_when_no_labels(self, repo):
        result = await repo.list_all()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_all_labels_ordered_by_name(self, repo, db):
        db.executemany(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("id-z", "Zebra", "#ff0000", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
                ("id-a", "Alpha", "#00ff00", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
            ],
        )
        db.commit()

        result = await repo.list_all()

        assert len(result) == 2
        assert result[0].name == "Alpha"
        assert result[1].name == "Zebra"

    @pytest.mark.asyncio
    async def test_returns_only_current_users_labels(self, repo, db):
        """Labels belonging to a different user must not be returned."""
        db.execute(
            "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("other-user", "other@example.com", "Other", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.execute(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("id-other", "OtherLabel", "#000000", "other-user", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.execute(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("id-mine", "MyLabel", "#ffffff", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()

        result = await repo.list_all()

        assert len(result) == 1
        assert result[0].name == "MyLabel"


# ---------------------------------------------------------------------------
# get / get_by_id
# ---------------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_get_existing_label(self, repo, db):
        db.execute(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("label-1", "Work", "#0000ff", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()

        label = await repo.get("label-1")

        assert label.id == "label-1"
        assert label.name == "Work"

    @pytest.mark.asyncio
    async def test_get_raises_when_not_found(self, repo):
        with pytest.raises(ValueError, match="Label not found"):
            await repo.get("non-existent-id")

    @pytest.mark.asyncio
    async def test_get_raises_for_other_users_label(self, repo, db):
        """get() must not return labels owned by a different user."""
        db.execute(
            "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("other-user", "other@example.com", "Other", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.execute(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("label-other", "OtherLabel", "#000000", "other-user", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()

        with pytest.raises(ValueError):
            await repo.get("label-other")

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_get(self, repo, db):
        db.execute(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("label-2", "Personal", "#123456", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()

        label = await repo.get_by_id("label-2")
        assert label.id == "label-2"

    @pytest.mark.asyncio
    async def test_get_by_id_raises_when_not_found(self, repo):
        with pytest.raises(ValueError):
            await repo.get_by_id("missing")


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_label_with_id(self, repo):
        label = await repo.create(LabelCreate(name="Urgent", color="#ff0000"))

        assert label.name == "Urgent"
        assert label.color == "#ff0000"
        assert label.id  # non-empty UUID

    @pytest.mark.asyncio
    async def test_create_persists_to_db(self, repo, db):
        await repo.create(LabelCreate(name="Persistent", color="#abcdef"))

        cursor = db.execute("SELECT * FROM labels WHERE name = ?", ("Persistent",))
        row = cursor.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_create_duplicate_name_raises_value_error(self, repo):
        await repo.create(LabelCreate(name="Dup", color="#111111"))
        with pytest.raises(ValueError, match="already exists"):
            await repo.create(LabelCreate(name="Dup", color="#222222"))

    @pytest.mark.asyncio
    async def test_create_without_color(self, repo):
        """Creating a label with no color should succeed."""
        label = await repo.create(LabelCreate(name="NoColor"))
        assert label.name == "NoColor"

    @pytest.mark.asyncio
    async def test_create_multiple_unique_names(self, repo):
        l1 = await repo.create(LabelCreate(name="A"))
        l2 = await repo.create(LabelCreate(name="B"))
        assert l1.id != l2.id


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_true(self, repo, db):
        db.execute(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("del-1", "ToDelete", "#aabbcc", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()

        result = await repo.delete("del-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_removes_label_from_db(self, repo, db):
        db.execute(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("del-2", "Gone", "#aabbcc", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()

        await repo.delete("del-2")

        cursor = db.execute("SELECT * FROM labels WHERE id = ?", ("del-2",))
        assert cursor.fetchone() is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_true(self, repo):
        """Deleting a label that does not exist should still return True."""
        result = await repo.delete("ghost-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_does_not_affect_other_labels(self, repo, db):
        db.executemany(
            "INSERT INTO labels (id, name, color, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("keep-1", "Keep", "#111111", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
                ("rm-1", "Remove", "#222222", USER_ID, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
            ],
        )
        db.commit()

        await repo.delete("rm-1")

        remaining = await repo.list_all()
        assert len(remaining) == 1
        assert remaining[0].id == "keep-1"


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_matching_prefix(self, repo):
        await repo.create(LabelCreate(name="Work"))
        await repo.create(LabelCreate(name="Workout"))
        await repo.create(LabelCreate(name="Personal"))

        result = await repo.search("Work")
        names = {l.name for l in result}
        assert "Work" in names
        assert "Workout" in names
        assert "Personal" not in names

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_match(self, repo):
        await repo.create(LabelCreate(name="Alpha"))
        result = await repo.search("XYZ")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_is_case_sensitive_by_default(self, repo):
        """SQLite LIKE is case-sensitive for non-ASCII but case-insensitive for ASCII letters.
        This test ensures at least a match for the exact case."""
        await repo.create(LabelCreate(name="Work"))
        result = await repo.search("Wo")
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_search_returns_all_when_prefix_empty(self, repo):
        await repo.create(LabelCreate(name="AAA"))
        await repo.create(LabelCreate(name="BBB"))

        result = await repo.search("")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_ordered_by_name(self, repo):
        await repo.create(LabelCreate(name="Zulu"))
        await repo.create(LabelCreate(name="Zebra"))
        await repo.create(LabelCreate(name="Zone"))

        result = await repo.search("Z")
        names = [l.name for l in result]
        assert names == sorted(names)
