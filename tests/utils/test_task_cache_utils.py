"""Unit tests for utils/task_cache.py (backward-compatibility wrappers)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestGetSuffixMapping:
    def test_calls_cache_service_get_suffix_mapping(self):
        """get_suffix_mapping delegates to cache_service._get()."""
        fake_mapping = {"abc": "full-uuid-abc-123"}

        with patch(
            "todopro_cli.services.cache_service.get_suffix_mapping",
            return_value=fake_mapping,
        ):
            from todopro_cli.utils.task_cache import get_suffix_mapping

            result = get_suffix_mapping()
            assert result == fake_mapping

    def test_returns_dict(self):
        """Return type is always a dict."""
        with patch(
            "todopro_cli.services.cache_service.get_suffix_mapping",
            return_value={},
        ):
            from todopro_cli.utils import task_cache

            # Force reimport to avoid cached module
            import importlib

            importlib.reload(task_cache)
            result = task_cache.get_suffix_mapping()
            assert isinstance(result, dict)


class TestGetBackgroundCache:
    def test_calls_cache_service_get_background_cache(self):
        """get_background_cache delegates to cache_service._get()."""
        fake_cache = MagicMock()
        fake_cache.is_being_completed.return_value = True

        with patch(
            "todopro_cli.services.cache_service.get_background_cache",
            return_value=fake_cache,
        ):
            from todopro_cli.utils.task_cache import get_background_cache

            cache = get_background_cache()
            assert cache is fake_cache

    def test_returns_cache_object(self):
        """Return value is the same object from cache_service."""
        fake_cache = MagicMock()

        with patch(
            "todopro_cli.services.cache_service.get_background_cache",
            return_value=fake_cache,
        ):
            from todopro_cli.utils import task_cache
            import importlib

            importlib.reload(task_cache)
            result = task_cache.get_background_cache()
            assert result is fake_cache
