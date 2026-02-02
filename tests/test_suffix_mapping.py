"""Tests for suffix mapping cache."""

import json
import time
from pathlib import Path

import pytest

from todopro_cli.utils.task_cache import (
    SUFFIX_MAPPING_FILE,
    SUFFIX_MAPPING_TTL,
    get_suffix_mapping,
    save_suffix_mapping,
)


@pytest.fixture
def cleanup_cache():
    """Clean up cache files before and after tests."""
    if SUFFIX_MAPPING_FILE.exists():
        SUFFIX_MAPPING_FILE.unlink()
    yield
    if SUFFIX_MAPPING_FILE.exists():
        SUFFIX_MAPPING_FILE.unlink()


def test_save_and_get_suffix_mapping(cleanup_cache):
    """Test saving and retrieving suffix mapping."""
    mapping = {
        "abc": "123e4567-e89b-12d3-a456-426614174000",
        "def": "223e4567-e89b-12d3-a456-426614174001",
        "xyz": "323e4567-e89b-12d3-a456-426614174002",
    }

    save_suffix_mapping(mapping)
    retrieved = get_suffix_mapping()

    assert retrieved == mapping


def test_suffix_mapping_ttl_expiration(cleanup_cache):
    """Test that expired suffix mappings are not returned."""
    mapping = {
        "abc": "123e4567-e89b-12d3-a456-426614174000",
    }

    # Save mapping with old timestamp
    SUFFIX_MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": time.time() - SUFFIX_MAPPING_TTL - 10,  # Expired
        "mapping": mapping,
    }
    SUFFIX_MAPPING_FILE.write_text(json.dumps(data))

    # Should return empty dict for expired mapping
    retrieved = get_suffix_mapping()
    assert retrieved == {}


def test_suffix_mapping_missing_file(cleanup_cache):
    """Test get_suffix_mapping when file doesn't exist."""
    retrieved = get_suffix_mapping()
    assert retrieved == {}


def test_suffix_mapping_corrupted_file(cleanup_cache):
    """Test get_suffix_mapping with corrupted file."""
    SUFFIX_MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUFFIX_MAPPING_FILE.write_text("not valid json{{{")

    # Should return empty dict on error
    retrieved = get_suffix_mapping()
    assert retrieved == {}


def test_suffix_mapping_overwrite(cleanup_cache):
    """Test that new mappings overwrite old ones."""
    mapping1 = {
        "abc": "123e4567-e89b-12d3-a456-426614174000",
    }
    mapping2 = {
        "xyz": "323e4567-e89b-12d3-a456-426614174002",
    }

    save_suffix_mapping(mapping1)
    save_suffix_mapping(mapping2)

    retrieved = get_suffix_mapping()
    assert retrieved == mapping2


def test_suffix_mapping_timestamp(cleanup_cache):
    """Test that timestamp is saved correctly."""
    mapping = {
        "abc": "123e4567-e89b-12d3-a456-426614174000",
    }

    before = time.time()
    save_suffix_mapping(mapping)
    after = time.time()

    # Read raw file to check timestamp
    data = json.loads(SUFFIX_MAPPING_FILE.read_text())
    assert "timestamp" in data
    assert before <= data["timestamp"] <= after
    assert data["mapping"] == mapping


def test_suffix_mapping_empty_dict(cleanup_cache):
    """Test saving and retrieving empty mapping."""
    mapping = {}

    save_suffix_mapping(mapping)
    retrieved = get_suffix_mapping()

    assert retrieved == {}
