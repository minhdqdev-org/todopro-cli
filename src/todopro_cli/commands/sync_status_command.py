"""Sync status command - Show sync status."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.ui.formatters import format_output
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Show sync status")
console = Console()


@app.command()
@command_wrapper
async def sync_status(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show synchronization status."""
    from todopro_cli.services.sync_service import SyncService

    strategy = get_strategy_context()
    sync_service = SyncService(factory)

    status = await sync_service.get_status()
    format_output(status.model_dump(), output)
