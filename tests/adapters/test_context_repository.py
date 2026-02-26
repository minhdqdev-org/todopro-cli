"""Unit tests for SqliteLocationContextRepository.

Uses an in-memory SQLite database to avoid filesystem side-effects.
"""

from __future__ import annotations

import sqlite3

import pytest

from todopro_cli.adapters.sqlite import schema as db_schema
from todopro_cli.adapters.sqlite.context_repository import SqliteLocationContextRepository
from todopro_cli.models import LocationContextCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "user-ctx-001"

# Coordinates for testing (London)
LONDON_LAT = 51.5074
LONDON_LON = -0.1278

# Coordinates close to London (within 500m)
NEARBY_LAT = 51.5080
NEARBY_LON = -0.1270

# Coordinates far from London
FAR_LAT = 48.8566  # Paris
FAR_LON = 2.3522


_CONTEXTS_TABLE_TEST = """
CREATE TABLE IF NOT EXISTS contexts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#808080',
    icon TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    radius REAL NOT NULL DEFAULT 100.0,
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    deleted_at DATETIME,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
"""


def _create_in_memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(db_schema.CREATE_USERS_TABLE)
    conn.execute(_CONTEXTS_TABLE_TEST)
    conn.commit()
    return conn


def _make_repo(conn: sqlite3.Connection, user_id: str = USER_ID) -> SqliteLocationContextRepository:
    repo = SqliteLocationContextRepository.__new__(SqliteLocationContextRepository)
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
    conn = _create_in_memory_db()
    conn.execute(
        "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (USER_ID, "ctx@example.com", "Ctx User", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    conn.commit()
    return conn


@pytest.fixture
def repo(db: sqlite3.Connection) -> SqliteLocationContextRepository:
    return _make_repo(db)


def _insert_context(db, cid, name, lat, lon, radius=100.0, user_id=USER_ID):
    db.execute(
        "INSERT INTO contexts (id, name, latitude, longitude, radius, user_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cid, name, lat, lon, radius, user_id, "2024-01-01T00:00:00"),
    )
    db.commit()


# ---------------------------------------------------------------------------
# connection property
# ---------------------------------------------------------------------------


class TestConnectionProperty:
    def test_returns_injected_connection(self, repo, db):
        assert repo.connection is db

    def test_lazy_init_creates_connection_when_none(self, mocker):
        mock_conn = mocker.MagicMock()
        mocker.patch(
            "todopro_cli.adapters.sqlite.context_repository.get_connection",
            return_value=mock_conn,
        )
        repo = SqliteLocationContextRepository.__new__(SqliteLocationContextRepository)
        repo.db_path = "some.db"
        repo.config_manager = None
        repo._connection = None
        repo._user_id = "x"

        assert repo.connection is mock_conn
        # Cached on second access
        assert repo.connection is mock_conn


# ---------------------------------------------------------------------------
# _get_user_id
# ---------------------------------------------------------------------------


class TestGetUserId:
    def test_returns_cached_user_id(self, repo):
        repo._user_id = "cached"
        assert repo._get_user_id() == "cached"

    def test_fetches_user_id_when_none(self, db, mocker):
        mocker.patch(
            "todopro_cli.adapters.sqlite.context_repository.get_or_create_local_user",
            return_value="fetched-id",
        )
        repo = _make_repo(db)
        repo._user_id = None
        result = repo._get_user_id()
        assert result == "fetched-id"
        assert repo._user_id == "fetched-id"


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


class TestListAll:
    @pytest.mark.asyncio
    async def test_empty_when_no_contexts(self, repo):
        assert await repo.list_all() == []

    @pytest.mark.asyncio
    async def test_returns_all_ordered_by_name(self, repo, db):
        _insert_context(db, "id-b", "Beta", LONDON_LAT, LONDON_LON)
        _insert_context(db, "id-a", "Alpha", LONDON_LAT + 0.01, LONDON_LON)

        result = await repo.list_all()
        assert len(result) == 2
        assert result[0].name == "Alpha"
        assert result[1].name == "Beta"

    @pytest.mark.asyncio
    async def test_returns_only_current_users_contexts(self, repo, db):
        db.execute(
            "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("other", "o@example.com", "Other", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()
        _insert_context(db, "mine", "Mine", LONDON_LAT, LONDON_LON, user_id=USER_ID)
        _insert_context(db, "theirs", "Theirs", FAR_LAT, FAR_LON, user_id="other")

        result = await repo.list_all()
        assert len(result) == 1
        assert result[0].id == "mine"


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_get_existing_context(self, repo, db):
        _insert_context(db, "ctx-1", "Office", LONDON_LAT, LONDON_LON, radius=200.0)

        ctx = await repo.get("ctx-1")
        assert ctx.id == "ctx-1"
        assert ctx.name == "Office"
        assert ctx.latitude == pytest.approx(LONDON_LAT)
        assert ctx.radius == 200.0

    @pytest.mark.asyncio
    async def test_get_raises_when_not_found(self, repo):
        with pytest.raises(ValueError, match="Context not found"):
            await repo.get("ghost")

    @pytest.mark.asyncio
    async def test_get_raises_for_other_users_context(self, repo, db):
        db.execute(
            "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("other2", "o2@example.com", "Other2", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()
        _insert_context(db, "foreign-ctx", "Foreign", FAR_LAT, FAR_LON, user_id="other2")

        with pytest.raises(ValueError):
            await repo.get("foreign-ctx")


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_context_with_id(self, repo):
        ctx = await repo.create(
            LocationContextCreate(name="Home", latitude=LONDON_LAT, longitude=LONDON_LON, radius=150.0)
        )
        assert ctx.name == "Home"
        assert ctx.latitude == pytest.approx(LONDON_LAT)
        assert ctx.radius == 150.0
        assert ctx.id

    @pytest.mark.asyncio
    async def test_create_persists_to_db(self, repo, db):
        await repo.create(
            LocationContextCreate(name="Gym", latitude=51.0, longitude=-0.5, radius=100.0)
        )
        cursor = db.execute("SELECT * FROM contexts WHERE name = ?", ("Gym",))
        assert cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_create_uses_default_radius_when_not_provided(self, repo, db):
        ctx = await repo.create(
            LocationContextCreate(name="Park", latitude=51.0, longitude=-0.5)
        )
        assert ctx.radius == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_create_multiple_contexts(self, repo):
        c1 = await repo.create(LocationContextCreate(name="A", latitude=1.0, longitude=1.0))
        c2 = await repo.create(LocationContextCreate(name="B", latitude=2.0, longitude=2.0))
        assert c1.id != c2.id


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_true(self, repo, db):
        _insert_context(db, "del-ctx", "ToRemove", LONDON_LAT, LONDON_LON)
        result = await repo.delete("del-ctx")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_removes_from_db(self, repo, db):
        _insert_context(db, "del-ctx2", "Gone", LONDON_LAT, LONDON_LON)
        await repo.delete("del-ctx2")
        cursor = db.execute("SELECT * FROM contexts WHERE id = ?", ("del-ctx2",))
        assert cursor.fetchone() is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_true(self, repo):
        assert await repo.delete("no-such-id") is True

    @pytest.mark.asyncio
    async def test_delete_does_not_affect_other_contexts(self, repo, db):
        _insert_context(db, "keep-ctx", "Keep", LONDON_LAT, LONDON_LON)
        _insert_context(db, "rm-ctx", "Remove", FAR_LAT, FAR_LON)

        await repo.delete("rm-ctx")
        remaining = await repo.list_all()
        assert len(remaining) == 1
        assert remaining[0].id == "keep-ctx"


# ---------------------------------------------------------------------------
# get_available
# ---------------------------------------------------------------------------


class TestGetAvailable:
    @pytest.mark.asyncio
    async def test_returns_context_when_within_radius(self, repo, db):
        # Insert London context with 10km radius
        _insert_context(db, "london", "London", LONDON_LAT, LONDON_LON, radius=10_000.0)

        # NEARBY_LAT/LON is just ~100m away
        result = await repo.get_available(NEARBY_LAT, NEARBY_LON)

        assert len(result) == 1
        assert result[0].id == "london"

    @pytest.mark.asyncio
    async def test_excludes_context_outside_radius(self, repo, db):
        # Insert London context with tight 50m radius
        _insert_context(db, "london-tight", "London Tight", LONDON_LAT, LONDON_LON, radius=50.0)

        # Paris is ~340km away
        result = await repo.get_available(FAR_LAT, FAR_LON)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_contexts(self, repo):
        result = await repo.get_available(LONDON_LAT, LONDON_LON)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_matching_contexts(self, repo, db):
        _insert_context(db, "big-area", "Big Area", LONDON_LAT, LONDON_LON, radius=100_000.0)
        _insert_context(db, "exact-match", "Exact", NEARBY_LAT, NEARBY_LON, radius=1_000.0)

        result = await repo.get_available(NEARBY_LAT, NEARBY_LON)
        ids = {c.id for c in result}
        assert "big-area" in ids
        assert "exact-match" in ids

    @pytest.mark.asyncio
    async def test_excludes_other_users_contexts(self, repo, db):
        """get_available must only consider contexts owned by the current user."""
        db.execute(
            "INSERT INTO users (id, email, name, timezone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("user-other", "o@example.com", "Other", "UTC", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
        )
        db.commit()
        # Other user's context at our exact location
        _insert_context(db, "other-ctx", "Other's", LONDON_LAT, LONDON_LON, radius=100_000.0, user_id="user-other")

        result = await repo.get_available(LONDON_LAT, LONDON_LON)
        assert result == []

    @pytest.mark.asyncio
    async def test_context_exactly_on_boundary(self, repo, db):
        """A context whose radius equals the distance should be included."""
        from todopro_cli.adapters.sqlite.utils import haversine_distance

        # Calculate exact distance between London and Nearby
        dist = haversine_distance(LONDON_LAT, LONDON_LON, NEARBY_LAT, NEARBY_LON)

        # Insert context with radius exactly equal to that distance
        _insert_context(db, "boundary", "Boundary", LONDON_LAT, LONDON_LON, radius=dist)

        result = await repo.get_available(NEARBY_LAT, NEARBY_LON)
        assert len(result) == 1
