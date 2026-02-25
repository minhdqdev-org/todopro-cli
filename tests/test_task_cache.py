"""Tests for background task cache."""

import json
import time
from unittest.mock import patch

import pytest

from todopro_cli.services.cache_service import BackgroundTaskCache, get_background_cache


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Fixture to use a temporary cache directory."""
    cache_dir = tmp_path / "todopro"
    cache_file = cache_dir / "processing_tasks.json"

    with patch("todopro_cli.services.cache_service.CACHE_DIR", cache_dir):
        with patch(
            "todopro_cli.services.cache_service.PROCESSING_CACHE_FILE", cache_file
        ):
            yield cache_dir


def test_cache_initialization(mock_cache_dir):
    """Test cache initialization."""
    cache = BackgroundTaskCache()
    assert cache.cache_file == mock_cache_dir / "processing_tasks.json"


def test_add_completing_task(mock_cache_dir):
    """Test adding a task to the cache."""
    cache = BackgroundTaskCache()
    cache.add_completing_task("task-123")

    # Verify task is in cache
    assert cache.is_being_completed("task-123")
    assert not cache.is_being_completed("task-456")


def test_add_completing_tasks_batch(mock_cache_dir):
    """Test adding multiple tasks to the cache."""
    cache = BackgroundTaskCache()
    cache.add_completing_tasks(["task-1", "task-2", "task-3"])

    # Verify all tasks are in cache
    assert cache.is_being_completed("task-1")
    assert cache.is_being_completed("task-2")
    assert cache.is_being_completed("task-3")
    assert not cache.is_being_completed("task-4")


def test_remove_task(mock_cache_dir):
    """Test removing a task from the cache."""
    cache = BackgroundTaskCache()
    cache.add_completing_task("task-123")

    assert cache.is_being_completed("task-123")

    cache.remove_task("task-123")
    assert not cache.is_being_completed("task-123")


def test_get_completing_tasks(mock_cache_dir):
    """Test getting list of completing tasks."""
    cache = BackgroundTaskCache()
    cache.add_completing_tasks(["task-1", "task-2", "task-3"])

    completing = cache.get_completing_tasks()
    assert set(completing) == {"task-1", "task-2", "task-3"}


def test_cache_persistence(mock_cache_dir):
    """Test that cache persists across instances."""
    cache1 = BackgroundTaskCache()
    cache1.add_completing_task("task-123")

    # Create new instance
    cache2 = BackgroundTaskCache()
    assert cache2.is_being_completed("task-123")


def test_expired_entries_cleaned(mock_cache_dir):
    """Test that expired entries are cleaned automatically."""
    cache = BackgroundTaskCache()

    # Add task with old timestamp
    cache_file = mock_cache_dir / "processing_tasks.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)
    old_cache = {
        "task-old": time.time() - 400,  # Expired (> 5 minutes)
        "task-new": time.time(),  # Fresh
    }
    cache_file.write_text(json.dumps(old_cache))

    # Check - old should be filtered out
    assert not cache.is_being_completed("task-old")
    assert cache.is_being_completed("task-new")


def test_clear_expired(mock_cache_dir):
    """Test explicit clearing of expired entries."""
    cache = BackgroundTaskCache()

    # Add tasks with different timestamps
    cache_file = mock_cache_dir / "processing_tasks.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)
    mixed_cache = {
        "task-1": time.time() - 400,  # Expired
        "task-2": time.time(),  # Fresh
        "task-3": time.time() - 500,  # Expired
    }
    cache_file.write_text(json.dumps(mixed_cache))

    cache.clear_expired()

    # Only fresh task should remain
    completing = cache.get_completing_tasks()
    assert len(completing) == 1
    assert "task-2" in completing


def test_clear_all(mock_cache_dir):
    """Test clearing all entries from cache."""
    cache = BackgroundTaskCache()
    cache.add_completing_tasks(["task-1", "task-2", "task-3"])

    assert len(cache.get_completing_tasks()) == 3

    cache.clear_all()
    assert len(cache.get_completing_tasks()) == 0


def test_cache_file_not_exists(mock_cache_dir):
    """Test behavior when cache file doesn't exist."""
    cache = BackgroundTaskCache()

    # Should not crash
    assert not cache.is_being_completed("task-123")
    assert cache.get_completing_tasks() == []


def test_corrupted_cache_file(mock_cache_dir):
    """Test handling of corrupted cache file."""
    cache_file = mock_cache_dir / "processing_tasks.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)

    # Write invalid JSON
    cache_file.write_text("{ invalid json }")

    cache = BackgroundTaskCache()
    # Should handle gracefully
    assert not cache.is_being_completed("task-123")
    assert cache.get_completing_tasks() == []


def test_get_background_cache_singleton(mock_cache_dir):
    """Test that get_background_cache returns singleton."""
    cache1 = get_background_cache()
    cache2 = get_background_cache()

    assert cache1 is cache2


def test_cache_ttl(mock_cache_dir):
    """Test that cache respects TTL."""
    from todopro_cli.services.cache_service import CACHE_TTL

    cache = BackgroundTaskCache()

    # Add task with timestamp just before TTL expiry
    cache_file = mock_cache_dir / "processing_tasks.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)

    # Just within TTL
    recent = {"task-recent": time.time() - (CACHE_TTL - 10)}
    cache_file.write_text(json.dumps(recent))
    assert cache.is_being_completed("task-recent")

    # Just outside TTL
    expired = {"task-expired": time.time() - (CACHE_TTL + 10)}
    cache_file.write_text(json.dumps(expired))
    assert not cache.is_being_completed("task-expired")
