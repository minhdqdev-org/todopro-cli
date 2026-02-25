"""Tests for configuration management."""

from todopro_cli.models.config_models import AppConfig


def test_default_config():
    """Test default configuration."""
    config = AppConfig()
    assert config.api.endpoint == "https://todopro.minhdq.dev/api"
    assert config.api.timeout == 30
    assert config.output.format == "pretty"
    assert config.cache.enabled is True


def test_api_config():
    """Test API configuration."""
    config = AppConfig()
    assert config.api.endpoint == "https://todopro.minhdq.dev/api"
    assert config.api.timeout == 30
    assert config.api.retry == 3


def test_auth_config():
    """Test auth configuration."""
    config = AppConfig()
    assert config.auth.auto_refresh is True


def test_output_config():
    """Test output configuration."""
    config = AppConfig()
    assert config.output.format == "pretty"
    assert config.output.color is True
    assert config.output.icons is True
    assert config.output.compact is False


def test_ui_config():
    """Test UI configuration."""
    config = AppConfig()
    assert config.ui.interactive is False
    assert config.ui.page_size == 30
    assert config.ui.language == "en"


def test_cache_config():
    """Test cache configuration."""
    config = AppConfig()
    assert config.cache.enabled is True
    assert config.cache.ttl == 300


def test_sync_config():
    """Test sync configuration."""
    config = AppConfig()
    assert config.sync.auto is False
    assert config.sync.interval == 300
