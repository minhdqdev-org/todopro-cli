"""Adapters module - Repository implementations for different storage backends.

This package contains concrete implementations (adapters) for the repository interfaces:
- sqlite: Local SQLite database storage
- rest_api: Remote REST API backend
"""

from .rest_api import (
    RestApiContextRepository,
    RestApiLabelRepository,
    RestApiProjectRepository,
    RestApiTaskRepository,
)
from .sqlite import (
    SqliteContextRepository,
    SqliteLabelRepository,
    SqliteProjectRepository,
    SqliteTaskRepository,
)

__all__ = [
    # SQLite adapters
    "SqliteTaskRepository",
    "SqliteProjectRepository",
    "SqliteLabelRepository",
    "SqliteContextRepository",
    # REST API adapters
    "RestApiTaskRepository",
    "RestApiProjectRepository",
    "RestApiLabelRepository",
    "RestApiContextRepository",
]

