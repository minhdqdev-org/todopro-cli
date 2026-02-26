"""Unit tests for todopro_cli/models/integrations.py.

All models are Pydantic BaseModel subclasses, so tests focus on:
- Field defaults
- Optional vs required fields
- Type coercion / validation
- Dict / JSON round-trips
"""

from __future__ import annotations

import pytest

from todopro_cli.models.integrations import (
    GitHubDeviceAuth,
    GitHubProject,
    GitHubStatus,
    GoogleAuthUrl,
    GoogleCalendar,
    GoogleStatus,
    ProjectLink,
    SyncState,
    SyncStats,
)


# ---------------------------------------------------------------------------
# GitHubStatus
# ---------------------------------------------------------------------------


class TestGitHubStatus:
    def test_connected_true_with_all_fields(self):
        status = GitHubStatus(
            connected=True,
            username="octocat",
            scopes="repo,user",
            connected_at="2024-01-01T00:00:00Z",
        )
        assert status.connected is True
        assert status.username == "octocat"
        assert status.scopes == "repo,user"
        assert status.connected_at == "2024-01-01T00:00:00Z"

    def test_connected_false_minimal(self):
        status = GitHubStatus(connected=False)
        assert status.connected is False
        assert status.username is None
        assert status.scopes is None
        assert status.connected_at is None

    def test_optional_fields_default_to_none(self):
        status = GitHubStatus(connected=True)
        assert status.username is None
        assert status.scopes is None
        assert status.connected_at is None

    def test_serialises_to_dict(self):
        status = GitHubStatus(connected=True, username="me")
        d = status.model_dump()
        assert d["connected"] is True
        assert d["username"] == "me"


# ---------------------------------------------------------------------------
# GitHubDeviceAuth
# ---------------------------------------------------------------------------


class TestGitHubDeviceAuth:
    def test_all_required_fields(self):
        auth = GitHubDeviceAuth(
            device_code="dev123",
            user_code="USER-CODE",
            verification_uri="https://github.com/login/device",
        )
        assert auth.device_code == "dev123"
        assert auth.user_code == "USER-CODE"
        assert auth.verification_uri == "https://github.com/login/device"

    def test_default_expires_in(self):
        auth = GitHubDeviceAuth(
            device_code="d", user_code="u", verification_uri="https://example.com"
        )
        assert auth.expires_in == 900

    def test_default_interval(self):
        auth = GitHubDeviceAuth(
            device_code="d", user_code="u", verification_uri="https://example.com"
        )
        assert auth.interval == 5

    def test_custom_expires_and_interval(self):
        auth = GitHubDeviceAuth(
            device_code="d",
            user_code="u",
            verification_uri="https://example.com",
            expires_in=1800,
            interval=10,
        )
        assert auth.expires_in == 1800
        assert auth.interval == 10

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            GitHubDeviceAuth(device_code="d", user_code="u")  # missing verification_uri


# ---------------------------------------------------------------------------
# GitHubProject
# ---------------------------------------------------------------------------


class TestGitHubProject:
    def test_required_fields(self):
        project = GitHubProject(id="proj-1", title="My Project")
        assert project.id == "proj-1"
        assert project.title == "My Project"
        assert project.number is None

    def test_with_number(self):
        project = GitHubProject(id="proj-2", number=42, title="Numbered Project")
        assert project.number == 42

    def test_serialises_to_dict(self):
        project = GitHubProject(id="p", title="T")
        d = project.model_dump()
        assert "id" in d
        assert "title" in d
        assert "number" in d


# ---------------------------------------------------------------------------
# ProjectLink
# ---------------------------------------------------------------------------


