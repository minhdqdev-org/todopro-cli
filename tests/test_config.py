"""Tests for configuration management."""

import json
import tempfile
from pathlib import Path

import pytest

from todopro_cli.config import Config, ConfigManager


def test_default_config():
    """Test default configuration."""
    config = Config()
    assert config.api.endpoint == "https://todopro.minhdq.dev/api"
    assert config.api.timeout == 30
    assert config.output.format == "table"
    assert config.cache.enabled is True


def test_config_manager_creation():
    """Test config manager creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        # Override directories for testing
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.data_dir = Path(tmpdir) / "data"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.credentials_file = config_manager.data_dir / "test.credentials.json"

        config_manager.config_dir.mkdir(parents=True, exist_ok=True)
        config_manager.data_dir.mkdir(parents=True, exist_ok=True)

        # Test default config
        config = config_manager.config
        assert config.api.endpoint == "https://todopro.minhdq.dev/api"


def test_config_save_load():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.data_dir = Path(tmpdir) / "data"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.credentials_file = config_manager.data_dir / "test.credentials.json"

        config_manager.config_dir.mkdir(parents=True, exist_ok=True)
        config_manager.data_dir.mkdir(parents=True, exist_ok=True)

        # Set a value
        config_manager.set("api.endpoint", "https://test.example.com/api")
        assert config_manager.get("api.endpoint") == "https://test.example.com/api"

        # Create a new manager with the same profile
        config_manager2 = ConfigManager(profile="test")
        config_manager2.config_dir = Path(tmpdir) / "config"
        config_manager2.config_file = config_manager2.config_dir / "test.json"

        # Load should return the saved value
        assert config_manager2.get("api.endpoint") == "https://test.example.com/api"


def test_credentials_save_load():
    """Test saving and loading credentials."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.data_dir = Path(tmpdir) / "data"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.credentials_file = config_manager.data_dir / "test.credentials.json"

        config_manager.config_dir.mkdir(parents=True, exist_ok=True)
        config_manager.data_dir.mkdir(parents=True, exist_ok=True)

        # Save credentials
        config_manager.save_credentials("test_token", "test_refresh_token")

        # Load credentials
        credentials = config_manager.load_credentials()
        assert credentials is not None
        assert credentials["token"] == "test_token"
        assert credentials["refresh_token"] == "test_refresh_token"

        # Clear credentials
        config_manager.clear_credentials()
        credentials = config_manager.load_credentials()
        assert credentials is None
