"""TodoPro CLI domain models.

This package contains Pydantic models that represent the core domain entities
of the TodoPro application. These models are used throughout the application
for data validation, serialization, and type safety.
"""

from .core import (
    Label,
    LabelCreate,
    LocationContext,
    LocationContextCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
    User,
)
from .config_models import AppConfig, Context as ConfigContext

# Alias for backward compatibility with repository.py
Context = LocationContext
ContextCreate = LocationContextCreate

__all__ = [
    # Task models
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "TaskFilters",
    # Project models
    "Project",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectFilters",
    # Label models
    "Label",
    "LabelCreate",
    # Context/Location models
    "LocationContext",
    "LocationContextCreate",
    "Context",  # Alias
    "ContextCreate",  # Alias
    # User model
    "User",
    # Config models
    "AppConfig",
    "ConfigContext",
]
