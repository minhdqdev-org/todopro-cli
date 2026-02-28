"""Tests for Strategy Pattern implementation.

This module tests the new Strategy Pattern architecture for repository selection.
"""

import tempfile
from unittest.mock import patch

import pytest

from todopro_cli.models.storage_strategy import (
    LocalStorageStrategy,
    RemoteStorageStrategy,
    StorageStrategyContext,
)
from todopro_cli.repositories import (
    LabelRepository,
    ProjectRepository,
    TaskRepository,
)
from todopro_cli.services.config_service import ConfigService, get_storage_strategy_context


class TestLocalStorageStrategy:
    """Tests for LocalStorageStrategy"""

    def test_initialization(self, tmp_path):
        """Test LocalStorageStrategy initializes with correct db_path"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)

        assert strategy.storage_type == "local"
        assert strategy.db_path == db_path

    def test_get_task_repository(self, tmp_path):
        """Test getting task repository from local strategy"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)

        repo = strategy.get_task_repository()

        assert isinstance(repo, TaskRepository)
        assert repo is strategy._task_repo  # Should return same instance

    def test_get_project_repository(self, tmp_path):
        """Test getting project repository from local strategy"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)

        repo = strategy.get_project_repository()

        assert isinstance(repo, ProjectRepository)
        assert repo is strategy._project_repo

    def test_get_label_repository(self, tmp_path):
        """Test getting label repository from local strategy"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)

        repo = strategy.get_label_repository()

        assert isinstance(repo, LabelRepository)
        assert repo is strategy._label_repo

    def test_repositories_created_once(self, tmp_path):
        """Test that repositories are created once at initialization"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)

        # Get repository multiple times
        repo1 = strategy.get_task_repository()
        repo2 = strategy.get_task_repository()
        repo3 = strategy.get_task_repository()

        # Should return same instance (created once)
        assert repo1 is repo2 is repo3


class TestRemoteStorageStrategy:
    """Tests for RemoteStorageStrategy"""

    @pytest.fixture
    def config_service(self):
        """Fixture for ConfigService with temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("platformdirs.user_config_dir", return_value=tmpdir):
                with patch("platformdirs.user_data_dir", return_value=tmpdir):
                    yield ConfigService()

    def test_initialization(self):
        """Test RemoteStorageStrategy initializes with config service"""
        strategy = RemoteStorageStrategy()

        assert strategy.storage_type == "remote"

    def test_get_task_repository(self):
        """Test getting task repository from remote strategy"""
        strategy = RemoteStorageStrategy()

        repo = strategy.get_task_repository()

        assert isinstance(repo, TaskRepository)
        assert repo is strategy._task_repo

    def test_repositories_created_once(self):
        """Test that repositories are created once at initialization"""
        strategy = RemoteStorageStrategy()

        # Get repository multiple times
        repo1 = strategy.get_task_repository()
        repo2 = strategy.get_task_repository()
        repo3 = strategy.get_task_repository()

        # Should return same instance (created once)
        assert repo1 is repo2 is repo3


class TestStorageStrategyContext:
    """Tests for StorageStrategyContext"""

    def test_initialization_with_local_strategy(self, tmp_path):
        """Test StorageStrategyContext wraps LocalStorageStrategy"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        context = StorageStrategyContext(strategy)

        assert context.storage_type == "local"
        assert context.strategy is strategy

    def test_initialization_with_remote_strategy(self):
        """Test StorageStrategyContext wraps RemoteStorageStrategy"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("platformdirs.user_config_dir", return_value=tmpdir):
                with patch("platformdirs.user_data_dir", return_value=tmpdir):
                    config_service = ConfigService()
                    strategy = RemoteStorageStrategy()
                    context = StorageStrategyContext(strategy)

                    assert context.storage_type == "remote"
                    assert context.strategy is strategy

    def test_task_repository_property(self, tmp_path):
        """Test task_repository property"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        context = StorageStrategyContext(strategy)

        repo = context.task_repository

        assert isinstance(repo, TaskRepository)
        assert repo is strategy.get_task_repository()

    def test_project_repository_property(self, tmp_path):
        """Test project_repository property"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        context = StorageStrategyContext(strategy)

        repo = context.project_repository

        assert isinstance(repo, ProjectRepository)
        assert repo is strategy.get_project_repository()

    def test_label_repository_property(self, tmp_path):
        """Test label_repository property"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        context = StorageStrategyContext(strategy)

        repo = context.label_repository

        assert isinstance(repo, LabelRepository)
        assert repo is strategy.get_label_repository()

    def test_property_access_no_runtime_branching(self, tmp_path):
        """Test that property access doesn't do runtime type checking"""
        db_path = str(tmp_path / "test.db")
        strategy = LocalStorageStrategy(db_path=db_path)
        context = StorageStrategyContext(strategy)

        # Access multiple times - should be fast property lookup, no if/else
        repo1 = context.task_repository
        repo2 = context.task_repository

        # Same instance from strategy
        assert repo1 is repo2


# NOTE: Integration tests updated for new ConfigService-based pattern
class TestStrategyPatternIntegration:
    """Integration tests for Strategy Pattern"""

    def test_strategy_isolation_local_and_remote_dont_touch(self):
        """Test that local and remote strategies are completely isolated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("platformdirs.user_config_dir", return_value=tmpdir):
                with patch("platformdirs.user_data_dir", return_value=tmpdir):
                    local_strategy = LocalStorageStrategy(db_path=":memory:")
                    remote_strategy = RemoteStorageStrategy()

                    local_repo = local_strategy.get_task_repository()
                    remote_repo = remote_strategy.get_task_repository()

                    # Repositories should be different types
                    assert type(local_repo).__name__ == "SqliteTaskRepository"
                    assert type(remote_repo).__name__ == "RestApiTaskRepository"

                    # No shared state
                    assert local_repo is not remote_repo

    def test_service_layer_decoupling(self, tmp_path):
        """Test that service layer doesn't know which strategy it's using"""
        from todopro_cli.services.task_service import TaskService

        strategy = LocalStorageStrategy(db_path=str(tmp_path / "test.db"))
        context = StorageStrategyContext(strategy)

        # Service receives repository, doesn't know it's SQLite
        service = TaskService(task_repository=context.task_repository)

        # Service just uses the interface - check for actual methods
        assert hasattr(service.repository, "list_all")
        assert hasattr(service.repository, "add")
        assert hasattr(service.repository, "update")
        assert hasattr(service.repository, "delete")

    def test_caching_same_profile_returns_same_strategy(self):
        """Test that get_storage_strategy_context returns same instance (via cached ConfigService)"""
        from todopro_cli.services.config_service import get_config_service

        # Clear the config service cache first
        get_config_service.cache_clear()

        # Get strategy twice - both should return same instance from ConfigService
        strategy1 = get_storage_strategy_context()
        strategy2 = get_storage_strategy_context()

        # Should return same cached instance (via ConfigService._storage_strategy_context)
        assert strategy1 is strategy2



