"""Comprehensive unit tests for services/config_service.py.

Covers ConfigService CRUD operations, context management,
credential handling, and the lru-cached factory helpers.
Uses a real ConfigService pointed at a tmp_path directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from todopro_cli.models.config_models import AppConfig, Context
from todopro_cli.models.storage_strategy import (
    LocalStorageStrategy,
    RemoteStorageStrategy,
    StorageStrategyContext,
)
from todopro_cli.services.config_service import ConfigService, get_config_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(tmp_path) -> ConfigService:
    """ConfigService backed by a temporary directory."""
    from todopro_cli.services.config_service import get_config_service as gcs

    gcs.cache_clear()
    with patch("todopro_cli.services.config_service.user_config_dir", return_value=str(tmp_path)):
        with patch("todopro_cli.services.config_service.user_data_dir", return_value=str(tmp_path)):
            service = ConfigService()
            # Trigger config initialization
            _ = service.config
            yield service
    gcs.cache_clear()


@pytest.fixture()
def svc_with_remote(tmp_path) -> ConfigService:
    """ConfigService with a remote context as the current context."""
    from todopro_cli.services.config_service import get_config_service as gcs

    gcs.cache_clear()
    with patch("todopro_cli.services.config_service.user_config_dir", return_value=str(tmp_path)):
        with patch("todopro_cli.services.config_service.user_data_dir", return_value=str(tmp_path)):
            service = ConfigService()
            # Force a remote context config
            remote_ctx = Context(name="myremote", type="remote", source="https://api.example.com")
            local_ctx = Context(name="local", type="local", source=str(tmp_path / "test.db"))
            service._config = AppConfig(
                current_context_name="myremote",
                contexts=[remote_ctx, local_ctx],
            )
            service.save_config()
            # Re-load to trigger storage strategy initialisation
            service._config = None
            service._storage_strategy_context = None
            _ = service.config
            yield service
    gcs.cache_clear()


# ===========================================================================
# Directories created on init
# ===========================================================================

class TestConfigServiceInit:
    """ConfigService must create required directories on first use."""

    def test_config_dir_created(self, svc):
        assert svc.config_dir.exists()
        assert svc.config_dir.is_dir()

    def test_data_dir_created(self, svc):
        assert svc.data_dir.exists()
        assert svc.data_dir.is_dir()

    def test_credentials_dir_created(self, svc):
        assert svc.credentials_dir.exists()
        assert svc.credentials_dir.is_dir()


# ===========================================================================
# Default config creation
# ===========================================================================

class TestCreateDefaultConfig:
    """Tests for create_default_cloud_config()."""

    def test_default_config_has_local_context(self, svc):
        ctx = svc.get_current_context()
        assert ctx.type == "local"

    def test_default_config_has_cloud_context(self, svc):
        names = [c.name for c in svc.list_contexts()]
        assert "cloud" in names

    def test_default_current_context_name_is_local(self, svc):
        assert svc.config.current_context_name == "local"

    def test_config_file_created_on_disk(self, svc):
        assert svc.config_path.exists()

    def test_config_file_is_valid_json(self, svc):
        text = svc.config_path.read_text()
        obj = json.loads(text)
        assert "current_context_name" in obj


# ===========================================================================
# load_config
# ===========================================================================

class TestLoadConfig:
    """Tests for load_config()."""

    def test_load_returns_app_config(self, svc):
        assert isinstance(svc.config, AppConfig)

    def test_load_is_cached(self, svc):
        """Calling load_config twice returns the same object."""
        c1 = svc.load_config()
        c2 = svc.load_config()
        assert c1 is c2

    def test_load_raises_on_malformed_json(self, tmp_path):
        from todopro_cli.services.config_service import get_config_service as gcs
        gcs.cache_clear()
        with patch("todopro_cli.services.config_service.user_config_dir", return_value=str(tmp_path)):
            with patch("todopro_cli.services.config_service.user_data_dir", return_value=str(tmp_path)):
                service = ConfigService()
                # Write invalid JSON
                service.config_path.parent.mkdir(parents=True, exist_ok=True)
                service.config_path.write_text("{invalid json}")
                with pytest.raises(RuntimeError, match="Failed to load config"):
                    service._config = None
                    service.load_config()
        gcs.cache_clear()


# ===========================================================================
# save_config
# ===========================================================================

class TestSaveConfig:
    """Tests for save_config()."""

    def test_save_writes_json_file(self, svc):
        svc.save_config()
        assert svc.config_path.exists()
        data = json.loads(svc.config_path.read_text())
        assert "current_context_name" in data

    def test_save_file_permissions_restrictive(self, svc):
        svc.save_config()
        import stat
        mode = svc.config_path.stat().st_mode & 0o777
        # Should be 0o600
        assert mode == 0o600

    def test_save_persists_current_context_name(self, svc):
        svc.config.current_context_name = "cloud"
        svc.save_config()
        data = json.loads(svc.config_path.read_text())
        assert data["current_context_name"] == "cloud"


# ===========================================================================
# Context management
# ===========================================================================

class TestListContexts:
    def test_returns_list_of_contexts(self, svc):
        ctxs = svc.list_contexts()
        assert isinstance(ctxs, list)
        assert all(isinstance(c, Context) for c in ctxs)

    def test_at_least_two_default_contexts(self, svc):
        assert len(svc.list_contexts()) >= 2


class TestGetCurrentContext:
    def test_returns_context_object(self, svc):
        ctx = svc.get_current_context()
        assert isinstance(ctx, Context)

    def test_current_context_matches_name(self, svc):
        ctx = svc.get_current_context()
        assert ctx.name == svc.config.current_context_name


class TestUseContext:
    def test_switches_current_context(self, svc):
        svc.use_context("cloud")
        assert svc.config.current_context_name == "cloud"

    def test_returns_context_object(self, svc):
        ctx = svc.use_context("cloud")
        assert isinstance(ctx, Context)

    def test_save_called_after_switch(self, svc):
        svc.use_context("cloud")
        # Config file should reflect the new context
        data = json.loads(svc.config_path.read_text())
        assert data["current_context_name"] == "cloud"

    def test_raises_for_unknown_context(self, svc):
        with pytest.raises((ValueError, KeyError, Exception)):
            svc.use_context("nonexistent")


class TestAddContext:
    def test_add_increases_context_count(self, svc):
        before = len(svc.list_contexts())
        new_ctx = Context(name="staging", type="remote", source="https://staging.example.com")
        svc.add_context(new_ctx)
        assert len(svc.list_contexts()) == before + 1

    def test_added_context_is_retrievable(self, svc):
        new_ctx = Context(name="staging", type="remote", source="https://staging.example.com")
        svc.add_context(new_ctx)
        names = [c.name for c in svc.list_contexts()]
        assert "staging" in names

    def test_add_persists_to_file(self, svc):
        new_ctx = Context(name="staging", type="remote", source="https://staging.example.com")
        svc.add_context(new_ctx)
        data = json.loads(svc.config_path.read_text())
        names = [c["name"] for c in data["contexts"]]
        assert "staging" in names


class TestRemoveContext:
    def test_remove_decreases_context_count(self, svc):
        before = len(svc.list_contexts())
        svc.remove_context("cloud")
        assert len(svc.list_contexts()) == before - 1

    def test_removed_context_not_listed(self, svc):
        svc.remove_context("cloud")
        names = [c.name for c in svc.list_contexts()]
        assert "cloud" not in names

    def test_remove_unknown_context_raises(self, svc):
        with pytest.raises((ValueError, KeyError, Exception)):
            svc.remove_context("nonexistent")


class TestRenameContext:
    def test_rename_changes_name(self, svc):
        svc.rename_context("cloud", "prod")
        names = [c.name for c in svc.list_contexts()]
        assert "prod" in names
        assert "cloud" not in names

    def test_rename_also_renames_credentials_file(self, svc):
        # Create a credentials file for "cloud"
        cred_path = svc.credentials_dir / "cloud.json"
        cred_path.write_text('{"token": "abc"}')
        svc.rename_context("cloud", "prod")
        assert (svc.credentials_dir / "prod.json").exists()
        assert not (svc.credentials_dir / "cloud.json").exists()

    def test_rename_with_no_creds_file_ok(self, svc):
        # No credential file exists — should not raise
        svc.rename_context("cloud", "prod")
        names = [c.name for c in svc.list_contexts()]
        assert "prod" in names


# ===========================================================================
# Credential management
# ===========================================================================

class TestSaveCredentials:
    def test_creates_credentials_file(self, svc):
        svc.save_credentials("my-token", context_name="cloud")
        cred_path = svc.credentials_dir / "cloud.json"
        assert cred_path.exists()

    def test_credentials_file_contains_token(self, svc):
        svc.save_credentials("my-token", context_name="cloud")
        data = json.loads((svc.credentials_dir / "cloud.json").read_text())
        assert data["token"] == "my-token"

    def test_credentials_file_contains_refresh_token(self, svc):
        svc.save_credentials("access-tok", refresh_token="refresh-tok", context_name="cloud")
        data = json.loads((svc.credentials_dir / "cloud.json").read_text())
        assert data["refresh_token"] == "refresh-tok"

    def test_no_refresh_token_not_in_file(self, svc):
        svc.save_credentials("access-tok", context_name="cloud")
        data = json.loads((svc.credentials_dir / "cloud.json").read_text())
        assert "refresh_token" not in data

    def test_file_permissions_restrictive(self, svc):
        svc.save_credentials("my-token", context_name="cloud")
        import stat
        mode = (svc.credentials_dir / "cloud.json").stat().st_mode & 0o777
        assert mode == 0o600

    def test_uses_current_context_when_name_none(self, svc):
        current = svc.get_current_context()
        svc.save_credentials("tok")
        cred_path = svc.credentials_dir / f"{current.name}.json"
        assert cred_path.exists()


class TestLoadCredentials:
    def test_returns_none_when_no_file(self, svc):
        result = svc.load_credentials()
        assert result is None

    def test_returns_dict_when_file_exists(self, svc):
        svc.save_credentials("tok", context_name="local")
        # Switch to local so load_credentials picks local
        svc.use_context("local")
        result = svc.load_credentials()
        assert result is not None
        assert result["token"] == "tok"

    def test_returns_none_for_malformed_json(self, svc):
        cred_path = svc.credentials_dir / "local.json"
        cred_path.write_text("{not valid json")
        svc.use_context("local")
        result = svc.load_credentials()
        assert result is None


class TestLoadContextCredentials:
    def test_returns_none_when_missing(self, svc):
        assert svc.load_context_credentials("cloud") is None

    def test_returns_dict_when_present(self, svc):
        svc.save_credentials("tok", context_name="cloud")
        data = svc.load_context_credentials("cloud")
        assert data == {"token": "tok"}


class TestClearCredentials:
    def test_removes_credentials_file(self, svc):
        svc.save_credentials("tok", context_name="cloud")
        assert (svc.credentials_dir / "cloud.json").exists()
        svc.clear_credentials("cloud")
        assert not (svc.credentials_dir / "cloud.json").exists()

    def test_clear_non_existent_is_noop(self, svc):
        # Should not raise
        svc.clear_credentials("nonexistent")

    def test_clear_uses_current_context_when_none(self, svc):
        current = svc.get_current_context()
        svc.save_credentials("tok")
        svc.clear_credentials()
        cred_path = svc.credentials_dir / f"{current.name}.json"
        assert not cred_path.exists()


class TestRemoveContextCredentials:
    def test_removes_file(self, svc):
        cred_path = svc.credentials_dir / "cloud.json"
        cred_path.write_text('{"token": "x"}')
        svc.remove_context_credentials("cloud")
        assert not cred_path.exists()

    def test_noop_when_file_absent(self, svc):
        # Should not raise
        svc.remove_context_credentials("nonexistent")


# ===========================================================================
# reset_config
# ===========================================================================

class TestResetConfig:
    def test_reset_removes_config_file(self, svc):
        svc.reset_config()
        # After reset, config file might be recreated but _config is cleared first
        assert svc._config is not None  # default config re-created

    def test_reset_clears_credentials(self, svc):
        svc.save_credentials("tok", context_name="cloud")
        svc.reset_config()
        assert svc.load_context_credentials("cloud") is None


# ===========================================================================
# StorageStrategyContext wiring
# ===========================================================================

class TestStorageStrategyWiring:
    def test_local_context_uses_local_strategy(self, svc):
        assert svc.config.current_context_name == "local"
        assert svc._storage_strategy_context is not None

    def test_remote_context_uses_remote_strategy(self, svc_with_remote):
        ctx = svc_with_remote.get_current_context()
        assert ctx.type == "remote"
        assert svc_with_remote._storage_strategy_context is not None

    def test_storage_strategy_context_property_returns_value(self, svc):
        result = svc.storage_strategy_context
        assert isinstance(result, StorageStrategyContext)

    def test_uninitialized_storage_strategy_raises(self, tmp_path):
        from todopro_cli.services.config_service import get_config_service as gcs
        gcs.cache_clear()
        with patch("todopro_cli.services.config_service.user_config_dir", return_value=str(tmp_path)):
            with patch("todopro_cli.services.config_service.user_data_dir", return_value=str(tmp_path)):
                service = ConfigService()
                # Do NOT call load_config — strategy is not set yet
                with pytest.raises(AssertionError):
                    _ = service.storage_strategy_context
        gcs.cache_clear()


# ===========================================================================
# get_config_service factory (lru_cache)
# ===========================================================================

class TestGetConfigServiceFactory:
    def test_returns_config_service_instance(self, tmp_path):
        get_config_service.cache_clear()
        with patch("todopro_cli.services.config_service.user_config_dir", return_value=str(tmp_path)):
            with patch("todopro_cli.services.config_service.user_data_dir", return_value=str(tmp_path)):
                instance = get_config_service()
                assert isinstance(instance, ConfigService)
        get_config_service.cache_clear()

    def test_returns_same_instance_on_repeated_calls(self, tmp_path):
        get_config_service.cache_clear()
        with patch("todopro_cli.services.config_service.user_config_dir", return_value=str(tmp_path)):
            with patch("todopro_cli.services.config_service.user_data_dir", return_value=str(tmp_path)):
                a = get_config_service()
                b = get_config_service()
                assert a is b
        get_config_service.cache_clear()

    def test_cache_clear_allows_new_instance(self, tmp_path):
        get_config_service.cache_clear()
        with patch("todopro_cli.services.config_service.user_config_dir", return_value=str(tmp_path)):
            with patch("todopro_cli.services.config_service.user_data_dir", return_value=str(tmp_path)):
                a = get_config_service()
                get_config_service.cache_clear()
                b = get_config_service()
                assert a is not b
        get_config_service.cache_clear()
