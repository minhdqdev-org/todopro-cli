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


# ---------------------------------------------------------------------------
# Tests for previously uncovered lines (83% → 100%)
# ---------------------------------------------------------------------------


def test_load_existing_valid_json_file(tmp_path):
    """Test _load reads an existing valid JSON file (covers lines 44-47)."""
    import json

    config_dir = tmp_path / ".todopro"
    config_dir.mkdir()
    state_file = config_dir / "sync-state.json"

    timestamp = datetime.now(UTC)
    state_file.write_text(
        json.dumps({"last_sync": {"context-1": timestamp.isoformat()}})
    )

    state = SyncState(config_dir=config_dir)
    result = state.get_last_sync("context-1")
    assert result is not None


def test_load_file_missing_last_sync_key(tmp_path):
    """Test _load handles a file that has no 'last_sync' key (covers lines 44-47)."""
    import json

    config_dir = tmp_path / ".todopro"
    config_dir.mkdir()
    state_file = config_dir / "sync-state.json"
    state_file.write_text(json.dumps({"other_key": "value"}))

    state = SyncState(config_dir=config_dir)
    # Missing key is initialised to empty dict
    assert state.get_all_sync_times() == {}


def test_save_creates_config_dir(tmp_path):
    """Test _save creates nested config dir when it doesn't exist (covers lines 71-73)."""
    config_dir = tmp_path / ".todopro" / "nested"
    # Directory does NOT exist yet
    state = SyncState(config_dir=config_dir)
    state.set_last_sync("test-key")  # triggers _save → mkdir
    assert (config_dir / "sync-state.json").exists()


def test_get_last_sync_with_aware_datetime_object(tmp_path):
    """Test get_last_sync when stored value is an aware datetime object (covers line 79)."""
    config_dir = tmp_path / ".todopro"
    state = SyncState(config_dir=config_dir)

    dt_aware = datetime.now(UTC)
    state._state["last_sync"]["test-key"] = dt_aware

    result = state.get_last_sync("test-key")
    assert result is not None
    assert result.tzinfo is not None


def test_get_last_sync_with_naive_datetime_object(tmp_path):
    """Test get_last_sync adds UTC to naive datetime objects (covers line 79 branch)."""
    config_dir = tmp_path / ".todopro"
    state = SyncState(config_dir=config_dir)

    dt_naive = datetime(2024, 1, 1, 12, 0, 0)  # no tzinfo
    state._state["last_sync"]["test-key"] = dt_naive

    result = state.get_last_sync("test-key")
    assert result is not None
    assert result.tzinfo is not None  # UTC was added


def test_get_all_sync_times_with_datetime_objects(tmp_path):
    """Test get_all_sync_times handles both aware and naive datetime values (covers line 121)."""
    config_dir = tmp_path / ".todopro"
    state = SyncState(config_dir=config_dir)

    dt_aware = datetime.now(UTC)
    dt_naive = datetime(2024, 1, 1, 12, 0, 0)
    state._state["last_sync"]["aware-key"] = dt_aware
    state._state["last_sync"]["naive-key"] = dt_naive

    all_times = state.get_all_sync_times()
    assert "aware-key" in all_times
    assert all_times["aware-key"] is not None
    assert "naive-key" in all_times
    assert all_times["naive-key"] is not None


def test_get_all_sync_times_with_iso_strings(tmp_path):
    """Test get_all_sync_times parses ISO format strings (covers lines 124-127)."""
    config_dir = tmp_path / ".todopro"
    state = SyncState(config_dir=config_dir)

    state._state["last_sync"]["iso-key"] = "2024-01-01T12:00:00Z"

    all_times = state.get_all_sync_times()
    assert "iso-key" in all_times
    assert all_times["iso-key"] is not None
    assert isinstance(all_times["iso-key"], datetime)


