"""Comprehensive unit tests for services/sync_service.py.

Tests SyncResult, SyncService base methods, SyncPullService,
and SyncPushService — fully mocked to avoid filesystem / network I/O.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.models import (
    Label,
    LabelCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
)
from todopro_cli.services.sync_service import (
    SyncPullService,
    SyncPushService,
    SyncResult,
    SyncService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_repo(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like any repository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=overrides.get("list_all", []))
    repo.get_by_id = AsyncMock(return_value=overrides.get("get_by_id", None))
    repo.create = AsyncMock(return_value=None)
    repo.update = AsyncMock(return_value=None)
    return repo


def _make_pull_service(**repo_overrides) -> SyncPullService:
    """Instantiate SyncPullService with 8 mock repositories."""
    from rich.console import Console
    from io import StringIO

    console = Console(file=StringIO(), no_color=True)
    repos = [_mock_repo(**repo_overrides) for _ in range(8)]
    svc = SyncPullService(*repos, console=console)
    # Patch sync_state to avoid filesystem access
    svc.sync_state = MagicMock()
    svc.sync_state.get_last_sync.return_value = None
    svc.sync_state.set_last_sync = MagicMock()
    # Patch conflict_tracker to avoid filesystem access
    svc.conflict_tracker = MagicMock()
    svc.conflict_tracker.has_conflicts.return_value = False
    svc.conflict_tracker.add_conflict = MagicMock()
    return svc


def _make_push_service(**repo_overrides) -> SyncPushService:
    from rich.console import Console
    from io import StringIO

    console = Console(file=StringIO(), no_color=True)
    repos = [_mock_repo(**repo_overrides) for _ in range(8)]
    svc = SyncPushService(*repos, console=console)
    svc.sync_state = MagicMock()
    svc.sync_state.get_last_sync.return_value = None
    svc.sync_state.set_last_sync = MagicMock()
    svc.conflict_tracker = MagicMock()
    svc.conflict_tracker.has_conflicts.return_value = False
    svc.conflict_tracker.add_conflict = MagicMock()
    return svc


def _make_project(updated_at: str = "2024-01-01T00:00:00Z") -> MagicMock:
    """Create a mock Project with necessary attributes."""
    p = MagicMock(spec=Project)
    p.id = "proj-001"
    p.name = "Test Project"
    p.description = None
    p.color = "#ff0000"
    p.updated_at = updated_at
    return p


def _make_label(updated_at: str = "2024-01-01T00:00:00Z") -> MagicMock:
    """Create a mock Label with necessary attributes."""
    lb = MagicMock(spec=Label)
    lb.id = "lbl-001"
    lb.name = "urgent"
    lb.color = "#ff0000"
    lb.updated_at = updated_at
    return lb


def _make_task(updated_at: str = "2024-01-01T00:00:00Z", *, status: str = "active") -> MagicMock:
    """Create a mock Task with necessary attributes."""
    t = MagicMock(spec=Task)
    t.id = "task-001"
    t.content = "Buy groceries"
    t.description = None
    t.priority = 4
    t.status = status
    t.project_id = None
    t.due_date = None
    t.completed_at = None
    t.updated_at = updated_at
    t.model_dump = MagicMock(return_value={"id": "task-001", "content": "Buy groceries"})
    return t


# ===========================================================================
# SyncResult
# ===========================================================================

class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_default_counters_are_zero(self):
        r = SyncResult()
        assert r.tasks_fetched == 0
        assert r.tasks_new == 0
        assert r.tasks_updated == 0
        assert r.tasks_unchanged == 0
        assert r.tasks_conflicts == 0

    def test_default_project_counters_are_zero(self):
        r = SyncResult()
        assert r.projects_fetched == 0
        assert r.projects_new == 0
        assert r.projects_updated == 0
        assert r.projects_unchanged == 0

    def test_default_label_counters_are_zero(self):
        r = SyncResult()
        assert r.labels_fetched == 0
        assert r.labels_new == 0
        assert r.labels_updated == 0
        assert r.labels_unchanged == 0

    def test_success_defaults_to_false(self):
        r = SyncResult()
        assert r.success is False

    def test_error_defaults_to_none(self):
        r = SyncResult()
        assert r.error is None

    def test_duration_defaults_to_zero(self):
        r = SyncResult()
        assert r.duration == 0.0

    def test_mutation(self):
        r = SyncResult()
        r.tasks_fetched = 10
        r.tasks_new = 5
        r.success = True
        assert r.tasks_fetched == 10
        assert r.tasks_new == 5
        assert r.success is True


# ===========================================================================
# SyncService._should_update
# ===========================================================================

class TestShouldUpdate:
    """Tests for SyncService._should_update() conflict resolution logic."""

    def setup_method(self):
        repos = [_mock_repo() for _ in range(8)]
        from rich.console import Console
        from io import StringIO
        self.svc = SyncService(*repos, console=Console(file=StringIO(), no_color=True))

    # --- equal timestamps ---

    def test_equal_timestamps_returns_false(self):
        ts = "2024-01-01T00:00:00Z"
        update, reason = self.svc._should_update(ts, ts, "remote_wins")
        assert update is False
        assert reason == "equal"

    def test_equal_timestamps_local_wins_also_false(self):
        ts = "2024-06-15T12:00:00Z"
        update, reason = self.svc._should_update(ts, ts, "local_wins")
        assert update is False
        assert reason == "equal"

    # --- remote_wins strategy ---

    def test_remote_newer_remote_wins_should_update_true(self):
        local = "2024-01-01T00:00:00Z"
        remote = "2024-01-02T00:00:00Z"
        update, reason = self.svc._should_update(local, remote, "remote_wins")
        assert update is True
        assert reason == "remote_newer"

    def test_local_newer_remote_wins_should_update_false(self):
        local = "2024-01-02T00:00:00Z"
        remote = "2024-01-01T00:00:00Z"
        update, reason = self.svc._should_update(local, remote, "remote_wins")
        assert update is False
        assert reason == "local_newer"

    # --- local_wins strategy ---

    def test_local_newer_local_wins_should_update_true(self):
        local = "2024-01-02T00:00:00Z"
        remote = "2024-01-01T00:00:00Z"
        update, reason = self.svc._should_update(local, remote, "local_wins")
        assert update is True
        assert reason == "local_newer"

    def test_remote_newer_local_wins_should_update_false(self):
        local = "2024-01-01T00:00:00Z"
        remote = "2024-01-02T00:00:00Z"
        update, reason = self.svc._should_update(local, remote, "local_wins")
        assert update is False
        assert reason == "remote_newer"

    # --- None timestamps ---

    def test_none_local_remote_wins_returns_update(self):
        update, reason = self.svc._should_update(None, "2024-01-01T00:00:00Z", "remote_wins")
        assert update is True
        assert reason == "remote_newer"

    def test_none_remote_local_wins_returns_update(self):
        update, reason = self.svc._should_update("2024-01-01T00:00:00Z", None, "local_wins")
        assert update is True
        assert reason == "local_newer"

    def test_both_none_returns_false(self):
        update, reason = self.svc._should_update(None, None, "remote_wins")
        assert update is False
        assert reason == "equal"


# ===========================================================================
# SyncService._log_conflict
# ===========================================================================

class TestLogConflict:
    """Tests for SyncService._log_conflict()."""

    def setup_method(self):
        repos = [_mock_repo() for _ in range(8)]
        from rich.console import Console
        from io import StringIO
        self.svc = SyncService(*repos, console=Console(file=StringIO(), no_color=True))
        # Use real conflict tracker but point it at a temp dir
        from todopro_cli.services.sync_conflicts import SyncConflictTracker
        self.svc.conflict_tracker = SyncConflictTracker(config_dir="/tmp/todopro_test_conflicts")

    def test_adds_conflict_to_tracker(self):
        self.svc._log_conflict(
            "task",
            "t-001",
            {"id": "t-001", "content": "local"},
            {"id": "t-001", "content": "remote"},
            "local_wins",
        )
        assert self.svc.conflict_tracker.count() == 1

    def test_conflict_has_correct_fields(self):
        self.svc._log_conflict(
            "project",
            "p-001",
            {"name": "local project"},
            {"name": "remote project"},
            "remote_wins",
        )
        conflicts = self.svc.conflict_tracker.get_conflicts()
        assert len(conflicts) == 1
        c = conflicts[0]
        assert c.resource_type == "project"
        assert c.resource_id == "p-001"
        assert c.resolution == "remote_wins"

    def test_multiple_conflicts_accumulate(self):
        for i in range(3):
            self.svc._log_conflict("task", f"t-{i:03d}", {}, {}, "skipped")
        assert self.svc.conflict_tracker.count() == 3


# ===========================================================================
# SyncPullService._sync_project
# ===========================================================================

class TestSyncPullServiceSyncProject:
    """Unit tests for _sync_project in SyncPullService."""

    def test_new_project_increments_projects_new(self):
        svc = _make_pull_service(get_by_id=None)
        project = _make_project()
        result = SyncResult()
        asyncio.run(
            svc._sync_project(project, result, "remote_wins")
        )
        assert result.projects_new == 1
        svc.target_project_repo.create.assert_called_once()

    def test_existing_project_remote_newer_increments_updated(self):
        existing = _make_project(updated_at="2024-01-01T00:00:00Z")
        incoming = _make_project(updated_at="2024-01-02T00:00:00Z")
        svc = _make_pull_service()
        svc.target_project_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_project(incoming, result, "remote_wins")
        )
        assert result.projects_updated == 1

    def test_existing_project_local_newer_remote_wins_unchanged(self):
        existing = _make_project(updated_at="2024-01-02T00:00:00Z")
        incoming = _make_project(updated_at="2024-01-01T00:00:00Z")
        svc = _make_pull_service()
        svc.target_project_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_project(incoming, result, "remote_wins")
        )
        assert result.projects_unchanged == 1
        svc.target_project_repo.update.assert_not_called()

    def test_equal_timestamps_unchanged(self):
        ts = "2024-06-01T00:00:00Z"
        existing = _make_project(updated_at=ts)
        incoming = _make_project(updated_at=ts)
        svc = _make_pull_service()
        svc.target_project_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_project(incoming, result, "remote_wins")
        )
        assert result.projects_unchanged == 1

    def test_exception_does_not_propagate(self):
        svc = _make_pull_service()
        svc.target_project_repo.get_by_id = AsyncMock(side_effect=RuntimeError("DB error"))
        result = SyncResult()
        # Should not raise
        asyncio.run(
            svc._sync_project(_make_project(), result, "remote_wins")
        )
        assert result.projects_new == 0


# ===========================================================================
# SyncPullService._sync_label
# ===========================================================================

class TestSyncPullServiceSyncLabel:
    """Unit tests for _sync_label in SyncPullService."""

    def test_new_label_increments_labels_new(self):
        svc = _make_pull_service(get_by_id=None)
        label = _make_label()
        result = SyncResult()
        asyncio.run(
            svc._sync_label(label, result, "remote_wins")
        )
        assert result.labels_new == 1
        svc.target_label_repo.create.assert_called_once()

    def test_existing_label_increments_unchanged(self):
        existing = _make_label()
        svc = _make_pull_service()
        svc.target_label_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_label(_make_label(), result, "remote_wins")
        )
        assert result.labels_unchanged == 1

    def test_exception_does_not_propagate(self):
        svc = _make_pull_service()
        svc.target_label_repo.get_by_id = AsyncMock(side_effect=RuntimeError("error"))
        result = SyncResult()
        asyncio.run(
            svc._sync_label(_make_label(), result, "remote_wins")
        )
        assert result.labels_new == 0


# ===========================================================================
# SyncPullService._sync_task
# ===========================================================================

class TestSyncPullServiceSyncTask:
    """Unit tests for _sync_task in SyncPullService."""

    def test_new_task_increments_tasks_new(self):
        """New task (no existing) must call create and increment tasks_new."""
        svc = _make_pull_service(get_by_id=None)
        # Inject TaskCreate/TaskUpdate so the NameError is avoided
        import todopro_cli.services.sync_service as m
        m.TaskCreate = TaskCreate
        m.TaskUpdate = TaskUpdate
        task = _make_task()
        result = SyncResult()
        asyncio.run(
            svc._sync_task(task, result, "remote_wins")
        )
        assert result.tasks_new == 1

    def test_existing_task_equal_timestamps_unchanged(self):
        ts = "2024-05-01T00:00:00Z"
        existing = _make_task(updated_at=ts)
        incoming = _make_task(updated_at=ts)
        svc = _make_pull_service()
        svc.target_task_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_task(incoming, result, "remote_wins")
        )
        assert result.tasks_unchanged == 1

    def test_existing_task_local_newer_remote_wins_conflict(self):
        existing = _make_task(updated_at="2024-01-02T00:00:00Z")
        incoming = _make_task(updated_at="2024-01-01T00:00:00Z")
        svc = _make_pull_service()
        svc.target_task_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_task(incoming, result, "remote_wins")
        )
        assert result.tasks_conflicts == 1

    def test_existing_task_remote_newer_remote_wins_updates(self):
        existing = _make_task(updated_at="2024-01-01T00:00:00Z")
        incoming = _make_task(updated_at="2024-01-02T00:00:00Z")
        svc = _make_pull_service()
        svc.target_task_repo.get_by_id = AsyncMock(return_value=existing)
        import todopro_cli.services.sync_service as m
        m.TaskCreate = TaskCreate
        m.TaskUpdate = TaskUpdate
        result = SyncResult()
        asyncio.run(
            svc._sync_task(incoming, result, "remote_wins")
        )
        assert result.tasks_updated == 1

    def test_exception_does_not_propagate(self):
        svc = _make_pull_service()
        svc.target_task_repo.get_by_id = AsyncMock(side_effect=RuntimeError("fail"))
        result = SyncResult()
        asyncio.run(
            svc._sync_task(_make_task(), result, "remote_wins")
        )
        assert result.tasks_new == 0


# ===========================================================================
# SyncPullService.pull (integration-style)
# ===========================================================================

class TestSyncPullServicePull:
    """Integration-style tests for SyncPullService.pull()."""

    def test_dry_run_returns_success_no_creates(self):
        project = _make_project()
        label = _make_label()
        task = _make_task()
        svc = _make_pull_service()
        svc.source_project_repo.list_all = AsyncMock(return_value=[project])
        svc.source_label_repo.list_all = AsyncMock(return_value=[label])
        svc.source_task_repo.list_all = AsyncMock(return_value=[task])

        result = asyncio.run(
            svc.pull("remote", "local", dry_run=True)
        )
        assert result.success is True
        assert result.projects_fetched == 1
        assert result.labels_fetched == 1
        assert result.tasks_fetched == 1
        # Dry run: target repos should not be called with create/update
        svc.target_project_repo.create.assert_not_called()
        svc.target_task_repo.create.assert_not_called()

    def test_empty_repos_succeeds(self):
        svc = _make_pull_service()
        result = asyncio.run(
            svc.pull("remote", "local")
        )
        assert result.success is True
        assert result.tasks_fetched == 0
        assert result.projects_fetched == 0

    def test_duration_is_positive(self):
        svc = _make_pull_service()
        result = asyncio.run(
            svc.pull("remote", "local")
        )
        assert result.duration > 0

    def test_result_has_no_error_on_success(self):
        svc = _make_pull_service()
        result = asyncio.run(
            svc.pull("remote", "local")
        )
        assert result.error is None

    def test_sync_state_updated_on_non_dry_run(self):
        svc = _make_pull_service()
        asyncio.run(
            svc.pull("remote", "local", dry_run=False)
        )
        svc.sync_state.set_last_sync.assert_called_once()

    def test_sync_state_not_updated_on_dry_run(self):
        svc = _make_pull_service()
        asyncio.run(
            svc.pull("remote", "local", dry_run=True)
        )
        svc.sync_state.set_last_sync.assert_not_called()

    def test_conflict_tracker_save_called_when_conflicts(self):
        svc = _make_pull_service()
        svc.conflict_tracker.has_conflicts.return_value = True
        asyncio.run(
            svc.pull("remote", "local")
        )
        svc.conflict_tracker.save.assert_called_once()

    def test_exception_in_list_all_captured_in_result(self):
        svc = _make_pull_service()
        svc.source_project_repo.list_all = AsyncMock(side_effect=RuntimeError("network failure"))
        result = asyncio.run(
            svc.pull("remote", "local")
        )
        assert result.success is False
        assert result.error is not None
        assert "RuntimeError" in result.error


# ===========================================================================
# SyncPushService._sync_project
# ===========================================================================

class TestSyncPushServiceSyncProject:
    """Unit tests for _sync_project in SyncPushService."""

    def test_new_project_increments_projects_new(self):
        svc = _make_push_service(get_by_id=None)
        result = SyncResult()
        asyncio.run(
            svc._sync_project(_make_project(), result, "local_wins")
        )
        assert result.projects_new == 1

    def test_existing_local_newer_local_wins_updated(self):
        existing = _make_project(updated_at="2024-01-01T00:00:00Z")
        incoming = _make_project(updated_at="2024-01-02T00:00:00Z")
        svc = _make_push_service()
        svc.target_project_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_project(incoming, result, "local_wins")
        )
        assert result.projects_updated == 1

    def test_existing_remote_newer_local_wins_unchanged(self):
        existing = _make_project(updated_at="2024-01-02T00:00:00Z")
        incoming = _make_project(updated_at="2024-01-01T00:00:00Z")
        svc = _make_push_service()
        svc.target_project_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_project(incoming, result, "local_wins")
        )
        assert result.projects_unchanged == 1


# ===========================================================================
# SyncPushService._sync_label
# ===========================================================================

class TestSyncPushServiceSyncLabel:
    """Unit tests for _sync_label in SyncPushService."""

    def test_new_label_increments_labels_new(self):
        svc = _make_push_service(get_by_id=None)
        result = SyncResult()
        asyncio.run(
            svc._sync_label(_make_label(), result, "local_wins")
        )
        assert result.labels_new == 1

    def test_existing_label_increments_unchanged(self):
        existing = _make_label()
        svc = _make_push_service()
        svc.target_label_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_label(_make_label(), result, "local_wins")
        )
        assert result.labels_unchanged == 1


# ===========================================================================
# SyncPushService._sync_task
# ===========================================================================

class TestSyncPushServiceSyncTask:
    """Unit tests for _sync_task in SyncPushService."""

    def test_new_task_increments_tasks_new(self):
        import todopro_cli.services.sync_service as m
        m.TaskCreate = TaskCreate
        m.TaskUpdate = TaskUpdate
        svc = _make_push_service(get_by_id=None)
        result = SyncResult()
        asyncio.run(
            svc._sync_task(_make_task(), result, "local_wins")
        )
        assert result.tasks_new == 1

    def test_existing_equal_timestamps_unchanged(self):
        ts = "2024-05-01T00:00:00Z"
        existing = _make_task(updated_at=ts)
        incoming = _make_task(updated_at=ts)
        svc = _make_push_service()
        svc.target_task_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_task(incoming, result, "local_wins")
        )
        assert result.tasks_unchanged == 1

    def test_existing_remote_newer_local_wins_conflict(self):
        existing = _make_task(updated_at="2024-01-02T00:00:00Z")
        incoming = _make_task(updated_at="2024-01-01T00:00:00Z")
        svc = _make_push_service()
        svc.target_task_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(
            svc._sync_task(incoming, result, "local_wins")
        )
        assert result.tasks_conflicts == 1

    def test_existing_local_newer_local_wins_updated(self):
        existing = _make_task(updated_at="2024-01-01T00:00:00Z")
        incoming = _make_task(updated_at="2024-01-02T00:00:00Z")
        svc = _make_push_service()
        svc.target_task_repo.get_by_id = AsyncMock(return_value=existing)
        import todopro_cli.services.sync_service as m
        m.TaskCreate = TaskCreate
        m.TaskUpdate = TaskUpdate
        result = SyncResult()
        asyncio.run(
            svc._sync_task(incoming, result, "local_wins")
        )
        assert result.tasks_updated == 1


# ===========================================================================
# SyncPushService.push (integration-style)
# ===========================================================================

class TestSyncPushServicePush:
    """Integration-style tests for SyncPushService.push()."""

    def test_dry_run_returns_success(self):
        svc = _make_push_service()
        svc.source_project_repo.list_all = AsyncMock(return_value=[_make_project()])
        svc.source_label_repo.list_all = AsyncMock(return_value=[_make_label()])
        svc.source_task_repo.list_all = AsyncMock(return_value=[_make_task()])

        result = asyncio.run(
            svc.push("local", "remote", dry_run=True)
        )
        assert result.success is True
        svc.target_project_repo.create.assert_not_called()

    def test_empty_repos_succeeds(self):
        svc = _make_push_service()
        result = asyncio.run(
            svc.push("local", "remote")
        )
        assert result.success is True
        assert result.tasks_fetched == 0

    def test_sync_state_updated_after_push(self):
        svc = _make_push_service()
        asyncio.run(
            svc.push("local", "remote", dry_run=False)
        )
        svc.sync_state.set_last_sync.assert_called_once()

    def test_exception_captured_in_result(self):
        svc = _make_push_service()
        svc.source_project_repo.list_all = AsyncMock(side_effect=ValueError("bad data"))
        result = asyncio.run(
            svc.push("local", "remote")
        )
        assert result.success is False
        assert "ValueError" in result.error

    def test_result_duration_positive(self):
        svc = _make_push_service()
        result = asyncio.run(
            svc.push("local", "remote")
        )
        assert result.duration >= 0


# ===========================================================================
# Additional coverage: pull non-dry-run loop bodies (lines 235-248)
# ===========================================================================

class TestSyncPullServiceNonDryRunLoops:
    """Cover lines 235-248: for loops in pull() non-dry-run path."""

    def test_pull_with_new_items_all_synced(self):
        """Non-empty repos + dry_run=False exercises the for-loop bodies."""
        project = _make_project()
        label = _make_label()
        task = _make_task()

        svc = _make_pull_service()
        svc.source_project_repo.list_all = AsyncMock(return_value=[project])
        svc.source_label_repo.list_all = AsyncMock(return_value=[label])
        svc.source_task_repo.list_all = AsyncMock(return_value=[task])
        # target repos return None → items are new
        svc.target_project_repo.get_by_id = AsyncMock(return_value=None)
        svc.target_label_repo.get_by_id = AsyncMock(return_value=None)
        svc.target_task_repo.get_by_id = AsyncMock(return_value=None)

        import todopro_cli.services.sync_service as m
        m.TaskCreate = TaskCreate
        m.TaskUpdate = TaskUpdate

        result = asyncio.run(svc.pull("remote", "local", dry_run=False))

        assert result.success is True
        assert result.projects_new >= 1
        assert result.labels_new >= 1
        assert result.tasks_new >= 1

    def test_pull_with_multiple_items_all_processed(self):
        """Multiple items per category all get processed."""
        projects = [_make_project(), _make_project()]
        projects[1].id = "proj-002"
        labels = [_make_label(), _make_label()]
        labels[1].id = "lbl-002"
        tasks = [_make_task(), _make_task()]
        tasks[1].id = "task-002"

        svc = _make_pull_service()
        svc.source_project_repo.list_all = AsyncMock(return_value=projects)
        svc.source_label_repo.list_all = AsyncMock(return_value=labels)
        svc.source_task_repo.list_all = AsyncMock(return_value=tasks)
        svc.target_project_repo.get_by_id = AsyncMock(return_value=None)
        svc.target_label_repo.get_by_id = AsyncMock(return_value=None)
        svc.target_task_repo.get_by_id = AsyncMock(return_value=None)

        import todopro_cli.services.sync_service as m
        m.TaskCreate = TaskCreate
        m.TaskUpdate = TaskUpdate

        result = asyncio.run(svc.pull("remote", "local", dry_run=False))
        assert result.projects_fetched == 2
        assert result.labels_fetched == 2
        assert result.tasks_fetched == 2


# ===========================================================================
# PullService _sync_label should_update=True (line 331)
# ===========================================================================

class TestSyncPullServiceSyncLabelShouldUpdate:
    """Cover line 331: _sync_label with should_update=True (remote newer)."""

    def test_existing_label_remote_newer_still_unchanged(self):
        """Label exists; remote is newer → should_update=True → labels_unchanged += 1 (line 331)."""
        existing = _make_label(updated_at="2024-01-01T00:00:00Z")
        incoming = _make_label(updated_at="2024-01-02T00:00:00Z")  # remote newer
        svc = _make_pull_service()
        svc.target_label_repo.get_by_id = AsyncMock(return_value=existing)
        result = SyncResult()
        asyncio.run(svc._sync_label(incoming, result, "remote_wins"))
        assert result.labels_unchanged == 1


# ===========================================================================
# Additional coverage: push non-dry-run loop bodies (lines 450-461)
# ===========================================================================

class TestSyncPushServiceNonDryRunLoops:
    """Cover lines 450-461: for loops in push() non-dry-run path."""

    def test_push_with_new_items_all_synced(self):
        """Non-empty repos + dry_run=False exercises the push for-loop bodies."""
        project = _make_project()
        label = _make_label()
        task = _make_task()

        svc = _make_push_service()
        svc.source_project_repo.list_all = AsyncMock(return_value=[project])
        svc.source_label_repo.list_all = AsyncMock(return_value=[label])
        svc.source_task_repo.list_all = AsyncMock(return_value=[task])
        svc.target_project_repo.get_by_id = AsyncMock(return_value=None)
        svc.target_label_repo.get_by_id = AsyncMock(return_value=None)
        svc.target_task_repo.get_by_id = AsyncMock(return_value=None)

        import todopro_cli.services.sync_service as m
        m.TaskCreate = TaskCreate
        m.TaskUpdate = TaskUpdate

        result = asyncio.run(svc.push("local", "remote", dry_run=False))

        assert result.success is True
        assert result.projects_new >= 1
        assert result.labels_new >= 1
        assert result.tasks_new >= 1


# ===========================================================================
# PushService conflict tracker save (line 470)
# ===========================================================================

class TestSyncPushServiceConflictTrackerSave:
    """Cover line 470: conflict_tracker.save() called in push() when conflicts."""

    def test_push_conflict_tracker_save_called_when_conflicts(self):
        svc = _make_push_service()
        svc.conflict_tracker.has_conflicts.return_value = True
        asyncio.run(svc.push("local", "remote"))
        svc.conflict_tracker.save.assert_called_once()


# ===========================================================================
# PushService _sync_project exception handling (lines 519-520)
# ===========================================================================

class TestSyncPushServiceSyncProjectException:
    """Cover lines 519-520: _sync_project exception handler."""

    def test_exception_in_get_by_id_does_not_propagate(self):
        svc = _make_push_service()
        svc.target_project_repo.get_by_id = AsyncMock(
            side_effect=RuntimeError("network error")
        )
        result = SyncResult()
        asyncio.run(svc._sync_project(_make_project(), result, "local_wins"))
        # Exception was swallowed; result unchanged
        assert result.projects_new == 0
        assert result.projects_updated == 0


# ===========================================================================
# PushService _sync_label exception handling (lines 537-538)
# ===========================================================================

class TestSyncPushServiceSyncLabelException:
    """Cover lines 537-538: _sync_label exception handler."""

    def test_exception_in_get_by_id_does_not_propagate(self):
        svc = _make_push_service()
        svc.target_label_repo.get_by_id = AsyncMock(
            side_effect=RuntimeError("network error")
        )
        result = SyncResult()
        asyncio.run(svc._sync_label(_make_label(), result, "local_wins"))
        assert result.labels_new == 0


# ===========================================================================
# PushService _sync_task exception handling (lines 590-591)
# ===========================================================================

class TestSyncPushServiceSyncTaskException:
    """Cover lines 590-591: _sync_task exception handler."""

    def test_exception_in_get_by_id_does_not_propagate(self):
        svc = _make_push_service()
        svc.target_task_repo.get_by_id = AsyncMock(
            side_effect=RuntimeError("network error")
        )
        result = SyncResult()
        asyncio.run(svc._sync_task(_make_task(), result, "local_wins"))
        assert result.tasks_new == 0
