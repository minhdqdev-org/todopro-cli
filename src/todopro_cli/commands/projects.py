"""Project management commands."""

import typer

from todopro_cli.services.project_service import get_project_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.uuid_utils import resolve_project_uuid

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Project management commands")
console = get_console()


@app.command("list")
@command_wrapper
async def list_projects(
    archived: bool = typer.Option(False, "--archived", help="Show archived projects"),
    favorites: bool = typer.Option(False, "--favorites", help="Show only favorites"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """List projects."""
    project_service = get_project_service()

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
    project_service = get_project_service()

    project_id = await resolve_project_uuid(project_id, project_service.repository)
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
    project_service = get_project_service()

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

    project_service = get_project_service()

    project_id = await resolve_project_uuid(project_id, project_service.repository)
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

    project_service = get_project_service()

    project_id = await resolve_project_uuid(project_id, project_service.repository)
    await project_service.delete_project(project_id)
    format_success(f"Project deleted: {project_id}")


@app.command("archive")
@command_wrapper
async def archive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Archive a project."""
    project_service = get_project_service()

    project_id = await resolve_project_uuid(project_id, project_service.repository)
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
    project_service = get_project_service()

    project_id = await resolve_project_uuid(project_id, project_service.repository)
    project = await project_service.unarchive_project(project_id)
    format_success(f"Project unarchived: {project_id}")
    format_output(project.model_dump(), output)


@app.command("describe")
@command_wrapper
async def describe_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Describe a project in detail."""
    project_service = get_project_service()

    project_id = await resolve_project_uuid(project_id, project_service.repository)
    project = await project_service.get_project(project_id)
    format_output(project.model_dump(), output)


@app.command("view")
def view_project(
    project_code: str = typer.Argument(..., help="Project code or ID"),
    layout: str = typer.Option("board", "--layout", help="View layout (board)"),
) -> None:
    """View project in interactive TUI board mode."""
    from todopro_cli.utils.ui.board_view import run_board_view

    if layout != "board":
        format_error(f"Unsupported layout: {layout}. Only 'board' is supported.")
        raise typer.Exit(1)

    run_board_view(project_code)


# ---------- share (collaborate) sub-typer ----------
from .collaborate_command import app as _collaborate_app  # noqa: E402

app.add_typer(_collaborate_app, name="share", help="Manage project collaboration")
