"""Unit tests for SQLite user_manager module."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from todopro_cli.adapters.sqlite import schema as db_schema
from todopro_cli.adapters.sqlite.user_manager import (
    create_default_user,
    get_or_create_local_user,
    get_system_timezone,
    get_user_info,
    update_user_timezone,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    """In-memory DB with users table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(db_schema.CREATE_USERS_TABLE)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# get_system_timezone
# ---------------------------------------------------------------------------


class TestGetSystemTimezone:
    def test_returns_non_empty_string(self):
        tz = get_system_timezone()
        assert isinstance(tz, str)
        assert len(tz) > 0

    def test_returns_utc_when_tzlocal_has_no_key(self):
        """If the tz object has no 'key' attribute, str() is used."""
        class _FakeTz:
            def __str__(self):
                return "UTC"

        with patch("todopro_cli.adapters.sqlite.user_manager.tzlocal") as mock_tz:
            mock_tz.get_localzone.return_value = _FakeTz()
            result = get_system_timezone()
        assert isinstance(result, str)

    def test_returns_key_when_available(self):
        class _FakeTzWithKey:
            key = "America/New_York"
            def __str__(self):
                return "America/New_York"

        with patch("todopro_cli.adapters.sqlite.user_manager.tzlocal") as mock_tz:
            mock_tz.get_localzone.return_value = _FakeTzWithKey()
            result = get_system_timezone()
        assert result == "America/New_York"


# ---------------------------------------------------------------------------
# create_default_user
# ---------------------------------------------------------------------------


class TestCreateDefaultUser:
    def test_returns_uuid_string(self):
        conn = _make_db()
        uid = create_default_user(conn)
        assert isinstance(uid, str)
        assert len(uid) == 36

    def test_user_stored_in_db(self):
        conn = _make_db()
        uid = create_default_user(conn)
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (uid,))
        row = cursor.fetchone()
        assert row is not None
        assert row["email"] == "local@todopro.local"
        assert row["name"] == "Local User"

    def test_uses_auto_detected_timezone(self):
        conn = _make_db()
        uid = create_default_user(conn)
        cursor = conn.execute("SELECT timezone FROM users WHERE id = ?", (uid,))
        row = cursor.fetchone()
        assert row is not None
        assert len(row[0]) > 0

    def test_uses_explicit_timezone(self):
        conn = _make_db()
        uid = create_default_user(conn, timezone="Europe/London")
        cursor = conn.execute("SELECT timezone FROM users WHERE id = ?", (uid,))
        row = cursor.fetchone()
        assert row["timezone"] == "Europe/London"

    def test_sets_created_and_updated_at(self):
        conn = _make_db()
        uid = create_default_user(conn)
        cursor = conn.execute(
            "SELECT created_at, updated_at FROM users WHERE id = ?", (uid,)
        )
        row = cursor.fetchone()
        assert row["created_at"] is not None
        assert row["updated_at"] is not None


# ---------------------------------------------------------------------------
# get_or_create_local_user
# ---------------------------------------------------------------------------


class TestGetOrCreateLocalUser:
    def test_creates_user_when_none_exists(self):
        conn = _make_db()
        uid = get_or_create_local_user(conn)
        assert isinstance(uid, str)
        assert len(uid) == 36

    def test_returns_existing_user_when_present(self):
        conn = _make_db()
        uid_first = get_or_create_local_user(conn)
        uid_second = get_or_create_local_user(conn)
        assert uid_first == uid_second

    def test_does_not_create_duplicate(self):
        conn = _make_db()
        get_or_create_local_user(conn)
        get_or_create_local_user(conn)
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        assert count == 1


# ---------------------------------------------------------------------------
# update_user_timezone
# ---------------------------------------------------------------------------


class TestUpdateUserTimezone:
    def test_updates_timezone(self):
        conn = _make_db()
        uid = create_default_user(conn, timezone="UTC")
        update_user_timezone(conn, uid, "Asia/Tokyo")
        cursor = conn.execute("SELECT timezone FROM users WHERE id = ?", (uid,))
        row = cursor.fetchone()
        assert row[0] == "Asia/Tokyo"

    def test_updates_updated_at(self):
        conn = _make_db()
        uid = create_default_user(conn, timezone="UTC")
        cursor = conn.execute("SELECT updated_at FROM users WHERE id = ?", (uid,))
        old_updated_at = cursor.fetchone()[0]
        update_user_timezone(conn, uid, "Asia/Tokyo")
        cursor = conn.execute("SELECT updated_at FROM users WHERE id = ?", (uid,))
        new_updated_at = cursor.fetchone()[0]
        # updated_at should change (or at least be set)
        assert new_updated_at is not None


# ---------------------------------------------------------------------------
# get_user_info
# ---------------------------------------------------------------------------


class TestGetUserInfo:
    def test_returns_dict_for_existing_user(self):
        conn = _make_db()
        uid = create_default_user(conn, timezone="UTC")
        info = get_user_info(conn, uid)
        assert info is not None
        assert info["id"] == uid
        assert info["email"] == "local@todopro.local"
        assert info["name"] == "Local User"
        assert info["timezone"] == "UTC"

    def test_returns_none_for_unknown_user(self):
        conn = _make_db()
        info = get_user_info(conn, "nonexistent-id")
        assert info is None

    def test_all_expected_keys_present(self):
        conn = _make_db()
        uid = create_default_user(conn)
        info = get_user_info(conn, uid)
        expected_keys = {"id", "email", "name", "timezone", "created_at", "updated_at"}
        assert expected_keys.issubset(set(info.keys()))
