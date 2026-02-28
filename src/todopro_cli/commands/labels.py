"""Label management commands."""

import typer

from todopro_cli.services.config_service import get_storage_strategy_context
from todopro_cli.services.label_service import LabelService
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.uuid_utils import resolve_label_id

from .decorators import command_wrapper
app = typer.Typer(cls=SuggestingGroup, help="Label management commands")
console = get_console()


@app.command("list")
@command_wrapper
async def list_labels(
    search: str | None = typer.Option(None, "--search", help="Search labels"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """List all labels."""
    if json_opt:
        output = "json"
    storage_strategy_context = get_storage_strategy_context()
    label_repo = storage_strategy_context.label_repository
    label_service = LabelService(label_repo)

    labels = await label_service.list_labels()
    if search:
        search_lower = search.lower()
        labels = [l for l in labels if search_lower in l.name.lower()]
    result = {"labels": [l.model_dump() for l in labels]}
    format_output(result, output, compact=compact)


@app.command("get")
@command_wrapper
async def get_label(
    label_id: str = typer.Argument(..., help="Label ID or suffix (from 'tp label list')"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get label details."""
    storage_strategy_context = get_storage_strategy_context()
    label_repo = storage_strategy_context.label_repository
    label_service = LabelService(label_repo)

    resolved_id = await resolve_label_id(label_id, label_repo)
    label = await label_service.get_label(resolved_id)
    format_output(label.model_dump(), output)


@app.command("create")
@command_wrapper
async def create_label(
    name: str = typer.Argument(..., help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new label."""
    storage_strategy_context = get_storage_strategy_context()
    label_repo = storage_strategy_context.label_repository
    label_service = LabelService(label_repo)

    label = await label_service.create_label(name=name, color=color)
    format_success(f"Label created: {label.id}")
    format_output(label.model_dump(), output)


@app.command("update")
@command_wrapper
async def update_label(
    label_id: str = typer.Argument(..., help="Label ID or suffix (from 'tp label list')"),
    name: str | None = typer.Option(None, "--name", help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a label."""
    if not any([name, color]):
        format_error("No updates specified")
        raise typer.Exit(1)

    storage_strategy_context = get_storage_strategy_context()
    label_repo = storage_strategy_context.label_repository
    label_service = LabelService(label_repo)

    resolved_id = await resolve_label_id(label_id, label_repo)
    label = await label_service.update_label(resolved_id, name=name, color=color)
    format_success(f"Label updated: {resolved_id}")
    format_output(label.model_dump(), output)


@app.command("delete")
@command_wrapper
async def delete_label(
    label_id: str = typer.Argument(..., help="Label ID or suffix (from 'tp label list')"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a label."""
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete label {label_id}?")
        if not confirm:
            format_error("Cancelled")
            raise typer.Exit(0)

    storage_strategy_context = get_storage_strategy_context()
    label_repo = storage_strategy_context.label_repository
    label_service = LabelService(label_repo)

    resolved_id = await resolve_label_id(label_id, label_repo)
    await label_service.delete_label(resolved_id)
    format_success(f"Label deleted: {resolved_id}")
