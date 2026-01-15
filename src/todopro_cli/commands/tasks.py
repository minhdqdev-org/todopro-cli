"""Task management commands."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from todopro_cli.api.client import get_client
from todopro_cli.api.tasks import TasksAPI
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success, format_info

app = typer.Typer(help="Task management commands")
console = Console()


def check_auth(profile: str = "default") -> None:
    """Check if user is authenticated."""
    config_manager = get_config_manager(profile)
    credentials = config_manager.load_credentials()
    if not credentials:
        format_error("Not logged in. Use 'todopro login' to authenticate.")
        raise typer.Exit(1)


@app.command("list")
def list_tasks(
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    project: Optional[str] = typer.Option(None, "--project", help="Filter by project ID"),
    priority: Optional[int] = typer.Option(None, "--priority", help="Filter by priority"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search tasks"),
    limit: int = typer.Option(30, "--limit", "-n", help="Limit results"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """List tasks."""
    check_auth(profile)

    # Get output format from config if not specified
    if output is None:
        config_manager = get_config_manager(profile)
        output = config_manager.get("output.format") or "pretty"
        if not compact:
            compact = config_manager.get("output.compact") or False

    try:

        async def do_list() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                result = await tasks_api.list_tasks(
                    status=status,
                    project_id=project,
                    priority=priority,
                    search=search,
                    limit=limit,
                    offset=offset,
                )
                format_output(result, output, compact=compact)
            finally:
                await client.close()

        asyncio.run(do_list())

    except Exception as e:
        format_error(f"Failed to list tasks: {str(e)}")
        raise typer.Exit(1)


@app.command("get")
def get_task(
    task_id: str = typer.Argument(..., help="Task ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Get task details."""
    check_auth(profile)

    try:

        async def do_get() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                task = await tasks_api.get_task(task_id)
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_get())

    except Exception as e:
        format_error(f"Failed to get task: {str(e)}")
        raise typer.Exit(1)


