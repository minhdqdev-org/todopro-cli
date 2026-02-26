"""Shared test fixtures and configuration.

Provides infrastructure to isolate tests from real filesystem/API state.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.models.config_models import AppConfig, Context


# ---------------------------------------------------------------------------
# Config isolation helpers
# ---------------------------------------------------------------------------


def _make_local_config(tmp_path) -> AppConfig:
    """Build a minimal AppConfig pointing at a tmp SQLite database."""
    db = str(tmp_path / "test.db")
    ctx = Context(name="default", type="local", source=db)
    config = AppConfig(current_context_name="default", contexts=[ctx])
    return config


@pytest.fixture()
def tmp_config(tmp_path):
    """Provide a real ConfigService backed by a temporary directory.

    Patches platform dirs so config/data files land in *tmp_path* only.
    Also clears the lru_cache so each test gets a fresh service instance.
    """
    from todopro_cli.services.config_service import get_config_service

    tmpdir = str(tmp_path)
    get_config_service.cache_clear()
    with patch("todopro_cli.services.config_service.user_config_dir", return_value=tmpdir):
        with patch("todopro_cli.services.config_service.user_data_dir", return_value=tmpdir):
            from todopro_cli.services.config_service import ConfigService

            svc = ConfigService()
            yield svc
    get_config_service.cache_clear()


@pytest.fixture()
def mock_config_service(tmp_path):
    """Provide a MagicMock that stands in for get_config_service().

    The mock's .load_config() returns a local AppConfig and .config property
    mirrors the same object so it can be safely used by commands/models.
    """
    config = _make_local_config(tmp_path)

    svc = MagicMock()
    svc.load_config.return_value = config
    svc.config = config
    svc.save_config = MagicMock()
    svc.get_current_context.return_value = config.contexts[0]

    return svc


@pytest.fixture(autouse=False)
def patch_config_service(mock_config_service):
    """Autouse=False convenience: patch get_config_service globally.

    Use explicitly in test classes/functions that need the full injection:
        @pytest.mark.usefixtures('patch_config_service')
    """
    from todopro_cli.services.config_service import get_config_service

    get_config_service.cache_clear()
    with patch(
        "todopro_cli.services.config_service.get_config_service",
        return_value=mock_config_service,
    ):
        with patch(
            "todopro_cli.commands.decorators.get_config_service",
            return_value=mock_config_service,
        ):
            yield mock_config_service
    get_config_service.cache_clear()


# ---------------------------------------------------------------------------
# Auth bypass
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def bypass_auth():
    """Skip authentication checks in all tests by default."""
    with patch("todopro_cli.commands.decorators._require_auth"):
        yield
