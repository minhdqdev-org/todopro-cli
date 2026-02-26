"""Unit tests for storage strategy pattern (models/storage_strategy.py)."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.adapters.sqlite import schema as db_schema
from todopro_cli.models.storage_strategy import (
    LocalStorageStrategy,
    RemoteStorageStrategy,
    StorageStrategy,
    StorageStrategyContext,
)
from todopro_cli.repositories.repository import (
    LabelRepository,
    LocationContextRepository,
    ProjectRepository,
    TaskRepository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_temp_db() -> str:
    """Create a temporary SQLite database with full schema and return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    db_schema.initialize_schema(conn)
    # Insert a default user so user_manager works
    conn.execute(
        "INSERT INTO users (id, email, name, timezone, created_at, updated_at) "
        "VALUES ('u1', 'test@local', 'Test', 'UTC', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    conn.close()
    return tmp.name


# ---------------------------------------------------------------------------
# StorageStrategy (abstract)
# ---------------------------------------------------------------------------


class TestStorageStrategyAbstract:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            StorageStrategy()


# ---------------------------------------------------------------------------
# LocalStorageStrategy
# ---------------------------------------------------------------------------


class TestLocalStorageStrategy:
    @pytest.fixture
    def db_path(self):
        path = _make_temp_db()
        yield path
        Path(path).unlink(missing_ok=True)

    @pytest.fixture
    def strategy(self, db_path):
        # Patch DatabaseConnection so each test gets fresh in-memory DB
        with patch(
            "todopro_cli.adapters.sqlite.connection.DatabaseConnection.get_connection"
        ) as mock_get_conn:
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            db_schema.initialize_schema(conn)
            conn.execute(
                "INSERT INTO users (id, email, name, timezone, created_at, updated_at) "
                "VALUES ('u1', 'test@local', 'Test', 'UTC', '2024-01-01', '2024-01-01')"
            )
            conn.commit()
            mock_get_conn.return_value = conn
            yield LocalStorageStrategy(db_path=db_path)

    def test_storage_type_is_local(self, strategy):
        assert strategy.storage_type == "local"

    def test_get_task_repository_returns_task_repo(self, strategy):
        repo = strategy.get_task_repository()
        assert isinstance(repo, TaskRepository)

    def test_get_project_repository_returns_project_repo(self, strategy):
        repo = strategy.get_project_repository()
        assert isinstance(repo, ProjectRepository)

    def test_get_label_repository_returns_label_repo(self, strategy):
        repo = strategy.get_label_repository()
        assert isinstance(repo, LabelRepository)

    def test_get_location_context_repository_returns_context_repo(self, strategy):
        repo = strategy.get_location_context_repository()
        assert isinstance(repo, LocationContextRepository)

    def test_same_repo_instance_returned_twice(self, strategy):
        repo1 = strategy.get_task_repository()
        repo2 = strategy.get_task_repository()
        assert repo1 is repo2

    def test_get_achievement_repository_raises(self, strategy):
        with pytest.raises(NotImplementedError):
            strategy.get_achievement_repository()

    def test_db_path_stored(self, strategy, db_path):
        assert strategy.db_path == db_path


# ---------------------------------------------------------------------------
# RemoteStorageStrategy
# ---------------------------------------------------------------------------


class TestRemoteStorageStrategy:
    @pytest.fixture
    def mock_rest_repos(self):
        """Patch all REST API repository classes with mocks."""
        mock_task = MagicMock(spec=TaskRepository)
        mock_project = MagicMock(spec=ProjectRepository)
        mock_label = MagicMock(spec=LabelRepository)
        mock_context = MagicMock(spec=LocationContextRepository)

        with patch(
            "todopro_cli.adapters.sqlite.task_repository.SqliteTaskRepository"
        ):
            with patch.multiple(
                "todopro_cli.adapters.rest_api",
                RestApiTaskRepository=MagicMock(return_value=mock_task),
                RestApiProjectRepository=MagicMock(return_value=mock_project),
                RestApiLabelRepository=MagicMock(return_value=mock_label),
                RestApiLocationContextRepository=MagicMock(
                    return_value=mock_context
                ),
            ):
                yield {
                    "task": mock_task,
                    "project": mock_project,
                    "label": mock_label,
                    "context": mock_context,
                }

    def test_storage_type_is_remote(self, mock_rest_repos):
        strategy = RemoteStorageStrategy()
        assert strategy.storage_type == "remote"

    def test_get_task_repository(self, mock_rest_repos):
        strategy = RemoteStorageStrategy()
        repo = strategy.get_task_repository()
        assert repo is mock_rest_repos["task"]

    def test_get_project_repository(self, mock_rest_repos):
        strategy = RemoteStorageStrategy()
        repo = strategy.get_project_repository()
        assert repo is mock_rest_repos["project"]

    def test_get_label_repository(self, mock_rest_repos):
        strategy = RemoteStorageStrategy()
        repo = strategy.get_label_repository()
        assert repo is mock_rest_repos["label"]

    def test_get_location_context_repository(self, mock_rest_repos):
        strategy = RemoteStorageStrategy()
        repo = strategy.get_location_context_repository()
        assert repo is mock_rest_repos["context"]

    def test_get_achievement_repository_raises(self, mock_rest_repos):
        strategy = RemoteStorageStrategy()
        with pytest.raises(NotImplementedError):
            strategy.get_achievement_repository()


# ---------------------------------------------------------------------------
# StorageStrategyContext
# ---------------------------------------------------------------------------


class TestStorageStrategyContext:
    @pytest.fixture
    def mock_strategy(self):
        strategy = MagicMock(spec=StorageStrategy)
        strategy.storage_type = "mock"
        mock_task_repo = MagicMock(spec=TaskRepository)
        mock_project_repo = MagicMock(spec=ProjectRepository)
        mock_label_repo = MagicMock(spec=LabelRepository)
        mock_context_repo = MagicMock(spec=LocationContextRepository)
        strategy.get_task_repository.return_value = mock_task_repo
        strategy.get_project_repository.return_value = mock_project_repo
        strategy.get_label_repository.return_value = mock_label_repo
        strategy.get_location_context_repository.return_value = mock_context_repo
        strategy.get_achievement_repository.side_effect = NotImplementedError
        return strategy

    @pytest.fixture
    def context(self, mock_strategy):
        return StorageStrategyContext(mock_strategy)

    def test_task_repository_delegates_to_strategy(self, context, mock_strategy):
        repo = context.task_repository
        mock_strategy.get_task_repository.assert_called_once()
        assert repo is mock_strategy.get_task_repository.return_value

    def test_project_repository_delegates_to_strategy(self, context, mock_strategy):
        repo = context.project_repository
        mock_strategy.get_project_repository.assert_called_once()
        assert repo is mock_strategy.get_project_repository.return_value

    def test_label_repository_delegates_to_strategy(self, context, mock_strategy):
        repo = context.label_repository
        mock_strategy.get_label_repository.assert_called_once()
        assert repo is mock_strategy.get_label_repository.return_value

    def test_location_context_repository_delegates(self, context, mock_strategy):
        repo = context.location_context_repository
        mock_strategy.get_location_context_repository.assert_called_once()
        assert repo is mock_strategy.get_location_context_repository.return_value

    def test_storage_type_delegates(self, context, mock_strategy):
        assert context.storage_type == "mock"

    def test_strategy_property_returns_current_strategy(self, context, mock_strategy):
        assert context.strategy is mock_strategy

    def test_switch_strategy_updates_strategy(self, context, mock_strategy):
        new_strategy = MagicMock(spec=StorageStrategy)
        new_strategy.storage_type = "new"
        context.switch_strategy(new_strategy)
        assert context.strategy is new_strategy
        assert context.storage_type == "new"

    def test_achievement_repository_delegates(self, context, mock_strategy):
        with pytest.raises(NotImplementedError):
            _ = context.achievement_repository
