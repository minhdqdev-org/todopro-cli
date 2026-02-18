"""Re-export repository interfaces for backward compatibility.

DEPRECATED: This module exists only for backward compatibility.
Use `from todopro_cli.repositories.repository import TaskRepository` instead.

This module will be removed in v3.0.
"""

import warnings

# Re-export from actual location
from todopro_cli.repositories.repository import (
    ContextRepository,
    LabelRepository,
    ProjectRepository,
    TaskRepository,
)

# Issue deprecation warning on import
warnings.warn(
    "Importing from 'todopro_cli.core.repository' is deprecated. "
    "Use 'from todopro_cli.repositories import TaskRepository' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "TaskRepository",
    "ProjectRepository",
    "LabelRepository",
    "ContextRepository",
]
