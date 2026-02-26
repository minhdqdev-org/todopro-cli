"""Unit tests for SQLite adapter utility functions."""

from __future__ import annotations

import math
import sqlite3
from datetime import UTC, datetime, timezone

import pytest

from todopro_cli.adapters.sqlite.utils import (
    build_update_clause,
    build_where_clause,
    generate_uuid,
    haversine_distance,
    is_soft_deleted,
    now_iso,
    parse_datetime,
    row_to_dict,
)


class TestGenerateUuid:
    def test_returns_string(self):
        result = generate_uuid()
        assert isinstance(result, str)

    def test_returns_uuid_format(self):
        result = generate_uuid()
        assert len(result) == 36
        parts = result.split("-")
        assert len(parts) == 5

    def test_returns_unique_values(self):
        ids = {generate_uuid() for _ in range(100)}
        assert len(ids) == 100


class TestNowIso:
    def test_returns_string(self):
        result = now_iso()
        assert isinstance(result, str)

    def test_parseable_as_datetime(self):
        result = now_iso()
        dt = datetime.fromisoformat(result)
        assert dt.tzinfo is not None

    def test_close_to_current_time(self):
        before = datetime.now(UTC)
        result = now_iso()
        after = datetime.now(UTC)
        dt = datetime.fromisoformat(result)
        assert before <= dt <= after


class TestHaversineDistance:
    def test_same_point_is_zero(self):
        dist = haversine_distance(0.0, 0.0, 0.0, 0.0)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_known_distance_london_paris(self):
        # London: 51.5074, -0.1278 / Paris: 48.8566, 2.3522
        # Approximate distance ~340 km
        dist = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
        assert 330_000 < dist < 350_000

    def test_returns_float(self):
        dist = haversine_distance(0.0, 0.0, 1.0, 0.0)
        assert isinstance(dist, float)

    def test_symmetry(self):
        d1 = haversine_distance(10.0, 20.0, 30.0, 40.0)
        d2 = haversine_distance(30.0, 40.0, 10.0, 20.0)
        assert d1 == pytest.approx(d2, rel=1e-10)

    def test_one_degree_latitude_roughly_111km(self):
        # 1° latitude ≈ 111 km
        dist = haversine_distance(0.0, 0.0, 1.0, 0.0)
        assert 110_000 < dist < 112_000


class TestRowToDict:
    def test_none_returns_empty_dict(self):
        assert row_to_dict(None) == {}

    def test_sqlite_row_converted(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE t (a INTEGER, b TEXT)")
        conn.execute("INSERT INTO t VALUES (1, 'hello')")
        row = conn.execute("SELECT * FROM t").fetchone()
        result = row_to_dict(row)
        assert result == {"a": 1, "b": "hello"}
        conn.close()

    def test_dict_passthrough(self):
        d = {"key": "value", "num": 42}
        assert row_to_dict(d) == d


class TestParseDatetime:
    def test_none_returns_none(self):
        assert parse_datetime(None) is None

    def test_datetime_passthrough(self):
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        result = parse_datetime(dt)
        assert result is dt

    def test_iso_string_parsed(self):
        iso = "2024-01-15T12:00:00+00:00"
        result = parse_datetime(iso)
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_z_suffix_normalized(self):
        iso_z = "2024-06-01T10:30:00Z"
        result = parse_datetime(iso_z)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_non_str_non_datetime_returns_none(self):
        result = parse_datetime(12345)  # type: ignore[arg-type]
        assert result is None


class TestBuildWhereClause:
    def test_empty_filters_returns_true(self):
        clause, params = build_where_clause({})
        assert clause == "1=1"
        assert params == []

    def test_none_values_excluded(self):
        clause, params = build_where_clause({"user_id": None, "project_id": None})
        assert clause == "1=1"
        assert params == []

    def test_single_filter(self):
        clause, params = build_where_clause({"user_id": "u1"})
        assert "user_id = ?" in clause
        assert params == ["u1"]

    def test_multiple_filters(self):
        filters = {"user_id": "u1", "project_id": "p1"}
        clause, params = build_where_clause(filters)
        assert "user_id = ?" in clause
        assert "project_id = ?" in clause
        assert " AND " in clause
        assert "u1" in params
        assert "p1" in params

    def test_mixed_none_and_value(self):
        clause, params = build_where_clause({"user_id": "u1", "project_id": None})
        assert "user_id = ?" in clause
        assert "project_id" not in clause
        assert params == ["u1"]


class TestBuildUpdateClause:
    def test_empty_updates_returns_empty_string(self):
        clause, params = build_update_clause({})
        assert clause == ""
        assert params == []

    def test_none_values_excluded(self):
        clause, params = build_update_clause({"name": None, "color": None})
        assert clause == ""
        assert params == []

    def test_single_update(self):
        clause, params = build_update_clause({"name": "Test"})
        assert "name = ?" in clause
        assert params == ["Test"]

    def test_multiple_updates(self):
        updates = {"name": "New Name", "color": "#ff0000"}
        clause, params = build_update_clause(updates)
        assert "name = ?" in clause
        assert "color = ?" in clause
        assert "New Name" in params
        assert "#ff0000" in params

    def test_mixed_none_and_value(self):
        clause, params = build_update_clause({"name": "Keep", "color": None})
        assert "name = ?" in clause
        assert "color" not in clause
        assert params == ["Keep"]


class TestIsSoftDeleted:
    def test_not_deleted_when_no_key(self):
        assert is_soft_deleted({}) is False

    def test_not_deleted_when_none(self):
        assert is_soft_deleted({"deleted_at": None}) is False

    def test_deleted_when_value_present(self):
        assert is_soft_deleted({"deleted_at": "2024-01-01T00:00:00"}) is True

    def test_deleted_when_any_truthy_value(self):
        assert is_soft_deleted({"deleted_at": "some-timestamp"}) is True
