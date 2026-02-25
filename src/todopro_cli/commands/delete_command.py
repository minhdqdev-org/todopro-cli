"""Delete command - Delete resources."""

import typer

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.filters import FiltersAPI
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.services.label_service import LabelService
from todopro_cli.services.project_service import get_project_service
from todopro_cli.services.task_service import get_task_service
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_info, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Delete resources")
console = get_console()


@app.command("task")
@command_wrapper
async def delete_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a task."""
    task_service = get_task_service()

    resolved_id = await resolve_task_id(task_service, task_id)

    # get task from resolved ID to display content in confirmation
    task = await task_service.get_task(resolved_id)
    if task is None:
        console.print(f"[red]Error: Task with ID '{resolved_id}' not found.[/red]")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete task '{task.content}'?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    await task_service.delete_task(resolved_id)
    console.print("Done.", style=None)


@app.command("project")
@command_wrapper
async def delete_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a project."""
    project_service = get_project_service()

    if not force:
        confirm = typer.confirm(f"Delete project {project_id}?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    await project_service.delete_project(project_id)
    format_success(f"Project deleted: {project_id}")


@app.command("label")
@command_wrapper
async def delete_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a label."""
    storage_strategy_context = get_storage_strategy_context()
    label_repo = storage_strategy_context.label_repository
    label_service = LabelService(label_repo)

    if not force:
        confirm = typer.confirm(f"Delete label {label_id}?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    await label_service.delete_label(label_id)
    format_success(f"Label deleted: {label_id}")


@app.command("context")
@command_wrapper
async def delete_context(
    name: str = typer.Argument(..., help="Context name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a storage context."""
    from todopro_cli.services.config_service import get_config_service

    config_service = get_config_service()

    if not force:
        confirm = typer.confirm(f"Delete context {name}?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    config_service.remove_context(name)
    format_success(f"Context deleted: {name}")


@app.command("location-context")
@command_wrapper
async def delete_location_context(
    name: str = typer.Argument(..., help="Location context name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a location context."""
    from todopro_cli.services.location_context_service import LocationContextService

    storage_strategy_context = get_storage_strategy_context()
    repo = factory.get_location_context_repository()
    service = LocationContextService(repo)

    if not force:
        confirm = typer.confirm(f"Delete location context {name}?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    await service.delete_context(name)
    format_success(f"Location context deleted: {name}")


@app.command("reminder")
@command_wrapper
async def delete_reminder(
    task_id: str = typer.Argument(..., help="Task ID"),
    reminder_id: str = typer.Argument(..., help="Reminder ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a task reminder."""
    if not force:
        confirm = typer.confirm(f"Delete reminder {reminder_id} for task {task_id}?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    client = get_client()
    api = TasksAPI(client)
    try:
        await api.delete_reminder(task_id, reminder_id)
        format_success(f"Reminder {reminder_id} deleted from task {task_id}")
    finally:
        await client.close()


@app.command("filter")
@command_wrapper
async def delete_filter(
    filter_id: str = typer.Argument(..., help="Filter ID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a saved filter."""
    client = get_client()
    api = FiltersAPI(client)
    try:
        # Resolve name → ID if needed
        resolved_id = filter_id
        if not _looks_like_uuid(filter_id):
            found = await api.find_filter_by_name(filter_id)
            if found is None:
                console.print(f"[red]Error: Filter '{filter_id}' not found.[/red]")
                raise typer.Exit(1)
            resolved_id = found["id"]

        if not force:
            confirm = typer.confirm(f"Delete filter {resolved_id}?")
            if not confirm:
                format_info("Cancelled")
                raise typer.Exit(0)

        await api.delete_filter(resolved_id)
        format_success(f"Filter deleted: {resolved_id}")
    finally:
        await client.close()


def _looks_like_uuid(value: str) -> bool:
    """Heuristic: a UUID is 36 chars with dashes at positions 8, 13, 18, 23."""
    return len(value) == 36 and value.count("-") == 4
