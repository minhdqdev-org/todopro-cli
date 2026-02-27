"""Unit tests for StorageStrategy pattern (models/storage_strategy.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.models.storage_strategy import (
    StorageStrategy,
    StorageStrategyContext,
)


# ---------------------------------------------------------------------------
# Concrete mock strategy for testing the abstract interface
# ---------------------------------------------------------------------------


class _MockStrategy(StorageStrategy):
    """Minimal concrete strategy for testing StorageStrategyContext."""

    def __init__(self):
        self._task_repo = MagicMock(name="task_repo")
        self._project_repo = MagicMock(name="project_repo")
        self._label_repo = MagicMock(name="label_repo")
        self._context_repo = MagicMock(name="context_repo")
        self._achievement_repo = MagicMock(name="achievement_repo")
        self._section_repo = MagicMock(name="section_repo")

    def get_task_repository(self):
        return self._task_repo

    def get_project_repository(self):
        return self._project_repo

    def get_label_repository(self):
        return self._label_repo

    def get_location_context_repository(self):
        return self._context_repo

    def get_achievement_repository(self):
        return self._achievement_repo

    def get_section_repository(self):
        return self._section_repo

    @property
    def storage_type(self) -> str:
        return "mock"


# ---------------------------------------------------------------------------
# StorageStrategy abstract interface
# ---------------------------------------------------------------------------


class TestStorageStrategyAbstract:
    def test_cannot_instantiate_directly(self):
        """StorageStrategy is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StorageStrategy()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# StorageStrategyContext
# ---------------------------------------------------------------------------


class TestStorageStrategyContext:
    def setup_method(self):
        self.strategy = _MockStrategy()
        self.ctx = StorageStrategyContext(strategy=self.strategy)

    def test_task_repository_delegates_to_strategy(self):
        assert self.ctx.task_repository is self.strategy._task_repo

    def test_project_repository_delegates_to_strategy(self):
        assert self.ctx.project_repository is self.strategy._project_repo

    def test_label_repository_delegates_to_strategy(self):
        assert self.ctx.label_repository is self.strategy._label_repo

    def test_location_context_repository_delegates_to_strategy(self):
        assert self.ctx.location_context_repository is self.strategy._context_repo

    def test_achievement_repository_delegates_to_strategy(self):
        assert self.ctx.achievement_repository is self.strategy._achievement_repo

    def test_storage_type_delegates_to_strategy(self):
        assert self.ctx.storage_type == "mock"

    def test_strategy_property_returns_strategy(self):
        assert self.ctx.strategy is self.strategy

    def test_switch_strategy(self):
        new_strategy = _MockStrategy()
        self.ctx.switch_strategy(new_strategy)
        assert self.ctx.strategy is new_strategy
        assert self.ctx.task_repository is new_strategy._task_repo


# ---------------------------------------------------------------------------
# LocalStorageStrategy
# ---------------------------------------------------------------------------


class TestLocalStorageStrategy:
    def test_storage_type_is_local(self, tmp_path):
        from todopro_cli.models.storage_strategy import LocalStorageStrategy

        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        assert strategy.storage_type == "local"

    def test_get_task_repository(self, tmp_path):
        from todopro_cli.models.storage_strategy import LocalStorageStrategy

        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        repo = strategy.get_task_repository()
        assert repo is not None

    def test_get_project_repository(self, tmp_path):
        from todopro_cli.models.storage_strategy import LocalStorageStrategy

        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        repo = strategy.get_project_repository()
        assert repo is not None

    def test_get_label_repository(self, tmp_path):
        from todopro_cli.models.storage_strategy import LocalStorageStrategy

        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        repo = strategy.get_label_repository()
        assert repo is not None

    def test_get_location_context_repository(self, tmp_path):
        from todopro_cli.models.storage_strategy import LocalStorageStrategy

        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        repo = strategy.get_location_context_repository()
        assert repo is not None

    def test_get_achievement_repository_raises_not_implemented(self, tmp_path):
        from todopro_cli.models.storage_strategy import LocalStorageStrategy

        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        with pytest.raises(NotImplementedError):
            strategy.get_achievement_repository()


# ---------------------------------------------------------------------------
# RemoteStorageStrategy
# ---------------------------------------------------------------------------


class TestRemoteStorageStrategy:
    def test_storage_type_is_remote(self):
        from todopro_cli.models.storage_strategy import RemoteStorageStrategy
        from todopro_cli.adapters.rest_api import (
            RestApiLabelRepository,
            RestApiLocationContextRepository,
            RestApiProjectRepository,
            RestApiTaskRepository,
        )

        strategy = RemoteStorageStrategy()
        assert strategy.storage_type == "remote"

    def test_get_task_repository(self):
        from todopro_cli.models.storage_strategy import RemoteStorageStrategy

        strategy = RemoteStorageStrategy()
        repo = strategy.get_task_repository()
        assert repo is not None

    def test_get_project_repository(self):
        from todopro_cli.models.storage_strategy import RemoteStorageStrategy

        strategy = RemoteStorageStrategy()
        repo = strategy.get_project_repository()
        assert repo is not None

    def test_get_achievement_repository_raises_not_implemented(self):
        from todopro_cli.models.storage_strategy import RemoteStorageStrategy

        strategy = RemoteStorageStrategy()
        with pytest.raises(NotImplementedError):
            strategy.get_achievement_repository()


class TestRemoteStorageStrategyAdditional:
    def test_get_label_repository(self):
        """Covers RemoteStorageStrategy.get_label_repository() (line 147)."""
        from todopro_cli.models.storage_strategy import RemoteStorageStrategy

        strategy = RemoteStorageStrategy()
        repo = strategy.get_label_repository()
        assert repo is not None

    def test_get_location_context_repository(self):
        """Covers RemoteStorageStrategy.get_location_context_repository() (line 150)."""
        from todopro_cli.models.storage_strategy import RemoteStorageStrategy

        strategy = RemoteStorageStrategy()
        repo = strategy.get_location_context_repository()
        assert repo is not None
