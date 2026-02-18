"""Tests for the auto-update checker."""

import json
import os
import time
from unittest.mock import Mock, patch

import pytest

from todopro_cli import __version__
from todopro_cli.utils.update_checker import (
    DEFAULT_BACKEND_URL,
    check_for_updates,
    get_backend_url,
    get_latest_version,
    is_update_available,
)


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Fixture to use a temporary cache directory."""
    cache_dir = tmp_path / "todopro"
    with (
        patch("todopro_cli.utils.update_checker.CACHE_DIR", cache_dir),
        patch(
            "todopro_cli.utils.update_checker.CACHE_FILE",
            cache_dir / "update_check.json",
        ),
    ):
        yield cache_dir


def test_check_for_updates_with_newer_version(mock_cache_dir, capsys):
    """Test that update notification is shown when newer version is available."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.99.99"}}

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
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

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
        check_for_updates()

    captured = capsys.readouterr()
    assert "New version available" not in captured.out


def test_check_for_updates_with_older_version(mock_cache_dir, capsys):
    """Test that no notification is shown when PyPI has older version."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "0.0.1"}}

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
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

    cache_data = {"last_check_timestamp": time.time(), "latest_version": "99.99.99"}
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
    cache_data = {"last_check_timestamp": time.time() - 7200, "latest_version": "1.0.0"}
    cache_file.write_text(json.dumps(cache_data))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.99.99"}}

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
        check_for_updates()

    # Verify new version from API was used, not cached version
    captured = capsys.readouterr()
    assert "New version available: 99.99.99" in captured.out


def test_check_for_updates_creates_cache_file(mock_cache_dir):
    """Test that cache file is created after successful PyPI check."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.99.99"}}

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
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


def test_get_latest_version_success(mock_cache_dir):
    """Test getting latest version from PyPI."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "2.0.0"}}

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
        version = get_latest_version()
        assert version == "2.0.0"


def test_get_latest_version_network_error(mock_cache_dir):
    """Test that network errors return None."""
    with patch(
        "todopro_cli.utils.update_checker.requests.get",
        side_effect=Exception("Network error"),
    ):
        version = get_latest_version()
        assert version is None


def test_get_latest_version_uses_cache(mock_cache_dir):
    """Test that get_latest_version uses cache when fresh."""
    cache_file = mock_cache_dir / "update_check.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)

    cache_data = {"last_check_timestamp": time.time(), "latest_version": "3.0.0"}
    cache_file.write_text(json.dumps(cache_data))

    with patch("todopro_cli.utils.update_checker.requests.get") as mock_get:
        version = get_latest_version()
        # Should use cache, not call API
        mock_get.assert_not_called()
        assert version == "3.0.0"


def test_is_update_available_newer_version(mock_cache_dir):
    """Test is_update_available returns True when newer version exists."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "99.99.99"}}

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
        is_available, latest = is_update_available()
        assert is_available is True
        assert latest == "99.99.99"


def test_is_update_available_same_version(mock_cache_dir):
    """Test is_update_available returns False when version is same."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": __version__}}

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
        is_available, latest = is_update_available()
        assert is_available is False
        assert latest == __version__


def test_is_update_available_network_error(mock_cache_dir):
    """Test is_update_available handles network errors gracefully."""
    with patch(
        "todopro_cli.utils.update_checker.requests.get",
        side_effect=Exception("Network error"),
    ):
        is_available, latest = is_update_available()
        assert is_available is False
        assert latest is None


def test_get_backend_url_from_env_var(mock_cache_dir):
    """Test that environment variable has highest priority."""
    with patch.dict(os.environ, {"TODOPRO_BACKEND_URL": "http://localhost:8000/api"}):
        url = get_backend_url()
        assert url == "http://localhost:8000/api"


def test_get_backend_url_from_cache(mock_cache_dir):
    """Test that cache is used when fresh."""
    cache_file = mock_cache_dir / "update_check.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)

    cache_data = {
        "last_check_timestamp": time.time(),
        "latest_version": "1.0.0",
        "backend_url": "https://cached.backend.com/api",
    }
    cache_file.write_text(json.dumps(cache_data))

    with patch("todopro_cli.utils.update_checker.requests.get") as mock_get:
        url = get_backend_url()
        # Should use cache, not call API
        mock_get.assert_not_called()
        assert url == "https://cached.backend.com/api"


def test_get_backend_url_from_pypi(mock_cache_dir):
    """Test fetching backend URL from PyPI metadata."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {
            "version": "1.0.0",
            "project_urls": {"Backend": "https://pypi.backend.com/api"},
        }
    }

    with patch(
        "todopro_cli.utils.update_checker.requests.get", return_value=mock_response
    ):
        url = get_backend_url()
        assert url == "https://pypi.backend.com/api"


def test_get_backend_url_fallback_to_default(mock_cache_dir):
    """Test fallback to default URL when all else fails."""
    with patch(
        "todopro_cli.utils.update_checker.requests.get",
        side_effect=Exception("Network error"),
    ):
        url = get_backend_url()
        assert url == DEFAULT_BACKEND_URL


def test_get_backend_url_strips_trailing_slash(mock_cache_dir):
    """Test that trailing slashes are removed."""
    with patch.dict(os.environ, {"TODOPRO_BACKEND_URL": "http://localhost:8000/api/"}):
        url = get_backend_url()
        assert url == "http://localhost:8000/api"
        assert not url.endswith("/")


def test_get_backend_url_expired_cache_fallback(mock_cache_dir):
    """Test that expired cache is still used as fallback if PyPI fails."""
    cache_file = mock_cache_dir / "update_check.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)

    # Cache from 2 hours ago (expired)
    cache_data = {
        "last_check_timestamp": time.time() - 7200,
        "latest_version": "1.0.0",
        "backend_url": "https://expired.cache.com/api",
    }
    cache_file.write_text(json.dumps(cache_data))

    with patch(
        "todopro_cli.utils.update_checker.requests.get",
        side_effect=Exception("Network error"),
    ):
        url = get_backend_url()
        # Should use expired cache as fallback
        assert url == "https://expired.cache.com/api"
