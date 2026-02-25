"""Command 'skip' of todopro-cli — skip a recurring task instance."""

import typer

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output, format_success

from .decorators import command_wrapper

app = typer.Typer()
console = get_console()


@app.command("skip")
@command_wrapper
async def skip_command(
    task_id: str = typer.Argument(..., help="Task ID to skip"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Skip the current instance of a recurring task.

    This advances the recurrence to the next occurrence without marking
    the task as complete.
    """
    client = get_client()
    api = TasksAPI(client)
    try:
        result = await api.skip_task(task_id)
        format_success(f"Skipped task: {task_id}")
        if result:
            format_output(result, output)
    finally:
        await client.close()
