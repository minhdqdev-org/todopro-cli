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
    assert config.output.format == "pretty"
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


def test_config_reset():
    """Test resetting configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.data_dir = Path(tmpdir) / "data"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.credentials_file = config_manager.data_dir / "test.credentials.json"

        config_manager.config_dir.mkdir(parents=True, exist_ok=True)
        config_manager.data_dir.mkdir(parents=True, exist_ok=True)

        # Set a value
        config_manager.set("api.endpoint", "https://custom.example.com/api")
        assert config_manager.get("api.endpoint") == "https://custom.example.com/api"

        # Reset all config
        config_manager.reset()
        assert config_manager.get("api.endpoint") == "https://todopro.minhdq.dev/api"


def test_config_reset_specific_key():
    """Test resetting a specific config key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.data_dir = Path(tmpdir) / "data"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.credentials_file = config_manager.data_dir / "test.credentials.json"

        config_manager.config_dir.mkdir(parents=True, exist_ok=True)
        config_manager.data_dir.mkdir(parents=True, exist_ok=True)

        # Set values
        config_manager.set("api.endpoint", "https://custom.example.com/api")
        config_manager.set("api.timeout", 60)

        # Reset specific key
        config_manager.reset("api.endpoint")
        assert config_manager.get("api.endpoint") == "https://todopro.minhdq.dev/api"
        assert config_manager.get("api.timeout") == 60


def test_list_profiles():
    """Test listing profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test1")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.config_file = config_manager.config_dir / "test1.json"
        config_manager.config_dir.mkdir(parents=True, exist_ok=True)
        config_manager.save_config()

        config_manager2 = ConfigManager(profile="test2")
        config_manager2.config_dir = Path(tmpdir) / "config"
        config_manager2.config_file = config_manager2.config_dir / "test2.json"
        config_manager2.save_config()

        profiles = config_manager.list_profiles()
        assert "test1" in profiles
        assert "test2" in profiles


def test_load_corrupted_config():
    """Test loading corrupted config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.config_dir.mkdir(parents=True, exist_ok=True)

        # Write corrupted JSON
        with open(config_manager.config_file, "w") as f:
            f.write("{invalid json")

        # Should return default config
        config = config_manager.load_config()
        assert config.api.endpoint == "https://todopro.minhdq.dev/api"


def test_load_credentials_corrupted():
    """Test loading corrupted credentials file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.data_dir = Path(tmpdir) / "data"
        config_manager.credentials_file = config_manager.data_dir / "test.credentials.json"
        config_manager.data_dir.mkdir(parents=True, exist_ok=True)

        # Write corrupted JSON
        with open(config_manager.credentials_file, "w") as f:
            f.write("{invalid json")

        # Should return None
        credentials = config_manager.load_credentials()
        assert credentials is None


def test_save_credentials_without_refresh_token():
    """Test saving credentials without refresh token."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.data_dir = Path(tmpdir) / "data"
        config_manager.credentials_file = config_manager.data_dir / "test.credentials.json"
        config_manager.data_dir.mkdir(parents=True, exist_ok=True)

        # Save credentials without refresh token
        config_manager.save_credentials("test_token")

        # Load credentials
        credentials = config_manager.load_credentials()
        assert credentials is not None
        assert credentials["token"] == "test_token"
        assert "refresh_token" not in credentials


def test_get_config_manager():
    """Test get_config_manager factory function."""
    from todopro_cli.config import get_config_manager
    
    manager1 = get_config_manager("default")
    assert manager1.profile == "default"
    
    # Should return the same instance for same profile
    manager2 = get_config_manager("default")
    assert manager1 is manager2
    
    # Should create new instance for different profile
    manager3 = get_config_manager("test")
    assert manager3.profile == "test"
    assert manager1 is not manager3


def test_get_from_config():
    """Test get_from_config helper method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.config_dir.mkdir(parents=True, exist_ok=True)

        config = Config()
        value = config_manager.get_from_config(config, "api.endpoint")
        assert value == "https://todopro.minhdq.dev/api"


def test_config_property():
    """Test config property lazy loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(profile="test")
        config_manager.config_dir = Path(tmpdir) / "config"
        config_manager.config_file = config_manager.config_dir / "test.json"
        config_manager.config_dir.mkdir(parents=True, exist_ok=True)

        # First access should load config
        config = config_manager.config
        assert isinstance(config, Config)
        
        # Second access should return cached config
        config2 = config_manager.config
        assert config is config2


def test_api_config():
    """Test API configuration."""
    config = Config()
    assert config.api.endpoint == "https://todopro.minhdq.dev/api"
    assert config.api.timeout == 30
    assert config.api.retry == 3


def test_auth_config():
    """Test auth configuration."""
    config = Config()
    assert config.auth.auto_refresh is True


def test_output_config():
    """Test output configuration."""
    config = Config()
    assert config.output.format == "pretty"
    assert config.output.color is True
    assert config.output.icons is True
    assert config.output.compact is False


def test_ui_config():
    """Test UI configuration."""
    config = Config()
    assert config.ui.interactive is False
    assert config.ui.page_size == 30
    assert config.ui.language == "en"


def test_cache_config():
    """Test cache configuration."""
    config = Config()
    assert config.cache.enabled is True
    assert config.cache.ttl == 300


def test_sync_config():
    """Test sync configuration."""
    config = Config()
    assert config.sync.auto is False
    assert config.sync.interval == 300
