"""Delete command - Delete resources."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.label_service import LabelService
from todopro_cli.services.project_service import ProjectService
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_info, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Delete resources")
console = Console()


@app.command("task")
@command_wrapper
async def delete_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a task."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)

    if not force:
        confirm = typer.confirm(f"Delete task {resolved_id}?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    await task_service.delete_task(resolved_id)
    format_success(f"Task deleted: {resolved_id}")


@app.command("project")
@command_wrapper
async def delete_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a project."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

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
    strategy = get_strategy_context()
    label_repo = strategy.label_repository
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

    strategy = get_strategy_context()
    repo = factory.get_location_context_repository()
    service = LocationContextService(repo)

    if not force:
        confirm = typer.confirm(f"Delete location context {name}?")
        if not confirm:
            format_info("Cancelled")
            raise typer.Exit(0)

    await service.delete_context(name)
    format_success(f"Location context deleted: {name}")
