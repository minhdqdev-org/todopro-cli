"""Task management commands."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from todopro_cli.api.client import get_client
from todopro_cli.api.tasks import TasksAPI
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success

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
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """List tasks."""
    check_auth(profile)

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
                format_output(result, output)
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
