"""Adapters module - Repository implementations for different storage backends.

This package contains concrete implementations (adapters) for the repository interfaces:
- sqlite: Local SQLite database storage
- rest_api: Remote REST API backend
"""

from .rest_api import (
    RestApiLabelRepository,
    RestApiLocationContextRepository,
    RestApiProjectRepository,
    RestApiTaskRepository,
)
from .sqlite import (
    SqliteLabelRepository,
    SqliteLocationContextRepository,
    SqliteProjectRepository,
    SqliteTaskRepository,
)

__all__ = [
    # SQLite adapters
    "SqliteTaskRepository",
    "SqliteProjectRepository",
    "SqliteLabelRepository",
    "SqliteLocationContextRepository",
    # REST API adapters
    "RestApiTaskRepository",
    "RestApiProjectRepository",
    "RestApiLabelRepository",
    "RestApiLocationContextRepository",
]
