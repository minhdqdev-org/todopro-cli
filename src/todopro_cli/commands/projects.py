"""Project management commands."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.project_service import ProjectService
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.uuid_utils import resolve_project_uuid

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Project management commands")
console = Console()


@app.command("list")
@command_wrapper
async def list_projects(
    archived: bool = typer.Option(False, "--archived", help="Show archived projects"),
    favorites: bool = typer.Option(False, "--favorites", help="Show only favorites"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """List projects."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    projects = await project_service.list_projects(
        is_archived=archived or None,
        is_favorite=favorites or None,
    )

    # Convert to dict format for formatters
    result = {"projects": [p.model_dump() for p in projects]}
    format_output(result, output, compact=compact)


@app.command("get")
@command_wrapper
async def get_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output"),
) -> None:
    """Get project details."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project_id = await resolve_project_uuid(project_id, project_repo)
    project = await project_service.get_project(project_id)
    format_output(project.model_dump(), output)


@app.command("create")
@command_wrapper
async def create_project(
    name: str = typer.Argument(..., help="Project name"),
    color: str | None = typer.Option(None, "--color", help="Project color"),
    favorite: bool = typer.Option(False, "--favorite", help="Mark as favorite"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new project."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project = await project_service.create_project(
        name=name, color=color, is_favorite=favorite
    )
    format_success(f"Project created: {project.id}")
    format_output(project.model_dump(), output)


@app.command("update")
@command_wrapper
async def update_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    name: str | None = typer.Option(None, "--name", help="Project name"),
    color: str | None = typer.Option(None, "--color", help="Project color"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a project."""
    if name is None and color is None:
        format_error("No updates specified")
        raise typer.Exit(1)

    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project_id = await resolve_project_uuid(project_id, project_repo)
    project = await project_service.update_project(project_id, name=name, color=color)
    format_success(f"Project updated: {project_id}")
    format_output(project.model_dump(), output)


@app.command("delete")
@command_wrapper
async def delete_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a project."""
    if not yes and not typer.confirm(
        f"Are you sure you want to delete project {project_id}?"
    ):
        format_error("Cancelled")
        raise typer.Exit(0)

    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project_id = await resolve_project_uuid(project_id, project_repo)
    await project_service.delete_project(project_id)
    format_success(f"Project deleted: {project_id}")


@app.command("archive")
@command_wrapper
async def archive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Archive a project."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project_id = await resolve_project_uuid(project_id, project_repo)
    project = await project_service.archive_project(project_id)
    format_success(f"Project archived: {project_id}")
    format_output(project.model_dump(), output)


@app.command("unarchive")
@command_wrapper
async def unarchive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Unarchive a project."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project_id = await resolve_project_uuid(project_id, project_repo)
    project = await project_service.unarchive_project(project_id)
    format_success(f"Project unarchived: {project_id}")
    format_output(project.model_dump(), output)
