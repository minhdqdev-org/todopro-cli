"""Label management commands."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.label_service import LabelService
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Label management commands")
console = Console()


@app.command("list")
@command_wrapper
async def list_labels(
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all labels."""
    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    labels = await label_service.list_labels()
    result = {"labels": [l.model_dump() for l in labels]}
    format_output(result, output)


@app.command("get")
@command_wrapper
async def get_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Get label details."""
    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    label = await label_service.get_label(label_id)
    format_output(label.model_dump(), output)


@app.command("create")
@command_wrapper
async def create_label(
    name: str = typer.Argument(..., help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Create a new label."""
    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    label = await label_service.create_label(name=name, color=color)
    format_success(f"Label created: {label.id}")
    format_output(label.model_dump(), output)


@app.command("update")
@command_wrapper
async def update_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    name: str | None = typer.Option(None, "--name", help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Update a label."""
    if not any([name, color]):
        format_error("No updates specified")
        raise typer.Exit(1)

    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    label = await label_service.update_label(label_id, name=name, color=color)
    format_success(f"Label updated: {label_id}")
    format_output(label.model_dump(), output)


@app.command("delete")
@command_wrapper
async def delete_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a label."""
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete label {label_id}?")
        if not confirm:
            format_error("Cancelled")
            raise typer.Exit(0)

    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    await label_service.delete_label(label_id)
    format_success(f"Label deleted: {label_id}")
