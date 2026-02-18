"""Reopen command - Reopen completed tasks."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Reopen completed tasks")
console = Console()


@app.command("reopen")
@command_wrapper
async def reopen_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
) -> None:
    """Reopen a completed task."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.reopen_task(resolved_id)
    content = task.content or "[No title]"
    if len(content) > 60:
        content = content[:57] + "..."
    format_success(f"↩ Reopened: {content}")
