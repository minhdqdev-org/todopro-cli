"""Task management commands."""

import typer

from todopro_cli.services.cache_service import get_background_cache
from todopro_cli.services.config_service import get_storage_strategy_context
from todopro_cli.services.task_service import TaskService, get_task_service
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import (
    format_error,
    format_info,
    format_output,
    format_success,
)
from todopro_cli.utils.uuid_utils import resolve_project_uuid

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Task management commands")
console = get_console()

# ---------- sub-typer mounts (comment, link, apply) ----------
from .comment_command import app as _comment_app  # noqa: E402
from .link_command import app as _link_app  # noqa: E402
from .apply_command import app as _apply_app  # noqa: E402

app.add_typer(_comment_app, name="comment", help="Manage task comments")
app.add_typer(_link_app, name="link", help="Manage task dependencies")
app.add_typer(_apply_app, name="apply", help="Apply saved filters")


@app.command("list")
@command_wrapper
async def list_tasks(
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    project: str | None = typer.Option(None, "--project", help="Filter by project ID"),
    priority: int | None = typer.Option(None, "--priority", help="Filter by priority"),
    search: str | None = typer.Option(None, "--search", help="Search tasks"),
    limit: int = typer.Option(30, "--limit", help="Limit results"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """List tasks."""
    if json_opt:
        output = "json"
    # TODO: consider deprecated --status in favor of dedicated commands to view project tasks, etc.

    storage_strategy_context = get_storage_strategy_context()
    task_repo = storage_strategy_context.task_repository
    task_service = TaskService(task_repo)

    # Resolve project name/prefix to UUID if provided
    project_uuid: str | None = None
    if project is not None:
        try:
            project_repo = storage_strategy_context.project_repository
            project_uuid = await resolve_project_uuid(project, project_repo)
        except ValueError as e:
            format_error(str(e))
            raise typer.Exit(1)

    tasks = await task_service.list_tasks(
        status=status,
        project_id=project_uuid,
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
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get task details."""
    task_service = get_task_service()

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
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new task."""
    storage_strategy_context = get_storage_strategy_context()
    task_repo = storage_strategy_context.task_repository
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
        priority=priority or 4,
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
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a task."""
    storage_strategy_context = get_storage_strategy_context()
    task_repo = storage_strategy_context.task_repository
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


# Replaced by the command 'delete task'
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

    storage_strategy_context = get_storage_strategy_context()
    task_repo = storage_strategy_context.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    await task_service.delete_task(resolved_id)
    format_success(f"Task deleted: {resolved_id}")


@app.command("reopen")
@command_wrapper
async def reopen_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Reopen a completed task."""
    storage_strategy_context = get_storage_strategy_context()
    task_repo = storage_strategy_context.task_repository
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
    storage_strategy_context = get_storage_strategy_context()
    task_repo = storage_strategy_context.task_repository
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

# ---------- focus-session delegation ----------

@app.command("start")
def task_start(
    task_id: str = typer.Argument(..., help="Task ID to focus on"),
    duration: int = typer.Option(25, "--duration", help="Session duration in minutes"),
    template: str | None = typer.Option(None, "--template", help="Template name"),
) -> None:
    """Start a Pomodoro focus session on a task."""
    from todopro_cli.commands.focus import start_focus as _impl

    _impl(task_id=task_id, duration=duration, template=template)


@app.command("stop")
def task_stop() -> None:
    """Stop the current focus session."""
    from todopro_cli.commands.focus import stop_focus as _impl

    _impl()


@app.command("resume")
def task_resume() -> None:
    """Resume a paused focus session."""
    from todopro_cli.commands.focus import resume_focus as _impl

    _impl()


@app.command("status")
def task_focus_status() -> None:
    """Show current focus session status."""
    from todopro_cli.commands.focus import focus_status as _impl

    _impl()


# ---------- skip ----------

@app.command("skip")
@command_wrapper
async def skip_task(
    task_id: str = typer.Argument(..., help="Task ID to skip"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Skip the current instance of a recurring task."""
    from todopro_cli.services.api.client import get_client
    from todopro_cli.services.api.tasks import TasksAPI

    client = get_client()
    api = TasksAPI(client)
    try:
        result = await api.skip_task(task_id)
        format_success(f"Skipped recurring task: {task_id}")
        format_output(result, output)
    finally:
        await client.close()


# ---------- next ----------

@app.command("next")
@command_wrapper
async def next_task(
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
) -> None:
    """Show the next most important task."""
    from todopro_cli.utils.ui.formatters import format_next_task

    task_service = get_task_service()
    tasks = await task_service.list_tasks(status="active", limit=50)
    if not tasks:
        console.print("[dim]No active tasks.[/dim]")
        return
    task = tasks[0]
    if output == "pretty":
        format_next_task(task.model_dump())
    else:
        format_output(task.model_dump(), output)
