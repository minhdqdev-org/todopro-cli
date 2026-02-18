"""
Strategy Pattern: Storage Strategy Container

This module implements the Strategy Pattern for repository selection.
Instead of using if/else at runtime, the Context Manager creates a
StrategyContext at startup and injects it into services.

This follows the architecture described in IMPROVE_ARCHITECTURE.md:
- Context Manager acts as Bootstrap/Config Loader
- Strategy is decided once at startup, not at every repository access
- Services are completely decoupled from storage implementation
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from todopro_cli.repositories.repository import (
    ContextRepository as ContextRepo,
    LabelRepository,
    ProjectRepository,
    TaskRepository,
)


class StorageStrategy(ABC):
    """
    Abstract base class for storage strategies.

    A strategy encapsulates ALL repository implementations for a given
    storage backend (either Local SQLite or Remote API).

    The Context Manager creates one strategy at startup and injects it
    throughout the application. Services never know which strategy they're using.
    """

    @abstractmethod
    def get_task_repository(self) -> TaskRepository:
        """Get task repository implementation for this strategy."""

    @abstractmethod
    def get_project_repository(self) -> ProjectRepository:
        """Get project repository implementation for this strategy."""

    @abstractmethod
    def get_label_repository(self) -> LabelRepository:
        """Get label repository implementation for this strategy."""

    @abstractmethod
    def get_context_repository(self) -> ContextRepo:
        """Get context repository implementation for this strategy."""

    @property
    @abstractmethod
    def storage_type(self) -> str:
        """Get storage type identifier (for logging/debugging)."""


class LocalStrategy(StorageStrategy):
    """
    Local SQLite storage strategy.

    All repositories use local SQLite database.
    This is instantiated once at startup if the active context is 'local'.
    """

    def __init__(self, db_path: str):
        """
        Initialize local strategy.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Import here to avoid circular dependencies
        from todopro_cli.adapters.sqlite.context_repository import (
            SqliteContextRepository,
        )
        from todopro_cli.adapters.sqlite.label_repository import SqliteLabelRepository
        from todopro_cli.adapters.sqlite.project_repository import (
            SqliteProjectRepository,
        )
        from todopro_cli.adapters.sqlite.task_repository import SqliteTaskRepository

        # Instantiate all repositories once
        self._task_repo = SqliteTaskRepository(db_path=db_path)
        self._project_repo = SqliteProjectRepository(db_path=db_path)
        self._label_repo = SqliteLabelRepository(db_path=db_path)
        self._context_repo = SqliteContextRepository(db_path=db_path)

    def get_task_repository(self) -> TaskRepository:
        return self._task_repo

    def get_project_repository(self) -> ProjectRepository:
        return self._project_repo

    def get_label_repository(self) -> LabelRepository:
        return self._label_repo

    def get_context_repository(self) -> ContextRepo:
        return self._context_repo

    @property
    def storage_type(self) -> str:
        return "local"


class RemoteStrategy(StorageStrategy):
    """
    Remote API storage strategy.

    All repositories use REST API backend.
    This is instantiated once at startup if the active context is 'remote'.
    """

    def __init__(self, config_service):
        """
        Initialize remote strategy.

        Args:
            config_service: ConfigService instance with API configuration
        """
        self.config_service = config_service

        # Import here to avoid circular dependencies
        from todopro_cli.adapters.rest_api import (
            RestApiContextRepository,
            RestApiLabelRepository,
            RestApiProjectRepository,
            RestApiTaskRepository,
        )

        # Instantiate all repositories once
        self._task_repo = RestApiTaskRepository(config_service)
        self._project_repo = RestApiProjectRepository(config_service)
        self._label_repo = RestApiLabelRepository(config_service)
        self._context_repo = RestApiContextRepository(config_service)

    def get_task_repository(self) -> TaskRepository:
        return self._task_repo

    def get_project_repository(self) -> ProjectRepository:
        return self._project_repo

    def get_label_repository(self) -> LabelRepository:
        return self._label_repo

    def get_context_repository(self) -> ContextRepo:
        return self._context_repo

    @property
    def storage_type(self) -> str:
        return "remote"


class StrategyContext:
    """
    Strategy context that provides access to all repositories.

    This is the single source of truth for repository access throughout
    the application. It's created once at startup by the Context Manager
    and injected into all services.

    Usage:
        # At startup (in Context Manager)
        strategy = LocalStrategy(db_path="/path/to/db")
        context = StrategyContext(strategy)

        # In services
        task_repo = strategy_context.task_repository
        task_repo.create(task)  # Works regardless of strategy
    """

    def __init__(self, strategy: StorageStrategy):
        """
        Initialize strategy context.

        Args:
            strategy: Storage strategy (Local or Remote)
        """
        self._strategy = strategy

    @property
    def task_repository(self) -> TaskRepository:
        """Get task repository from current strategy."""
        return self._strategy.get_task_repository()

    @property
    def project_repository(self) -> ProjectRepository:
        """Get project repository from current strategy."""
        return self._strategy.get_project_repository()

    @property
    def label_repository(self) -> LabelRepository:
        """Get label repository from current strategy."""
        return self._strategy.get_label_repository()

    @property
    def context_repository(self) -> ContextRepo:
        """Get context repository from current strategy."""
        return self._strategy.get_context_repository()

    @property
    def storage_type(self) -> str:
        """Get storage type (for logging/debugging only)."""
        return self._strategy.storage_type

    @property
    def strategy(self) -> StorageStrategy:
        """Get underlying strategy (for advanced use cases)."""
        return self._strategy
