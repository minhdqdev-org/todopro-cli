"""Configuration management for TodoPro CLI."""

import json
from pathlib import Path
from typing import Any, Optional

from platformdirs import user_config_dir, user_data_dir
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API configuration."""

    endpoint: str = Field(default="https://todopro.minhdq.dev/api")
    timeout: int = Field(default=30)
    retry: int = Field(default=3)


class AuthConfig(BaseModel):
    """Authentication configuration."""

    auto_refresh: bool = Field(default=True)


class OutputConfig(BaseModel):
    """Output configuration."""

    format: str = Field(default="table")
    color: bool = Field(default=True)
    wide: bool = Field(default=False)


class UIConfig(BaseModel):
    """UI configuration."""

    interactive: bool = Field(default=False)
    page_size: int = Field(default=30)
    language: str = Field(default="en")
    timezone: str = Field(default="UTC")


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True)
    ttl: int = Field(default=300)


class SyncConfig(BaseModel):
    """Sync configuration."""

    auto: bool = Field(default=False)
    interval: int = Field(default=300)


class Config(BaseModel):
    """Main configuration."""

    api: APIConfig = Field(default_factory=APIConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)


class ConfigManager:
    """Manages TodoPro CLI configuration."""

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.config_dir = Path(user_config_dir("todopro-cli"))
        self.data_dir = Path(user_data_dir("todopro-cli"))
        self.config_file = self.config_dir / f"{profile}.json"
        self.credentials_file = self.data_dir / f"{profile}.credentials.json"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._config: Optional[Config] = None

    @property
    def config(self) -> Config:
        """Get the current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def load_config(self) -> Config:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                return Config(**data)
            except Exception:
                # If config is corrupted, return default
                return Config()
        return Config()

    def save_config(self, config: Optional[Config] = None) -> None:
        """Save configuration to file."""
        if config is None:
            config = self.config

        with open(self.config_file, "w") as f:
            json.dump(config.model_dump(), f, indent=2)

    def get(self, key: str) -> Any:
        """Get a configuration value by dot-separated key."""
        keys = key.split(".")
        value: Any = self.config
        for k in keys:
            if isinstance(value, BaseModel):
                value = getattr(value, k, None)
            else:
                return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot-separated key."""
        keys = key.split(".")
        config_dict = self.config.model_dump()

        # Navigate to the nested dictionary
        current = config_dict
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        # Reload config from the modified dictionary
        self._config = Config(**config_dict)
        self.save_config()

    def reset(self, key: Optional[str] = None) -> None:
        """Reset configuration to defaults."""
        if key is None:
            self._config = Config()
        else:
            # Reset specific key to default
            default_config = Config()
            default_value = self.get_from_config(default_config, key)
            if default_value is not None:
                self.set(key, default_value)
        self.save_config()

    def get_from_config(self, config: Config, key: str) -> Any:
        """Get value from a config object using dot notation."""
        keys = key.split(".")
        value: Any = config
        for k in keys:
            if isinstance(value, BaseModel):
                value = getattr(value, k, None)
            else:
                return None
        return value

    def save_credentials(self, token: str, refresh_token: Optional[str] = None) -> None:
        """Save authentication credentials."""
        credentials = {"token": token}
        if refresh_token:
            credentials["refresh_token"] = refresh_token

        with open(self.credentials_file, "w") as f:
            json.dump(credentials, f, indent=2)

        # Set file permissions to be readable only by owner
        self.credentials_file.chmod(0o600)

    def load_credentials(self) -> Optional[dict[str, str]]:
        """Load authentication credentials."""
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def clear_credentials(self) -> None:
        """Clear authentication credentials."""
        if self.credentials_file.exists():
            self.credentials_file.unlink()

    def list_profiles(self) -> list[str]:
        """List all available profiles."""
        profiles = []
        for config_file in self.config_dir.glob("*.json"):
            if not config_file.name.startswith("."):
                profiles.append(config_file.stem)
        return profiles


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(profile: str = "default") -> ConfigManager:
    """Get or create the global config manager."""
    global _config_manager
    if _config_manager is None or _config_manager.profile != profile:
        _config_manager = ConfigManager(profile)
    return _config_manager