@app.command("create")
def create_task(
    content: str = typer.Argument(..., help="Task content"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date"),
    priority: Optional[int] = typer.Option(None, "--priority", help="Priority (1-4)"),
    labels: Optional[str] = typer.Option(None, "--labels", "-l", help="Comma-separated labels"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Create a new task."""
    check_auth(profile)

    try:
        # Parse labels
        label_list = None
        if labels:
            label_list = [l.strip() for l in labels.split(",")]

        async def do_create() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                task = await tasks_api.create_task(
                    content=content,
                    description=description,
                    project_id=project,
                    due_date=due,
                    priority=priority,
                    labels=label_list,
                )
                format_success(f"Task created: {task.get('id', 'unknown')}")
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_create())

    except Exception as e:
        format_error(f"Failed to create task: {str(e)}")
        raise typer.Exit(1)


@app.command("update")
def update_task(
    task_id: str = typer.Argument(..., help="Task ID"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Task content"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date"),
    priority: Optional[int] = typer.Option(None, "--priority", help="Priority (1-4)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Update a task."""
    check_auth(profile)

    try:
        # Build updates dictionary
        updates = {}
        if content:
            updates["content"] = content
        if description:
            updates["description"] = description
        if project:
            updates["project_id"] = project
        if due:
            updates["due_date"] = due
        if priority is not None:
            updates["priority"] = priority

        if not updates:
            format_error("No updates specified")
            raise typer.Exit(1)

        async def do_update() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                task = await tasks_api.update_task(task_id, **updates)
                format_success(f"Task updated: {task_id}")
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_update())

    except Exception as e:
        format_error(f"Failed to update task: {str(e)}")
        raise typer.Exit(1)


@app.command("delete")
def delete_task(
    task_id: str = typer.Argument(..., help="Task ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Delete a task."""
    check_auth(profile)

    try:
        if not yes:
            confirm = typer.confirm(f"Are you sure you want to delete task {task_id}?")
            if not confirm:
                format_error("Cancelled")
                raise typer.Exit(0)

        async def do_delete() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                await tasks_api.delete_task(task_id)
                format_success(f"Task deleted: {task_id}")
            finally:
                await client.close()

        asyncio.run(do_delete())

    except Exception as e:
        format_error(f"Failed to delete task: {str(e)}")
        raise typer.Exit(1)


@app.command("complete")
def complete_task(
    task_id: str = typer.Argument(..., help="Task ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Mark a task as completed."""
    check_auth(profile)

    try:

        async def do_complete() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                task = await tasks_api.complete_task(task_id)
                format_success(f"Task completed: {task_id}")
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_complete())

    except Exception as e:
        format_error(f"Failed to complete task: {str(e)}")
        raise typer.Exit(1)


@app.command("reopen")
def reopen_task(
    task_id: str = typer.Argument(..., help="Task ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Reopen a completed task."""
    check_auth(profile)

    try:

        async def do_reopen() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                task = await tasks_api.reopen_task(task_id)
                format_success(f"Task reopened: {task_id}")
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_reopen())

    except Exception as e:
        format_error(f"Failed to reopen task: {str(e)}")
        raise typer.Exit(1)


@app.command("today")
def today(
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show tasks for today (overdue + today's tasks)."""
    check_auth(profile)

    try:

        async def do_today() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                result = await tasks_api.today_tasks()
                
                # Combine overdue and today tasks for pretty output
                all_tasks = result.get("overdue", []) + result.get("today", [])
                
                if all_tasks:
                    # Display with pretty format by default
                    format_output(all_tasks, output, compact=compact)
                    
                    # Summary
                    console.print()
                    console.print(
                        f"[bold]Summary:[/bold] {result.get('overdue_count', 0)} overdue, "
                        f"{result.get('today_count', 0)} due today"
                    )
                else:
                    console.print("[green]No tasks due today! 🎉[/green]")
                    
            finally:
                await client.close()

        asyncio.run(do_today())

    except Exception as e:
        format_error(f"Failed to get today's tasks: {str(e)}")
        raise typer.Exit(1)


@app.command("next")
def next_task(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show the next task to do right now."""
    check_auth(profile)

    try:

        async def do_next() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                result = await tasks_api.next_task()
                
                if "message" in result:
                    console.print(f"[green]{result['message']}[/green]")
                else:
                    console.print("\n[bold cyan]Next Task:[/bold cyan]")
                    format_output(result, output)
                    
            finally:
                await client.close()

        asyncio.run(do_next())

    except Exception as e:
        format_error(f"Failed to get next task: {str(e)}")
        raise typer.Exit(1)


@app.command("reschedule")
def reschedule(
    target: str = typer.Argument("overdue", help="What to reschedule (overdue)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Reschedule tasks to today."""
    check_auth(profile)

    if target != "overdue":
        format_error(f"Unknown target: {target}. Only 'overdue' is supported.")
        raise typer.Exit(1)

    try:

        async def do_reschedule() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                # Get overdue count first
                result = await tasks_api.today_tasks()
                overdue_count = result.get("overdue_count", 0)
                
                if overdue_count == 0:
                    console.print("[green]No overdue tasks to reschedule! 🎉[/green]")
                    return
                
                # Confirm
                if not yes:
                    confirm = typer.confirm(
                        f"Reschedule {overdue_count} overdue task(s) to today?"
                    )
                    if not confirm:
                        format_info("Cancelled")
                        raise typer.Exit(0)
                
                # Reschedule
                response = await tasks_api.reschedule_overdue()
                
                count = response.get("rescheduled_count", 0)
                format_success(f"Rescheduled {count} overdue task(s) to today")
                
                # Show rescheduled tasks
                tasks = response.get("tasks", [])
                if tasks:
                    console.print()
                    console.print("[bold cyan]Rescheduled Tasks:[/bold cyan]")
                    format_output(tasks, "pretty", compact=True)
                    
            finally:
                await client.close()

        asyncio.run(do_reschedule())

    except Exception as e:
        format_error(f"Failed to reschedule tasks: {str(e)}")
        raise typer.Exit(1)
