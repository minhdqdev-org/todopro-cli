"""Context and strategy management for TodoPro CLI.

This module provides the bootstrap function for initializing the Strategy Pattern.

Key Functions:
- get_strategy_context(): Main entry point for repository access (RECOMMENDED)
- get_context_manager(): Deprecated backward-compatibility wrapper

Architecture (Post Spec 10-14 Refactoring):
- Strategy Pattern replaced Factory Pattern (Spec 11)
- ConfigService is single source of truth (Spec 12)
- ContextManager is deprecated, kept for backward compatibility
- All 29 commands migrated to use get_strategy_context()

Usage Pattern:
    from todopro_cli.services.context_manager import get_strategy_context
    
    # Get repositories for current context
    strategy = get_strategy_context()
    tasks = await strategy.task_repository.list(filters)
    
    # Strategy automatically handles:
    # - Reading current context from ConfigService
    # - Initializing LocalStrategy or RemoteStrategy
    # - Setting up appropriate adapters (SQLite or REST API)

Migration Note:
    OLD (deprecated):  factory = get_repository_factory()
    NEW (current):     strategy = get_strategy_context()
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_dir

from todopro_cli.models.config_models import AppConfig, Context
from todopro_cli.models.strategy import LocalStrategy, RemoteStrategy, StrategyContext
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.ui.console import get_console

console = get_console()


@lru_cache(maxsize=1)
def get_strategy_context() -> StrategyContext:
    """Get a cached StrategyContext using ConfigService.
    
    This is the recommended way to get repository access in the application.
    It bootstraps the appropriate storage strategy based on the active context.
    
    Returns:
        StrategyContext: Configured strategy with all repositories
    
    Example:
        from todopro_cli.services.context_manager import get_strategy_context
        
        strategy = get_strategy_context()
        task_repo = strategy.task_repository
        tasks = task_repo.get_all()
    """
    config_svc = get_config_service()
    
    try:
        context = config_svc.config.get_current_context()
    except (ValueError, KeyError):
        # No context configured, use default local
        console.print(
            "[yellow]No active context found, using default local storage[/yellow]"
        )
        data_dir = Path(user_data_dir("todopro_cli"))
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(data_dir / "todopro.db")
        strategy = LocalStrategy(db_path=db_path)
        return StrategyContext(strategy)
    
    if context.type == "local":
        # Local SQLite strategy
        # Use 'source' field as the db path
        db_path = context.source
        strategy = LocalStrategy(db_path=db_path)
    
    elif context.type == "remote":
        # Remote API strategy
        strategy = RemoteStrategy(config_service=config_svc)
    
    else:
        raise ValueError(
            f"Invalid context type: {context.type}. Must be 'local' or 'remote'"
        )
    
    return StrategyContext(strategy)


@lru_cache(maxsize=1)
def get_context_manager():
    """Get ConfigService instance (backward compatibility).
    
    Deprecated: Use get_config_service() directly instead.
    This function exists for backward compatibility and returns ConfigService.
    """
    import warnings
    warnings.warn(
        "get_context_manager() is deprecated. Use get_config_service() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_config_service()


# Legacy ContextManager class stub for backward compatibility
class ContextManager:
    """Deprecated: Use ConfigService instead.
    
    This class exists only for backward compatibility.
    All methods delegate to ConfigService.
    """
    
    def __init__(self):
        import warnings
        warnings.warn(
            "ContextManager is deprecated. Use ConfigService instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._config_service = get_config_service()
        
        # Expose attributes for compatibility
        self.config_dir = self._config_service.config_dir
        self.config_path = self._config_service.config_path
        self.credentials_dir = self._config_service.credentials_dir
        self.data_dir = self._config_service.data_dir
    
    @property
    def config(self) -> AppConfig:
        """Get configuration."""
        return self._config_service.config
    
    def load_config(self) -> AppConfig:
        """Load configuration."""
        return self._config_service.load_config()
    
    def save_config(self):
        """Save configuration."""
        return self._config_service.save_config()
    
    def get_context(self, name: str) -> Context | None:
        """Get context by name."""
        try:
            return self._config_service.config.get_context(name)
        except ValueError:
            return None
    
    def get_current_context(self) -> Context | None:
        """Get current context."""
        try:
            return self._config_service.config.get_current_context()
        except (ValueError, KeyError):
            return None
    
    def get_current_context_name(self) -> str | None:
        """Get current context name."""
        return self._config_service.config.current_context_name
    
    def set_current_context(self, name: str):
        """Set current context."""
        self._config_service.use_context(name)
    
    def list_contexts(self) -> list[Context]:
        """List all contexts."""
        return self._config_service.list_contexts()
    
    def use_context(self, name: str) -> Context:
        """Switch to a context."""
        return self._config_service.use_context(name)
    
    def add_context(self, context: Context):
        """Add a new context."""
        self._config_service.add_context(context)
    
    def remove_context(self, name: str):
        """Remove a context."""
        self._config_service.remove_context(name)
    
    def bootstrap(self) -> StrategyContext:
        """Bootstrap strategy context."""
        return get_strategy_context()
