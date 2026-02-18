"""Repository factory for instantiating the correct storage adapters.

⚠️ DEPRECATED: This factory pattern violates the Strategy Pattern.
   Use get_strategy_context() instead for proper dependency injection.

   Old way (deprecated):
       factory = RepositoryFactory()
       task_repo = factory.get_task_repository()

   New way (recommended):
       from todopro_cli.context_manager import get_strategy_context
       strategy = get_strategy_context()
       task_repo = strategy.task_repository

This module is kept for backward compatibility but will be removed in v3.0.
The old factory uses runtime if/else to select implementations, violating
the Strategy Pattern. The new approach decides strategy once at bootstrap.
"""

from __future__ import annotations

import functools
from typing import Literal

from todopro_cli.adapters.rest_api import (
    RestApiContextRepository,
    RestApiLabelRepository,
    RestApiProjectRepository,
    RestApiTaskRepository,
)
from todopro_cli.adapters.sqlite import (
    SqliteContextRepository,
    SqliteLabelRepository,
    SqliteProjectRepository,
    SqliteTaskRepository,
)
from todopro_cli.repositories.repository import (
    ContextRepository,
    LabelRepository,
    ProjectRepository,
    TaskRepository,
)
from todopro_cli.services.context_manager import ContextManager, get_context_manager


class RepositoryFactoryError(Exception):
    """Exception raised when repository factory encounters an error."""


class RepositoryFactory:
    """Factory for creating repository instances based on current context.

    ⚠️ DEPRECATED: Use get_strategy_context() instead.

    This factory will be removed in v3.0. It violates the Strategy Pattern
    by using runtime if/else to select implementations. The new approach
    uses bootstrap-time strategy injection.

    The factory reads the current context from configuration and instantiates
    the appropriate adapter (SQLite for local, REST API for remote).

    Uses lazy initialization - repositories are only created when first accessed.
    """

    def __init__(self, context_manager: ContextManager | None = None):
        """Initialize the repository factory.

        Args:
            context_manager: Optional ContextManager instance. If None, uses singleton.
        """
        self._context_manager = context_manager or get_context_manager()
        self._storage_type: Literal["local", "remote"] | None = None
        self._db_path: str | None = None  # For local storage

        # Lazy-loaded repository instances
        self._task_repo: TaskRepository | None = None
        self._project_repo: ProjectRepository | None = None
        self._label_repo: LabelRepository | None = None
        self._context_repo: ContextRepository | None = None

    @property
    def storage_type(self) -> Literal["local", "remote"]:
        """Determine the storage type from current context.

        Returns:
            "local" for SQLite storage, "remote" for REST API storage

        Raises:
            RepositoryFactoryError: If context is invalid or storage type cannot be determined
        """
        if self._storage_type is not None:
            return self._storage_type

        context = self._context_manager.get_current_context()

        if context is None:
            # Default to remote if no context is configured
            self._storage_type = "remote"
            return self._storage_type

        # Use the explicit type field from Context
        self._storage_type = context.type

        # Store db_path for local storage
        if context.type == "local":
            self._db_path = context.source

        return self._storage_type

    @property
    def database_path(self) -> str | None:
        """Get the database path for local storage.

        Returns:
            Database file path for local storage, None for remote
        """
        # Trigger storage_type detection
        _ = self.storage_type
        return self._db_path

    def get_task_repository(self) -> TaskRepository:
        """Get task repository instance.

        Returns:
            TaskRepository implementation (SQLite or REST API based)

        Raises:
            RepositoryFactoryError: If repository cannot be instantiated
        """
        if self._task_repo is None:
            self._task_repo = self._create_task_repository()
        return self._task_repo

    def get_project_repository(self) -> ProjectRepository:
        """Get project repository instance.

        Returns:
            ProjectRepository implementation (SQLite or REST API based)

        Raises:
            RepositoryFactoryError: If repository cannot be instantiated
        """
        if self._project_repo is None:
            self._project_repo = self._create_project_repository()
        return self._project_repo

    def get_label_repository(self) -> LabelRepository:
        """Get label repository instance.

        Returns:
            LabelRepository implementation (SQLite or REST API based)

        Raises:
            RepositoryFactoryError: If repository cannot be instantiated
        """
        if self._label_repo is None:
            self._label_repo = self._create_label_repository()
        return self._label_repo

    def get_context_repository(self) -> ContextRepository:
        """Get context repository instance.

        Returns:
            ContextRepository implementation (SQLite or REST API based)

        Raises:
            RepositoryFactoryError: If repository cannot be instantiated
        """
        if self._context_repo is None:
            self._context_repo = self._create_context_repository()
        return self._context_repo

    def _create_task_repository(self) -> TaskRepository:
        """Create task repository based on storage type.

        Returns:
            Concrete TaskRepository implementation

        Raises:
            RepositoryFactoryError: If adapter cannot be created
        """
        storage = self.storage_type

        if storage == "remote":
            config_mgr = ContextManager()
            return RestApiTaskRepository(config_mgr)
        return SqliteTaskRepository(db_path=self._db_path)

    def _create_project_repository(self) -> ProjectRepository:
        """Create project repository based on storage type.

        Returns:
            Concrete ProjectRepository implementation

        Raises:
            RepositoryFactoryError: If adapter cannot be created
        """
        storage = self.storage_type

        if storage == "remote":
            config_mgr = ContextManager()
            return RestApiProjectRepository(config_mgr)
        # local

        return SqliteProjectRepository(db_path=self._db_path)

    def _create_label_repository(self) -> LabelRepository:
        """Create label repository based on storage type.

        Returns:
            Concrete LabelRepository implementation

        Raises:
            RepositoryFactoryError: If adapter cannot be created
        """
        storage = self.storage_type

        if storage == "remote":
            config_mgr = ContextManager()
            return RestApiLabelRepository(config_mgr)
        # local
        return SqliteLabelRepository(db_path=self._db_path)

    def _create_context_repository(self) -> ContextRepository:
        """Create context repository based on storage type.

        Returns:
            Concrete ContextRepository implementation

        Raises:
            RepositoryFactoryError: If adapter cannot be created
        """
        storage = self.storage_type

        if storage == "remote":
            config_mgr = ContextManager()
            return RestApiContextRepository(config_mgr)
        # local

        return SqliteContextRepository(db_path=self._db_path)


@functools.lru_cache(maxsize=1)
def get_repository_factory() -> RepositoryFactory:
    """Get a singleton repository factory instance"""
    return RepositoryFactory()
