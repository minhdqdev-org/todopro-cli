"""TodoPro CLI domain models.

This package contains Pydantic models that represent the core domain entities
of the TodoPro application. These models are used throughout the application
for data validation, serialization, and type safety.
"""

from .config_models import AppConfig
from .config_models import Context as ConfigContext
from .core import (
    Label,
    LabelCreate,
    LocationContext,
    LocationContextCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Section,
    SectionCreate,
    SectionFilters,
    SectionUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
    User,
)

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
    # Section models
    "Section",
    "SectionCreate",
    "SectionUpdate",
    "SectionFilters",
    # Label models
    "Label",
    "LabelCreate",
    # Context/Location models
    "LocationContext",
    "LocationContextCreate",
    # User model
    "User",
    # Config models
    "AppConfig",
    "ConfigContext",
]
