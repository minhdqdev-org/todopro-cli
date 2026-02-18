"""Push command - Push data to remote (sync)."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Push data to remote")
console = Console()


@app.command()
@command_wrapper
async def push(
    force: bool = typer.Option(False, "--force", "-f", help="Force push"),
) -> None:
    """Push data to remote context."""
    from todopro_cli.services.sync_service import SyncService

    strategy = get_strategy_context()
    sync_service = SyncService(factory)

    await sync_service.push(force=force)
    format_success("Data pushed to remote")
