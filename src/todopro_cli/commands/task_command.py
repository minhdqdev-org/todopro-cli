"""Top-level `tp task <task_id>` command — quick shortcut to get task details."""

from typing import Annotated

import typer

from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer()


@app.command("task")
@command_wrapper
async def task_command(
    task_id: Annotated[str, typer.Argument(help="Task ID or suffix")],
    output: Annotated[
        str, typer.Option("--output", "-o", help="Output format")
    ] = "table",
) -> None:
    """Get task details by ID or suffix."""
    storage_strategy_context = get_storage_strategy_context()
    task_repo = strategy_context.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.get_task(resolved_id)
    format_output(task.model_dump(), output)
