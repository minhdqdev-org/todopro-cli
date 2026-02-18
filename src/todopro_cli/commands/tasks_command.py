"""Task management commands."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.cache_service import get_background_cache
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.ui.formatters import (
    format_error,
    format_info,
    format_output,
    format_success,
)
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Task management commands")
console = Console()


@app.command("list")
@command_wrapper
async def list_tasks(
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    project: str | None = typer.Option(None, "--project", help="Filter by project ID"),
    priority: int | None = typer.Option(None, "--priority", help="Filter by priority"),
    search: str | None = typer.Option(None, "--search", help="Search tasks"),
    limit: int = typer.Option(30, "--limit", help="Limit results"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    output: str = typer.Option("pretty", "--output", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """List tasks."""
    # TODO: consider deprecated --status in favor of dedicated commands to view project tasks, etc.

    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    tasks = await task_service.list_tasks(
        status=status,
        project_id=project,
        priority=priority,
        search=search,
        limit=limit,
        offset=offset,
    )

    # Filter out tasks being completed in background
    cache = get_background_cache()
    completing_tasks = set(cache.get_completing_tasks())

    if completing_tasks:
        tasks = [
            task
            for task in tasks
            if not any(task.id.endswith(short_id) for short_id in completing_tasks)
        ]

    # Convert to dict format for formatters
    result = {"tasks": [t.model_dump() for t in tasks]}
    format_output(result, output, compact=compact)


@app.command("get")
@command_wrapper
async def get_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Get task details."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.get_task(resolved_id)
    format_output(task.model_dump(), output)


@app.command("create")
@command_wrapper
async def create_task(
    content: str = typer.Argument(..., help="Task content"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    project: str | None = typer.Option(None, "--project", help="Project ID"),
    due: str | None = typer.Option(None, "--due", help="Due date"),
    priority: int | None = typer.Option(None, "--priority", help="Priority (1-4)"),
    labels: str | None = typer.Option(None, "--labels", help="Comma-separated labels"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Create a new task."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    # Parse labels
    label_list = None
    if labels:
        label_list = [l.strip() for l in labels.split(",")]

    task = await task_service.add_task(
        content=content,
        description=description,
        project_id=project,
        due_date=due,
        priority=priority or 1,
        labels=label_list,
    )
    format_success(f"Task created: {task.id}")
    format_output(task.model_dump(), output)


@app.command("update")
@command_wrapper
async def update_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    content: str | None = typer.Option(None, "--content", help="Task content"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    project: str | None = typer.Option(None, "--project", help="Project ID"),
    due: str | None = typer.Option(None, "--due", help="Due date"),
    priority: int | None = typer.Option(None, "--priority", help="Priority (1-4)"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Update a task."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    if not any([content, description, project, due, priority is not None]):
        format_error("No updates specified")
        raise typer.Exit(1)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.update_task(
        resolved_id,
        content=content,
        description=description,
        project_id=project,
        due_date=due,
        priority=priority,
    )
    format_success(f"Task updated: {resolved_id}")
    format_output(task.model_dump(), output)


@app.command("delete")
@command_wrapper
async def delete_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a task."""
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete task {task_id}?")
        if not confirm:
            format_error("Cancelled")
            raise typer.Exit(0)

    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    await task_service.delete_task(resolved_id)
    format_success(f"Task deleted: {resolved_id}")


@app.command("reopen")
@command_wrapper
async def reopen_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Reopen a completed task."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.update_task(resolved_id, is_completed=False)
    format_success(f"Task reopened: {resolved_id}")
    format_output(task.model_dump(), output)


@app.command("reschedule")
@command_wrapper
async def reschedule(
    target: str | None = typer.Argument(
        None, help="Task ID/suffix (omit to reschedule all overdue tasks)"
    ),
    date: str | None = typer.Option(
        None, "--date", "-d", help="New due date (today/tomorrow/YYYY-MM-DD)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reschedule a task or all overdue tasks."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    # Check if target is None or "overdue" for bulk reschedule
    if target is None or target == "overdue":
        from datetime import datetime

        # Get overdue tasks
        today_str = datetime.now().date().isoformat()
        all_tasks = await task_service.list_tasks(status="active", limit=1000)
        overdue_tasks = [
            task
            for task in all_tasks
            if task.due_date and task.due_date.date().isoformat() < today_str
        ]

        if not overdue_tasks:
            console.print("[green]No overdue tasks to reschedule! 🎉[/green]")
            return

        # Confirm
        if not yes:
            overdue_count = len(overdue_tasks)
            task_word = "task" if overdue_count == 1 else "tasks"
            confirm = typer.confirm(
                f"Do you want to reschedule {overdue_count} overdue {task_word} to today?",
                default=True,
            )
            if not confirm:
                format_info("Cancelled")
                return

        # Reschedule all to today
        new_due_date = datetime.now().date().isoformat()
        for task in overdue_tasks:
            await task_service.update_task(task.id, due_date=new_due_date)

        count = len(overdue_tasks)
        task_word = "task" if count == 1 else "tasks"
        format_success(f"Rescheduled {count} overdue {task_word} to today")
        console.print("[dim]💡 Tip: You can undo this later if needed[/dim]")

    else:
        # Reschedule a specific task
        task_id = target

        # Default to today if no date specified
        if not date:
            from datetime import datetime

            date = datetime.now().date().isoformat()

        # Resolve task ID
        resolved_id = await resolve_task_id(task_service, task_id)

        # Reschedule the task
        task = await task_service.update_task(resolved_id, due_date=date)

        content = task.content or "[No title]"
        if len(content) > 60:
            content = content[:57] + "..."

        format_success(f"✓ {content}")
        console.print(f"[dim]Rescheduled to {date}[/dim]")


# TODO: Refactor classify to use service layer
# @app.command("classify")
# def classify_task_cmd(
#     task_id: str = typer.Argument(..., help="Task ID or suffix to classify"),
#     urgent: bool = typer.Option(None, "--urgent/--not-urgent", help="Mark as urgent"),
#     important: bool = typer.Option(
#         None, "--important/--not-important", help="Mark as important"
#     ),
# ) -> None:
#     """Classify a task in the Eisenhower Matrix."""
#     pass


# TODO: Refactor focus to use service layer
# @app.command("focus")
# def focus_on_q2() -> None:
#     """Show Q2 tasks (Important but Not Urgent) - Strategic work."""
#     pass
