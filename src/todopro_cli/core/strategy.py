"""Re-export strategy pattern classes for backward compatibility.

DEPRECATED: This module exists only for backward compatibility.
Use `from todopro_cli.models.strategy import StrategyContext` instead.

This module will be removed in v3.0.
"""

import warnings

# Re-export from actual location
from todopro_cli.models.strategy import (
    LocalStrategy,
    RemoteStrategy,
    StorageStrategy,
    StrategyContext,
)

# Issue deprecation warning on import
warnings.warn(
    "Importing from 'todopro_cli.core.strategy' is deprecated. "
    "Use 'from todopro_cli.models.strategy import StrategyContext' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "StorageStrategy",
    "LocalStrategy",
    "RemoteStrategy",
    "StrategyContext",
]
