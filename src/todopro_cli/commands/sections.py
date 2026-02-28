"""Section management commands."""

import typer

from todopro_cli.services.config_service import get_storage_strategy_context
from todopro_cli.services.section_service import get_section_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.uuid_utils import resolve_project_uuid, resolve_section_id

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Section management commands")
console = get_console()


@app.command("list")
@command_wrapper
async def list_sections(
    project_id: str = typer.Argument(..., help="Project ID, name, or suffix (from 'tp project list')"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """List sections in a project."""
    if json_opt:
        output = "json"
    storage_strategy_context = get_storage_strategy_context()
    resolved_project_id = await resolve_project_uuid(project_id, storage_strategy_context.project_repository)
    section_service = get_section_service()
    sections = await section_service.list_sections(resolved_project_id)
    result = {"sections": [s.model_dump() for s in sections]}
    format_output(result, output)


@app.command("get")
@command_wrapper
async def get_section(
    project_id: str = typer.Argument(..., help="Project ID, name, or suffix"),
    section_id: str = typer.Argument(..., help="Section ID or suffix (from 'tp section list <project>')"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get a section by ID."""
    storage_strategy_context = get_storage_strategy_context()
    resolved_project_id = await resolve_project_uuid(project_id, storage_strategy_context.project_repository)
    section_service = get_section_service()
    resolved_section_id = await resolve_section_id(section_id, section_service.repository, resolved_project_id)
    section = await section_service.get_section(resolved_project_id, resolved_section_id)
    format_output(section.model_dump(), output)


@app.command("create")
@command_wrapper
async def create_section(
    project_id: str = typer.Argument(..., help="Project ID, name, or suffix"),
    name: str = typer.Argument(..., help="Section name"),
    display_order: int = typer.Option(
        0, "--order", help="Display order position"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new section within a project."""
    storage_strategy_context = get_storage_strategy_context()
    resolved_project_id = await resolve_project_uuid(project_id, storage_strategy_context.project_repository)
    section_service = get_section_service()
    section = await section_service.create_section(
        resolved_project_id, name, display_order=display_order
    )
    format_success(f"Section created: {section.id}")
    format_output(section.model_dump(), output)


@app.command("update")
@command_wrapper
async def update_section(
    project_id: str = typer.Argument(..., help="Project ID, name, or suffix"),
    section_id: str = typer.Argument(..., help="Section ID or suffix"),
    name: str | None = typer.Option(None, "--name", help="New section name"),
    display_order: int | None = typer.Option(
        None, "--order", help="New display order position"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a section."""
    if name is None and display_order is None:
        format_error("No updates specified")
        raise typer.Exit(1)

    storage_strategy_context = get_storage_strategy_context()
    resolved_project_id = await resolve_project_uuid(project_id, storage_strategy_context.project_repository)
    section_service = get_section_service()
    resolved_section_id = await resolve_section_id(section_id, section_service.repository, resolved_project_id)
    section = await section_service.update_section(
        resolved_project_id, resolved_section_id, name=name, display_order=display_order
    )
    format_success(f"Section updated: {resolved_section_id}")
    format_output(section.model_dump(), output)


@app.command("delete")
@command_wrapper
async def delete_section(
    project_id: str = typer.Argument(..., help="Project ID, name, or suffix"),
    section_id: str = typer.Argument(..., help="Section ID or suffix"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a section (tasks in the section remain in the project)."""
    if not yes and not typer.confirm(
        f"Are you sure you want to delete section {section_id}?"
    ):
        format_error("Cancelled")
        raise typer.Exit(0)

    storage_strategy_context = get_storage_strategy_context()
    resolved_project_id = await resolve_project_uuid(project_id, storage_strategy_context.project_repository)
    section_service = get_section_service()
    resolved_section_id = await resolve_section_id(section_id, section_service.repository, resolved_project_id)
    await section_service.delete_section(resolved_project_id, resolved_section_id)
    format_success(f"Section deleted: {resolved_section_id}")


@app.command("reorder")
@command_wrapper
async def reorder_sections(
    project_id: str = typer.Argument(..., help="Project ID, name, or suffix"),
    orders: list[str] = typer.Argument(
        ...,
        help="Space-separated list of section_id:display_order pairs (e.g. abc:0 def:1)",
    ),
) -> None:
    """Reorder sections within a project.

    Example:
        todopro section reorder <project_id> abc123:0 def456:1 ghi789:2
    """
    storage_strategy_context = get_storage_strategy_context()
    resolved_project_id = await resolve_project_uuid(project_id, storage_strategy_context.project_repository)
    section_service = get_section_service()

    section_orders = []
    for order_str in orders:
        parts = order_str.split(":")
        if len(parts) != 2:
            format_error(f"Invalid format '{order_str}'. Expected 'section_id:display_order'")
            raise typer.Exit(1)
        section_id_part, pos_str = parts
        try:
            pos = int(pos_str)
        except ValueError:
            format_error(f"Invalid display_order '{pos_str}'. Must be an integer.")
            raise typer.Exit(1)
        resolved_sid = await resolve_section_id(section_id_part, section_service.repository, resolved_project_id)
        section_orders.append({"section_id": resolved_sid, "display_order": pos})

    await section_service.reorder_sections(resolved_project_id, section_orders)
    format_success("Sections reordered successfully")
