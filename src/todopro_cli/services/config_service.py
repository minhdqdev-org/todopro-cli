"""Configuration service for managing TodoPro CLI configuration.

This module provides the ConfigService class, which is the single source of truth
for all configuration management in TodoPro CLI. It handles:

- Loading and saving config.json
- Context management (list, add, remove, switch, rename)
- Credential management for remote contexts
- Config file initialization with sensible defaults
"""

from __future__ import annotations

import json
from functools import lru_cache
from json import JSONDecodeError
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

from todopro_cli.models.config_models import AppConfig, Context
from todopro_cli.models.storage_strategy import (
    LocalStorageStrategy,
    RemoteStorageStrategy,
    StorageStrategyContext,
)


class ConfigService:
    """Service for managing application configuration.

    This service provides methods to load, save, and manipulate the application's
    configuration settings. It abstracts away the underlying storage mechanism
    (e.g., file system, database) and provides a clean interface for other parts
    of the application to interact with configuration data.
    """

    def __init__(self):
        """Initialize the config service."""

        self.config_dir = Path(user_config_dir("todopro_cli"))
        self.config_path = self.config_dir / "config.json"
        self.credentials_dir = self.config_dir / "credentials"
        self.data_dir = Path(user_data_dir("todopro_cli"))

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        self._config: AppConfig | None = None

        self._storage_strategy_context: StorageStrategyContext | None = None

    @property
    def config(self) -> AppConfig:
        """Get or load the current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    @property
    def storage_strategy_context(self) -> StorageStrategyContext:
        """Get a StorageStrategyContext based on the current configuration."""
        assert self._storage_strategy_context is not None, (
            "StorageStrategyContext should be initialized"
        )
        return self._storage_strategy_context

    def load_config(self) -> AppConfig:
        """Load configuration from storage."""
        if self._config is not None:
            return self._config  # Return cached config if already loaded

        try:
            with open(self.config_path, encoding="utf-8") as f:
                raw = f.read()
                self._config = AppConfig.model_validate_json(raw)

                # Persist a freshly-generated client_id for configs written
                # before the field existed, so it stays stable across runs.
                if "client_id" not in raw:
                    self.save_config()

                # After loading config, initialize the storage strategy context
                context = self.get_current_context()
                if context.type == "remote":
                    strategy = RemoteStorageStrategy()
                else:
                    strategy = LocalStorageStrategy(db_path=context.source)
                self._storage_strategy_context = StorageStrategyContext(strategy)

        except FileNotFoundError:
            # Config file doesn't exist yet - create default config
            # This is expected on first run
            self._config = self.create_default_cloud_config()
            self._storage_strategy_context = StorageStrategyContext(
                strategy=RemoteStorageStrategy()
            )
            self.save_config()
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}") from e

        return self.config

    def save_config(self):
        """Save the current configuration to storage."""
        if self.config is None:
            raise RuntimeError("No configuration to save")

        try:
            # save as JSON
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(self.config.model_dump_json(indent=4))

            # Set file permissions
            self.config_path.chmod(0o600)
        except Exception as e:
            raise RuntimeError(f"Failed to save config: {e}") from e

    def reset_config(self):
        """Reset configuration to defaults."""
        self._config = None
        self._storage_strategy_context = None
        if self.config_path.exists():
            self.config_path.unlink()
        # Also clear credentials
        for cred_file in self.credentials_dir.glob("*.json"):
            cred_file.unlink()
        # Recreate default config and storage context
        self.create_default_cloud_config()
        context = self.get_current_context()
        if context.type == "remote":
            strategy = RemoteStorageStrategy()
        else:
            strategy = LocalStorageStrategy(db_path=context.source)
        self._storage_strategy_context = StorageStrategyContext(strategy)

    def create_default_cloud_config(self) -> AppConfig:
        """Create a default configuration with local context.

        Note: Despite the name, this now creates LOCAL context by default
        for better first-run experience. Users don't need authentication
        to get started.
        """
        # Create local context as default (better UX - no auth required)
        local_db_path = str(self.data_dir / "todopro.db")
        local_context = Context(
            name="local",
            type="local",
            source=local_db_path,
            description="Local SQLite storage",
        )

        # Also add cloud context for easy switching later
        cloud_context = Context(
            name="cloud",
            type="remote",
            source="https://todopro.minhdq.dev/api",
            description="TodoPro Cloud (requires login)",
        )

        self._config = AppConfig(
            current_context_name=local_context.name,
            contexts=[local_context, cloud_context],
        )
        self.save_config()
        return self._config

    def list_contexts(self) -> list[Context]:
        """List all available contexts."""
        return self.config.contexts

    def get_current_context(self) -> Context:
        """Get the currently active context.

        Returns:
            Context: The active context

        Raises:
            ValueError: If no context is configured or current context not found
        """
        return self.config.get_current_context()

    def get_context(self, name: str) -> Context | None:
        """Get a context by name, or None if it doesn't exist.

        Unlike ``AppConfig.get_context`` (which raises), this returns ``None`` so
        callers can cheaply test for existence (e.g. ``context create``).
        """
        try:
            return self.config.get_context(name)
        except ValueError:
            return None

    def use_context(self, name: str) -> Context:
        """Set the current context by name."""

        context = self.config.get_context(name)
        self.config.current_context_name = context.name
        self.save_config()
        return context

    def add_context(self, context: Context):
        """Add a new context to the configuration."""

        self.config.add_context(context)
        self.save_config()

    def remove_context(self, name: str):
        """Remove a context from the configuration."""

        self.config.remove_context(name)
        self.save_config()
        self.remove_context_credentials(name)

    def remove_context_credentials(self, context_name: str):
        """Remove credentials associated with a context."""
        cred_path = self.credentials_dir / f"{context_name}.json"
        if cred_path.exists():
            cred_path.unlink()

    def rename_context(self, old_name: str, new_name: str):
        """Rename a context in the configuration."""

        self.config.rename_context(old_name, new_name)
        self.save_config()

        # Also rename credentials file if it exists
        old_cred_path = self.credentials_dir / f"{old_name}.json"
        new_cred_path = self.credentials_dir / f"{new_name}.json"
        if old_cred_path.exists():
            old_cred_path.rename(new_cred_path)

    def load_credentials(self) -> dict | None:
        """Load credentials for the current context.

        Returns:
            dict with 'token' and optionally 'refresh_token', or None if not found
        """
        try:
            current_context = self.config.get_current_context()
            return self.load_context_credentials(current_context.name)
        except (ValueError, FileNotFoundError):
            return None

    def load_context_credentials(self, context_name: str) -> dict | None:
        """Load credentials for a specific context.

        Args:
            context_name: Name of the context

        Returns:
            dict with 'token' and optionally 'refresh_token', or None if not found
        """

        cred_path = self.credentials_dir / f"{context_name}.json"
        if not cred_path.exists():
            return None

        try:
            with open(cred_path, encoding="utf-8") as f:
                return json.load(f)
        except JSONDecodeError:
            return None

    def save_credentials(
        self,
        access_token: str,
        refresh_token: str | None = None,
        context_name: str | None = None,
    ):
        """Save credentials for a context.

        Args:
            access_token: The access token (JWT)
            refresh_token: Optional refresh token
            context_name: Context name (defaults to current context)
        """

        if context_name is None:
            current_context = self.config.get_current_context()
            context_name = current_context.name

        cred_data = {"token": access_token}
        if refresh_token:
            cred_data["refresh_token"] = refresh_token

        cred_path = self.credentials_dir / f"{context_name}.json"
        cred_path.parent.mkdir(parents=True, exist_ok=True)

        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(cred_data, f, indent=2)

        # Set secure file permissions
        cred_path.chmod(0o600)

    def clear_credentials(self, context_name: str | None = None) -> None:
        """Clear credentials for a context.

        Args:
            context_name: Context name (defaults to current context)
        """
        if context_name is None:
            try:
                current_context = self.config.get_current_context()
                context_name = current_context.name
            except (ValueError, KeyError):
                return
        self.remove_context_credentials(context_name)

    # Alias kept for callers that use the older name.
    def clear_context_credentials(self, context_name: str) -> None:
        """Remove credentials associated with a context (alias)."""
        self.remove_context_credentials(context_name)

    # ----- dotted-path config access (e.g. "api.endpoint") -------------------
    def get(self, key: str) -> object | None:
        """Read a config value by dotted path, e.g. ``get("api.endpoint")``.

        Returns ``None`` if any segment of the path is missing.
        """
        node: object = self.config
        for part in key.split("."):
            if node is None:
                return None
            node = getattr(node, part, None)
        return node

    def set(self, key: str, value: object) -> None:
        """Set a config value by dotted path and persist it.

        e.g. ``set("api.endpoint", "http://localhost:8000/api")``.
        """
        parts = key.split(".")
        node: object = self.config
        for part in parts[:-1]:
            node = getattr(node, part)
        leaf = parts[-1]
        if not hasattr(node, leaf):
            raise ValueError(f"Unknown configuration key '{key}'")
        setattr(node, leaf, value)
        self.save_config()

    def reset(self, key: str | None = None) -> None:
        """Reset the whole config, or a single dotted key to its default."""
        if not key:
            self.reset_config()
            return
        # Read the field's default from a fresh AppConfig instance.
        default_node: object = AppConfig()
        for part in key.split("."):
            default_node = getattr(default_node, part, None)
        self.set(key, default_node)

    def set_endpoint(self, url: str) -> None:
        """Point the active remote context (and api.endpoint) at ``url``.

        Used by ``auth login/signup --endpoint``. Updating the current context's
        source is what actually changes request routing (the API client reads the
        active remote context's source first); api.endpoint is kept in sync as a
        fallback for callers not using contexts.
        """
        url = url.rstrip("/")
        try:
            current = self.config.get_current_context()
            if current is not None and current.type == "remote":
                current.source = url
        except ValueError:
            pass
        self.config.api.endpoint = url
        self.save_config()

    def init_default_contexts(self) -> None:
        """Ensure the default local + cloud contexts exist (no-op if present)."""
        if not self.config.contexts:
            self.create_default_cloud_config()


@lru_cache(maxsize=1)
def get_config_service() -> ConfigService:
    """Get a cached ConfigService instance."""
    config_service = ConfigService()
    config_service.load_config()  # Ensure config is loaded and storage context initialized
    return config_service


def get_storage_strategy_context() -> StorageStrategyContext:
    """Get a StorageStrategyContext based on the current configuration."""
    config_service = get_config_service()
    return config_service.storage_strategy_context
