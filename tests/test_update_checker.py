"""Tests for the auto-update checker."""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from todopro_cli import __version__
from todopro_cli.utils.update_checker import (
    CACHE_DIR,
    CACHE_FILE,
    check_for_updates,
)


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Fixture to use a temporary cache directory."""
    cache_dir = tmp_path / "todopro"
    with patch("todopro_cli.utils.update_checker.CACHE_DIR", cache_dir):
        with patch(
            "todopro_cli.utils.update_checker.CACHE_FILE", cache_dir / "update_check.json"
        ):
            yield cache_dir


def test_check_for_updates_with_newer_version(mock_cache_dir, capsys):
    """Test that update notification is shown when newer version is available."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.99.99"}}

    with patch("todopro_cli.utils.update_checker.requests.get", return_value=mock_response):
        check_for_updates()

    captured = capsys.readouterr()
    assert "New version available: 99.99.99" in captured.out
    assert __version__ in captured.out
    assert "uv tool upgrade todopro-cli" in captured.out


def test_check_for_updates_with_same_version(mock_cache_dir, capsys):
    """Test that no notification is shown when version is the same."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": __version__}}

    with patch("todopro_cli.utils.update_checker.requests.get", return_value=mock_response):
        check_for_updates()

    captured = capsys.readouterr()
    assert "New version available" not in captured.out


def test_check_for_updates_with_older_version(mock_cache_dir, capsys):
    """Test that no notification is shown when PyPI has older version."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "0.0.1"}}

    with patch("todopro_cli.utils.update_checker.requests.get", return_value=mock_response):
        check_for_updates()

    captured = capsys.readouterr()
    assert "New version available" not in captured.out


def test_check_for_updates_network_error(mock_cache_dir, capsys):
    """Test that network errors are handled silently."""
    with patch(
        "todopro_cli.utils.update_checker.requests.get",
        side_effect=Exception("Network error"),
    ):
        check_for_updates()

    captured = capsys.readouterr()
    assert "Network error" not in captured.out
    assert "New version available" not in captured.out


def test_check_for_updates_uses_cache(mock_cache_dir, capsys):
    """Test that cache is used when it's fresh (< 1 hour)."""
    cache_file = mock_cache_dir / "update_check.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_data = {
        "last_check_timestamp": time.time(),
        "latest_version": "99.99.99"
    }
    cache_file.write_text(json.dumps(cache_data))

    # Mock requests to ensure it's NOT called
    with patch("todopro_cli.utils.update_checker.requests.get") as mock_get:
        check_for_updates()
        mock_get.assert_not_called()

    captured = capsys.readouterr()
    assert "New version available: 99.99.99" in captured.out


def test_check_for_updates_refreshes_expired_cache(mock_cache_dir, capsys):
    """Test that cache is refreshed when expired (> 1 hour)."""
    cache_file = mock_cache_dir / "update_check.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Cache from 2 hours ago
    cache_data = {
        "last_check_timestamp": time.time() - 7200,
        "latest_version": "1.0.0"
    }
    cache_file.write_text(json.dumps(cache_data))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.99.99"}}

    with patch("todopro_cli.utils.update_checker.requests.get", return_value=mock_response):
        check_for_updates()

    # Verify new version from API was used, not cached version
    captured = capsys.readouterr()
    assert "New version available: 99.99.99" in captured.out


def test_check_for_updates_creates_cache_file(mock_cache_dir):
    """Test that cache file is created after successful PyPI check."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.99.99"}}

    with patch("todopro_cli.utils.update_checker.requests.get", return_value=mock_response):
        check_for_updates()

    cache_file = mock_cache_dir / "update_check.json"
    assert cache_file.exists()
    
    cache_data = json.loads(cache_file.read_text())
    assert "last_check_timestamp" in cache_data
    assert cache_data["latest_version"] == "99.99.99"


def test_check_for_updates_timeout(mock_cache_dir, capsys):
    """Test that timeout is properly set to avoid blocking."""
    with patch("todopro_cli.utils.update_checker.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "1.0.0"}}
        mock_get.return_value = mock_response
        
        check_for_updates()
        
        # Verify timeout parameter is set
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == 0.5