class TestProjectLink:
    def test_all_fields_required(self):
        link = ProjectLink(
            id=1,
            todopro_project_id="tp-001",
            external_id="gh-42",
            external_name="GitHub Project",
            sync_direction="bidirectional",
        )
        assert link.id == 1
        assert link.todopro_project_id == "tp-001"
        assert link.external_id == "gh-42"
        assert link.external_name == "GitHub Project"
        assert link.sync_direction == "bidirectional"

    def test_serialises_to_dict(self):
        link = ProjectLink(
            id=2,
            todopro_project_id="tp-002",
            external_id="ext-99",
            external_name="Ext",
            sync_direction="one_way",
        )
        d = link.model_dump()
        assert d["id"] == 2
        assert d["sync_direction"] == "one_way"


# ---------------------------------------------------------------------------
# GoogleStatus
# ---------------------------------------------------------------------------


class TestGoogleStatus:
    def test_connected_with_email(self):
        status = GoogleStatus(connected=True, email="user@gmail.com")
        assert status.email == "user@gmail.com"

    def test_not_connected_minimal(self):
        status = GoogleStatus(connected=False)
        assert status.connected is False
        assert status.email is None

    def test_all_fields(self):
        status = GoogleStatus(
            connected=True,
            email="a@b.com",
            scopes="calendar",
            connected_at="2024-06-01T00:00:00Z",
        )
        assert status.scopes == "calendar"
        assert status.connected_at == "2024-06-01T00:00:00Z"


# ---------------------------------------------------------------------------
# GoogleAuthUrl
# ---------------------------------------------------------------------------


class TestGoogleAuthUrl:
    def test_auth_url_stored(self):
        obj = GoogleAuthUrl(auth_url="https://accounts.google.com/o/oauth2/auth?foo=bar")
        assert "google.com" in obj.auth_url

    def test_serialises_to_dict(self):
        obj = GoogleAuthUrl(auth_url="https://example.com")
        assert obj.model_dump() == {"auth_url": "https://example.com"}


# ---------------------------------------------------------------------------
# GoogleCalendar
# ---------------------------------------------------------------------------


class TestGoogleCalendar:
    def test_required_fields(self):
        cal = GoogleCalendar(id="cal-1", summary="Work Calendar")
        assert cal.id == "cal-1"
        assert cal.summary == "Work Calendar"

    def test_optional_fields_default(self):
        cal = GoogleCalendar(id="c", summary="S")
        assert cal.timeZone is None
        assert cal.primary is False

    def test_primary_calendar(self):
        cal = GoogleCalendar(id="primary", summary="Primary", primary=True, timeZone="UTC")
        assert cal.primary is True
        assert cal.timeZone == "UTC"


# ---------------------------------------------------------------------------
# SyncStats
# ---------------------------------------------------------------------------


class TestSyncStats:
    def test_defaults_are_zero(self):
        stats = SyncStats()
        assert stats.created == 0
        assert stats.updated == 0
        assert stats.skipped == 0

    def test_custom_values(self):
        stats = SyncStats(created=5, updated=3, skipped=1)
        assert stats.created == 5
        assert stats.updated == 3
        assert stats.skipped == 1

    def test_serialises_to_dict(self):
        stats = SyncStats(created=2, updated=1, skipped=0)
        d = stats.model_dump()
        assert d == {"created": 2, "updated": 1, "skipped": 0}


# ---------------------------------------------------------------------------
# SyncState
# ---------------------------------------------------------------------------


class TestSyncState:
    def test_defaults(self):
        state = SyncState()
        assert state.last_synced_at is None
        assert state.stats == {}

    def test_with_last_synced_at(self):
        state = SyncState(last_synced_at="2024-01-01T12:00:00Z")
        assert state.last_synced_at == "2024-01-01T12:00:00Z"

    def test_with_stats_dict(self):
        state = SyncState(
            last_synced_at="2024-01-01T00:00:00Z",
            stats={"tasks": {"created": 3, "updated": 1}},
        )
        assert state.stats["tasks"]["created"] == 3

    def test_serialises_round_trip(self):
        state = SyncState(last_synced_at="2024-06-01T00:00:00Z", stats={"k": "v"})
        d = state.model_dump()
        restored = SyncState(**d)
        assert restored.last_synced_at == state.last_synced_at
        assert restored.stats == state.stats
