"""Repository interfaces for the TodoPro CLI.

This package contains abstract base classes (ABCs) that define the contracts
for data persistence operations. These are the "Ports" in the Hexagonal Architecture.

Implementations (Adapters) are in:
- todopro_cli.adapters.sqlite (local storage)
- todopro_cli.adapters.rest_api (remote API)
"""

from .repository import (
    AchievementRepository,
    LabelRepository,
    LocationContextRepository,
    ProjectRepository,
    TaskRepository,
)

__all__ = [
    "TaskRepository",
    "ProjectRepository",
    "LabelRepository",
    "LocationContextRepository",
    "AchievementRepository",
]
