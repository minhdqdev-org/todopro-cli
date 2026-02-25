"""Tests for sync state manager."""

# pylint: disable=redefined-outer-name

from datetime import UTC, datetime, timedelta

import pytest

from todopro_cli.services.sync_state import SyncState


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    return tmp_path / ".todopro"


@pytest.fixture
def sync_state(temp_config_dir):
    """Create a sync state instance with temp directory."""
    return SyncState(config_dir=temp_config_dir)


def test_initial_state(sync_state):
    """Test initial state is empty."""
    assert sync_state.get_last_sync("test-context") is None
    assert sync_state.get_all_sync_times() == {}


def test_set_and_get_last_sync(sync_state):
    """Test setting and getting last sync time."""
    context_key = "local:work -> remote:api (pull)"
    now = datetime.now(UTC)

    sync_state.set_last_sync(context_key, now)

    retrieved = sync_state.get_last_sync(context_key)
    assert retrieved is not None
    # Compare with small tolerance for ISO string conversion
    assert abs((retrieved - now).total_seconds()) < 1


def test_set_last_sync_without_timestamp(sync_state):
    """Test setting last sync with automatic timestamp."""
    context_key = "local:work -> remote:api (push)"

    before = datetime.now(UTC)
    sync_state.set_last_sync(context_key)
    after = datetime.now(UTC)

    retrieved = sync_state.get_last_sync(context_key)
    assert retrieved is not None
    assert before <= retrieved <= after


def test_clear_last_sync(sync_state):
    """Test clearing last sync time."""
    context_key = "test-context"

    sync_state.set_last_sync(context_key)
    assert sync_state.get_last_sync(context_key) is not None

    sync_state.clear_last_sync(context_key)
    assert sync_state.get_last_sync(context_key) is None


def test_get_all_sync_times(sync_state):
    """Test getting all sync times."""
    context1 = "context-1"
    context2 = "context-2"
    time1 = datetime.now(UTC)
    time2 = datetime.now(UTC) + timedelta(hours=1)

    sync_state.set_last_sync(context1, time1)
    sync_state.set_last_sync(context2, time2)

    all_times = sync_state.get_all_sync_times()
    assert len(all_times) == 2
    assert context1 in all_times
    assert context2 in all_times


def test_persistence(temp_config_dir):
    """Test that state persists across instances."""
    context_key = "persistent-context"
    timestamp = datetime.now(UTC)

    # Create first instance and set state
    state1 = SyncState(config_dir=temp_config_dir)
    state1.set_last_sync(context_key, timestamp)

    # Create second instance and verify state persists
    state2 = SyncState(config_dir=temp_config_dir)
    retrieved = state2.get_last_sync(context_key)

    assert retrieved is not None
    assert abs((retrieved - timestamp).total_seconds()) < 1


def test_make_context_key():
    """Test context key generation."""
    key = SyncState.make_context_key("local", "remote", "pull")
    assert key == "local -> remote (pull)"

    key = SyncState.make_context_key("vault-work", "api-prod", "push")
    assert key == "vault-work -> api-prod (push)"


def test_corrupted_file_handling(temp_config_dir):
    """Test handling of corrupted state file."""
    # Create a corrupted file
    temp_config_dir.mkdir(parents=True, exist_ok=True)
    state_file = temp_config_dir / "sync-state.yaml"
    state_file.write_text("invalid: yaml: content: [unclosed")

    # Should handle gracefully and start fresh
    state = SyncState(config_dir=temp_config_dir)
    assert state.get_all_sync_times() == {}
