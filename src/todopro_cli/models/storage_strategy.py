"""
Strategy Pattern: Storage Strategy Container

This module implements the Strategy Pattern for repository selection.
Instead of using if/else at runtime, the StorageStrategyContext holds the strategy
at startup and injects it into services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from todopro_cli.repositories import (
    AchievementRepository,
    LabelRepository,
    LocationContextRepository,
    ProjectRepository,
    TaskRepository,
)


class StorageStrategy(ABC):
    """
    Abstract base class for storage strategies.

    A strategy encapsulates ALL repository implementations for a given
    storage backend (either Local SQLite or Remote API).

    The StorageStrategyContext creates one strategy at startup and injects it
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
    def get_location_context_repository(self) -> LocationContextRepository:
        """Get location context repository implementation for this strategy."""

    @abstractmethod
    def get_achievement_repository(self) -> AchievementRepository:
        """Get achievement repository implementation for this strategy."""

    @property
    @abstractmethod
    def storage_type(self) -> str:
        """Get storage type identifier (for logging/debugging)."""


class LocalStorageStrategy(StorageStrategy):
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
            SqliteLocationContextRepository,
        )
        from todopro_cli.adapters.sqlite.label_repository import SqliteLabelRepository
        from todopro_cli.adapters.sqlite.project_repository import (
            SqliteProjectRepository,
        )
        from todopro_cli.adapters.sqlite.task_repository import (
            SqliteTaskRepository,  # pylint: disable
        )

        # Instantiate all repositories once
        self._task_repo = SqliteTaskRepository(db_path=db_path)
        self._project_repo = SqliteProjectRepository(db_path=db_path)
        self._label_repo = SqliteLabelRepository(db_path=db_path)
        self._location_context_repo = SqliteLocationContextRepository(db_path=db_path)

    def get_task_repository(self) -> TaskRepository:
        return self._task_repo

    def get_project_repository(self) -> ProjectRepository:
        return self._project_repo

    def get_label_repository(self) -> LabelRepository:
        return self._label_repo

    def get_location_context_repository(self) -> LocationContextRepository:
        return self._location_context_repo

    def get_achievement_repository(self) -> AchievementRepository:
        raise NotImplementedError("Achievement repository not yet implemented for local storage")

    @property
    def storage_type(self) -> str:
        return "local"


class RemoteStorageStrategy(StorageStrategy):
    """
    Remote API storage strategy.

    All repositories use REST API backend.
    This is instantiated once at startup if the active context is 'remote'.
    """

    def __init__(self):
        """
        Initialize remote strategy.

        """

        from todopro_cli.adapters.rest_api import (
            RestApiLabelRepository,
            RestApiLocationContextRepository,
            RestApiProjectRepository,
            RestApiTaskRepository,
        )  # type: ignore

        self._task_repo = RestApiTaskRepository()
        self._project_repo = RestApiProjectRepository()
        self._label_repo = RestApiLabelRepository()
        self._location_context_repo = RestApiLocationContextRepository()

    def get_task_repository(self) -> TaskRepository:
        return self._task_repo

    def get_project_repository(self) -> ProjectRepository:
        return self._project_repo

    def get_label_repository(self) -> LabelRepository:
        return self._label_repo

    def get_location_context_repository(self) -> LocationContextRepository:
        return self._location_context_repo

    def get_achievement_repository(self) -> AchievementRepository:
        raise NotImplementedError("Achievement repository not yet implemented for remote storage")

    @property
    def storage_type(self) -> str:
        return "remote"


class StorageStrategyContext:
    """
    Strategy context that provides access to all repositories.

    This is the single source of truth for repository access throughout
    the application. It's created once at startup by the StorageStrategyContext
    and injected into all services.

    Usage:
        # At startup
        strategy = LocalStorageStrategy(db_path="/path/to/db")
        context = StorageStrategyContext(strategy)

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

    def switch_strategy(self, new_strategy: StorageStrategy):
        """Switch to a new storage strategy at runtime (advanced use case)."""
        self._strategy = new_strategy

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
    def location_context_repository(self) -> LocationContextRepository:
        """Get context repository from current strategy."""
        return self._strategy.get_location_context_repository()

    @property
    def achievement_repository(self) -> LocationContextRepository:
        """Get achievement repository (same as context repository for now)."""
        return self._strategy.get_achievement_repository()

    @property
    def storage_type(self) -> str:
        """Get storage type (for logging/debugging only)."""
        return self._strategy.storage_type

    @property
    def strategy(self) -> StorageStrategy:
        """Get underlying strategy (for advanced use cases)."""
        return self._strategy
