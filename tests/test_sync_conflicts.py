"""Tests for sync conflict tracker."""

import json

import pytest

from todopro_cli.services.sync_conflicts import SyncConflict, SyncConflictTracker


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    return tmp_path / ".todopro"


@pytest.fixture
def conflict_tracker(temp_config_dir):
    """Create a conflict tracker instance with temp directory."""
    return SyncConflictTracker(config_dir=temp_config_dir)


def test_initial_state(conflict_tracker):
    """Test initial state has no conflicts."""
    assert conflict_tracker.count() == 0
    assert conflict_tracker.has_conflicts() is False
    assert conflict_tracker.get_conflicts() == []


def test_add_conflict(conflict_tracker):
    """Test adding a conflict."""
    conflict = SyncConflict(
        resource_type="task",
        resource_id="test-uuid",
        local_data={"content": "Local version"},
        remote_data={"content": "Remote version"},
        resolution="remote_wins",
    )

    conflict_tracker.add_conflict(conflict)

    assert conflict_tracker.count() == 1
    assert conflict_tracker.has_conflicts() is True
    conflicts = conflict_tracker.get_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].resource_id == "test-uuid"


def test_conflict_to_dict():
    """Test converting conflict to dictionary."""
    conflict = SyncConflict(
        resource_type="project",
        resource_id="proj-123",
        local_data={"name": "Local Project"},
        remote_data={"name": "Remote Project"},
        resolution="local_wins",
    )

    conflict_dict = conflict.to_dict()

    assert conflict_dict["resource_type"] == "project"
    assert conflict_dict["resource_id"] == "proj-123"
    assert conflict_dict["local_data"]["name"] == "Local Project"
    assert conflict_dict["remote_data"]["name"] == "Remote Project"
    assert conflict_dict["resolution"] == "local_wins"
    assert "detected_at" in conflict_dict


def test_save_conflicts(conflict_tracker, temp_config_dir):
    """Test saving conflicts to file."""
    conflict1 = SyncConflict(
        resource_type="task",
        resource_id="task-1",
        local_data={"content": "Local 1"},
        remote_data={"content": "Remote 1"},
        resolution="remote_wins",
    )
    conflict2 = SyncConflict(
        resource_type="task",
        resource_id="task-2",
        local_data={"content": "Local 2"},
        remote_data={"content": "Remote 2"},
        resolution="local_wins",
    )

    conflict_tracker.add_conflict(conflict1)
    conflict_tracker.add_conflict(conflict2)
    conflict_tracker.save()

    # Verify file was created and contains conflicts
    conflicts_file = temp_config_dir / "sync-conflicts.json"
    assert conflicts_file.exists()

    with open(conflicts_file) as f:
        saved_conflicts = json.load(f)

    assert len(saved_conflicts) == 2
    assert saved_conflicts[0]["resource_id"] == "task-1"
    assert saved_conflicts[1]["resource_id"] == "task-2"


def test_clear_conflicts(conflict_tracker):
    """Test clearing conflicts from memory."""
    conflict = SyncConflict(
        resource_type="task",
        resource_id="test",
        local_data={},
        remote_data={},
        resolution="skipped",
    )

    conflict_tracker.add_conflict(conflict)
    assert conflict_tracker.count() == 1

    conflict_tracker.clear()
    assert conflict_tracker.count() == 0
    assert conflict_tracker.has_conflicts() is False


def test_compare_timestamps_remote_newer():
    """Test timestamp comparison when remote is newer."""
    local = "2026-02-09T10:00:00Z"
    remote = "2026-02-09T11:00:00Z"

    result = SyncConflictTracker.compare_timestamps(local, remote)
    assert result == "remote"


def test_compare_timestamps_local_newer():
    """Test timestamp comparison when local is newer."""
    local = "2026-02-09T12:00:00Z"
    remote = "2026-02-09T11:00:00Z"

    result = SyncConflictTracker.compare_timestamps(local, remote)
    assert result == "local"


def test_compare_timestamps_equal():
    """Test timestamp comparison when timestamps are equal."""
    timestamp = "2026-02-09T10:00:00Z"

    result = SyncConflictTracker.compare_timestamps(timestamp, timestamp)
    assert result == "equal"


def test_compare_timestamps_none():
    """Test timestamp comparison with None values."""
    result = SyncConflictTracker.compare_timestamps(None, None)
    assert result == "equal"

    result = SyncConflictTracker.compare_timestamps("2026-02-09T10:00:00Z", None)
    assert result == "local"

    result = SyncConflictTracker.compare_timestamps(None, "2026-02-09T10:00:00Z")
    assert result == "remote"


def test_save_empty_conflicts(conflict_tracker):
    """Test that save does nothing when no conflicts."""
    conflict_tracker.save()

    # Should not create file if no conflicts
    conflicts_file = conflict_tracker.conflicts_file
    assert not conflicts_file.exists()


def test_append_to_existing_conflicts(conflict_tracker, temp_config_dir):
    """Test appending new conflicts to existing file."""
    # Create initial conflicts
    conflict1 = SyncConflict(
        resource_type="task",
        resource_id="task-1",
        local_data={},
        remote_data={},
        resolution="remote_wins",
    )
    conflict_tracker.add_conflict(conflict1)
    conflict_tracker.save()

    # Create new tracker instance and add more conflicts
    tracker2 = SyncConflictTracker(config_dir=temp_config_dir)
    conflict2 = SyncConflict(
        resource_type="task",
        resource_id="task-2",
        local_data={},
        remote_data={},
        resolution="local_wins",
    )
    tracker2.add_conflict(conflict2)
    tracker2.save()

    # Verify both conflicts are in file
    with open(temp_config_dir / "sync-conflicts.json") as f:
        all_conflicts = json.load(f)

    assert len(all_conflicts) == 2
    assert all_conflicts[0]["resource_id"] == "task-1"
    assert all_conflicts[1]["resource_id"] == "task-2"
