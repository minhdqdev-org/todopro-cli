"""Command 'today' of todopro-cli"""

import json
from datetime import datetime

import typer
from rich.panel import Panel

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.cache_service import get_background_cache
from todopro_cli.services.log_service import LogService
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.ui.formatters import (
    format_output,
)
from todopro_cli.utils.ui.console import get_console

from .decorators import command_wrapper

app = typer.Typer()
console = get_console()


@app.command("today")
@command_wrapper
async def today_command(
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """Show tasks for today (overdue + today's tasks)."""
    # Handle --json flag as alias for --output json
    if json_opt:
        output = "json"

    # Show error banner if there are unread errors
    unread_errors = LogService.get_unread_errors()
    if unread_errors:
        error_count = len(unread_errors)
        latest_error = unread_errors[0]

        # Show banner
        error_msg = latest_error.get("error", "Unknown error")
        command = latest_error.get("command", "unknown")

        # Truncate long error messages
        if len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."

        banner_text = (
            f"[yellow]⚠️  {error_count} background task(s) failed[/yellow]\n"
            f"[dim]Latest: '{command}' - {error_msg}[/dim]\n\n"
            f"[dim]View details: [cyan]todopro errors[/cyan][/dim]"
        )

        console.print(Panel(banner_text, border_style="yellow", padding=(0, 1)))
        console.print()

        # Mark errors as read
        LogService.mark_errors_as_read()

    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    # For now, use list_tasks to get active tasks (simplified version)
    # TODO: Implement dedicated today_tasks method in service layer

    today_str = datetime.now().date().isoformat()

    # Get all active tasks
    all_tasks = await task_service.list_tasks(status="active", limit=1000)

    overdue_tasks = []
    today_tasks = []

    for task in all_tasks:
        if task.due_date:
            due_date_str = (
                task.due_date.date().isoformat()
                if isinstance(task.due_date, datetime)
                else task.due_date
            )
            if due_date_str < today_str:
                overdue_tasks.append(task)
            elif due_date_str == today_str:
                today_tasks.append(task)

    # Combine tasks
    all_tasks_today = overdue_tasks + today_tasks

    # Filter out tasks being completed in background
    cache = get_background_cache()
    completing_tasks = set(cache.get_completing_tasks())

    if completing_tasks:
        original_count = len(all_tasks_today)
        all_tasks_today = [
            task
            for task in all_tasks_today
            if not any(task.id.endswith(short_id) for short_id in completing_tasks)
        ]
        filtered_count = original_count - len(all_tasks_today)

        if filtered_count > 0:
            console.print(
                f"[dim]Hiding {filtered_count} task(s) being completed in background...[/dim]"
            )
            console.print()

    if all_tasks_today:
        # Display with pretty format by default
        result = {"tasks": [t.model_dump() for t in all_tasks_today]}
        # Pass all active task IDs so suffixes are globally unique
        all_task_ids = [t.id for t in all_tasks]
        format_output(result["tasks"], output, compact=compact, all_task_ids=all_task_ids)

        # Summary (skip for JSON output)
        if output not in ["json"]:
            console.print()
            console.print(
                f"[bold]Summary:[/bold] {len(overdue_tasks)} overdue, "
                f"{len(today_tasks)} due today"
            )
    else:
        # Handle empty result based on output format
        if output == "json":
            console.print(
                json.dumps(
                    {
                        "tasks": [],
                        "overdue_count": 0,
                        "today_count": 0,
                        "message": "No tasks due today",
                    }
                )
            )
        else:
            console.print("[green]No tasks due today! 🎉[/green]")