def test_default_config_dir_used_when_none_given(tmp_path, monkeypatch):
    """SyncState() with no args uses Path.home() / '.todopro' (covers line 25)."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr("todopro_cli.services.sync_state.Path.home", lambda: fake_home)

    state = SyncState()  # config_dir=None triggers the default branch

    assert state.config_dir == fake_home / ".todopro"


def test_load_corrupted_json_falls_back_to_empty(tmp_path):
    """_load recovers gracefully when sync-state.json contains invalid JSON (covers lines 45-47)."""
    config_dir = tmp_path / ".todopro"
    config_dir.mkdir()
    # Use the exact file name the code looks for (sync-state.json, not .yaml)
    state_file = config_dir / "sync-state.json"
    state_file.write_text("{not valid json}")  # triggers json.JSONDecodeError

    state = SyncState(config_dir=config_dir)
    assert state.get_all_sync_times() == {}


def test_get_last_sync_naive_iso_string_gets_utc(tmp_path):
    """ISO string without timezone info is treated as UTC (covers line 79)."""
    config_dir = tmp_path / ".todopro"
    state = SyncState(config_dir=config_dir)
    # No 'Z' / '+00:00' suffix → fromisoformat produces a naive datetime
    state._state["last_sync"]["naive-iso-key"] = "2024-06-15T10:30:00"

    result = state.get_last_sync("naive-iso-key")
    assert result is not None
    assert result.tzinfo is not None  # UTC was added at line 79


def test_get_all_sync_times_with_none_value(tmp_path):
    """get_all_sync_times preserves explicit None values (covers line 121)."""
    config_dir = tmp_path / ".todopro"
    state = SyncState(config_dir=config_dir)
    state._state["last_sync"]["null-key"] = None

    all_times = state.get_all_sync_times()
    assert "null-key" in all_times
    assert all_times["null-key"] is None


def test_load_state_without_last_sync_key(temp_config_dir):
    """Test loading state file that is missing 'last_sync' key gets repaired."""
    import json

    temp_config_dir.mkdir(parents=True, exist_ok=True)
    state_file = temp_config_dir / "sync-state.json"
    # Write a state file without 'last_sync' key
    state_file.write_text(json.dumps({"other_key": "value"}))

    state = SyncState(config_dir=temp_config_dir)
    # Should have repaired the missing key
    assert state.get_all_sync_times() == {}
    assert state.get_last_sync("any") is None


def test_load_corrupted_json_file(temp_config_dir):
    """Test loading a corrupted JSON file starts fresh."""
    temp_config_dir.mkdir(parents=True, exist_ok=True)
    state_file = temp_config_dir / "sync-state.json"
    state_file.write_text("{invalid json content")

    state = SyncState(config_dir=temp_config_dir)
    assert state.get_all_sync_times() == {}


def test_get_last_sync_with_datetime_object_naive(temp_config_dir):
    """Test get_last_sync when value in state is a naive datetime object."""
    from datetime import datetime

    state = SyncState(config_dir=temp_config_dir)
    # Directly inject a naive datetime into _state to hit the datetime branch
    naive_dt = datetime(2025, 1, 15, 10, 30, 0)
    state._state["last_sync"]["test-ctx"] = naive_dt

    result = state.get_last_sync("test-ctx")
    assert result is not None
    # Should have UTC timezone attached
    assert result.tzinfo is not None


def test_get_last_sync_with_datetime_object_aware(temp_config_dir):
    """Test get_last_sync when value is an aware datetime object."""
    from datetime import datetime

    state = SyncState(config_dir=temp_config_dir)
    aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
    state._state["last_sync"]["test-ctx"] = aware_dt

    result = state.get_last_sync("test-ctx")
    assert result is not None
    assert result == aware_dt


def test_get_last_sync_naive_iso_string(temp_config_dir):
    """Test get_last_sync parses ISO string without timezone (adds UTC)."""
    import json

    temp_config_dir.mkdir(parents=True, exist_ok=True)
    state_file = temp_config_dir / "sync-state.json"
    # ISO string without timezone
    state_file.write_text(json.dumps({"last_sync": {"ctx": "2025-01-15T10:30:00"}}))

    state = SyncState(config_dir=temp_config_dir)
    result = state.get_last_sync("ctx")
    assert result is not None
    assert result.tzinfo is not None


def test_get_all_sync_times_with_none_value(temp_config_dir):
    """Test get_all_sync_times handles None values in state."""
    state = SyncState(config_dir=temp_config_dir)
    # Directly inject a None value
    state._state["last_sync"]["null-ctx"] = None

    all_times = state.get_all_sync_times()
    assert "null-ctx" in all_times
    assert all_times["null-ctx"] is None


def test_get_all_sync_times_with_datetime_object(temp_config_dir):
    """Test get_all_sync_times when state contains datetime objects."""
    from datetime import datetime

    state = SyncState(config_dir=temp_config_dir)
    # Naive datetime
    naive_dt = datetime(2025, 1, 15, 10, 0, 0)
    state._state["last_sync"]["dt-ctx"] = naive_dt

    all_times = state.get_all_sync_times()
    assert "dt-ctx" in all_times
    assert all_times["dt-ctx"] == naive_dt


def test_get_all_sync_times_with_aware_datetime_object(temp_config_dir):
    """Test get_all_sync_times strips tzinfo from aware datetime objects."""
    from datetime import datetime

    state = SyncState(config_dir=temp_config_dir)
    aware_dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    state._state["last_sync"]["aware-ctx"] = aware_dt

    all_times = state.get_all_sync_times()
    assert "aware-ctx" in all_times
    # Should be stripped of timezone
    result = all_times["aware-ctx"]
    assert result is not None
    assert result.tzinfo is None
