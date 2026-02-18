"""Re-export factory functions for backward compatibility.

DEPRECATED: This module exists only for backward compatibility.
Use `from todopro_cli.models.factory import get_repository_factory` instead.

This module will be removed in v3.0 when all commands migrate to the
Strategy Pattern (get_strategy_context).
"""

import warnings

# Re-export from actual location
from todopro_cli.models.factory import (
    RepositoryFactory,
    get_repository_factory,
)

# Issue deprecation warning on import
warnings.warn(
    "Importing from 'todopro_cli.core.factory' is deprecated. "
    "Use 'from todopro_cli.models.factory import get_repository_factory' instead. "
    "Better yet, migrate to the Strategy Pattern: "
    "'from todopro_cli.services.context_manager import get_strategy_context'",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["RepositoryFactory", "get_repository_factory"]
