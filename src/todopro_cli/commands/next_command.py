"""Command 'next' of todopro-cli"""

import json

import typer

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.ui.formatters import (
    format_next_task,
    format_output,
)
from todopro_cli.utils.ui.console import get_console

from .decorators import command_wrapper

app = typer.Typer()
console = get_console()


@app.command("next")
@command_wrapper
async def next_command(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """Show the next task to do right now."""
    # Handle --json flag as alias for --output json
    if json_opt:
        output = "json"

    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    # Get active tasks sorted by priority and due date
    tasks = await task_service.list_tasks(status="active", limit=1, sort="priority")

    if not tasks:
        # No tasks found
        if output == "json":
            console.print(json.dumps({"task": None, "message": "No active tasks"}))
        elif output == "yaml":
            console.print("task: null\nmessage: No active tasks")
        else:
            console.print("[green]No active tasks - you're all caught up! 🎉[/green]")
    else:
        # Task found - format based on output type
        task = tasks[0]
        if output in ["json", "yaml"]:
            format_output(task.model_dump(), output)
        else:
            # Custom simple format for next task
            format_next_task(task.model_dump())
