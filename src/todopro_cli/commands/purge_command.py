"""Purge command - Delete all data."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_info, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Delete all data")
console = get_console()


@app.command("data")
@command_wrapper
async def purge_data() -> None:
    """Delete all data with multi-step confirmation."""
    from todopro_cli.services.data_service import DataService

    console.print("[bold red]⚠️  WARNING: This will delete ALL data![/bold red]")
    console.print("This action cannot be undone.")

    confirm1 = typer.confirm("Are you absolutely sure?")
    if not confirm1:
        format_info("Cancelled")
        raise typer.Exit(0)

    confirm2 = typer.confirm("Type 'yes' to confirm permanent deletion")
    if not confirm2:
        format_info("Cancelled")
        raise typer.Exit(0)

    storage_strategy_context = get_storage_strategy_context()
    data_service = DataService(factory)

    await data_service.purge_all()
    format_success("All data has been deleted")
