"""Sync status command - Show sync status."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Show sync status")
console = get_console()


@app.command()
@command_wrapper
async def sync_status(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show synchronization status."""
    from todopro_cli.services.sync_service import SyncService

    storage_strategy_context = get_storage_strategy_context()
    sync_service = SyncService(factory)

    status = await sync_service.get_status()
    format_output(status.model_dump(), output)
