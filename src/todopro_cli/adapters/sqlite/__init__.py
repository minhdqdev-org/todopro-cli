"""SQLite adapter module - Local database storage implementation."""

from todopro_cli.adapters.sqlite.context_repository import SqliteContextRepository
from todopro_cli.adapters.sqlite.e2ee import E2EEHandler, get_e2ee_handler
from todopro_cli.adapters.sqlite.label_repository import SqliteLabelRepository
from todopro_cli.adapters.sqlite.project_repository import SqliteProjectRepository
from todopro_cli.adapters.sqlite.task_repository import SqliteTaskRepository
from todopro_cli.adapters.sqlite.user_manager import (
    get_or_create_local_user,
    get_system_timezone,
)

__all__ = [
    "SqliteTaskRepository",
    "SqliteProjectRepository",
    "SqliteLabelRepository",
    "SqliteContextRepository",
    "E2EEHandler",
    "get_e2ee_handler",
    "get_or_create_local_user",
    "get_system_timezone",
]
