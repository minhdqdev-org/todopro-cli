"""Pull command - Pull data from remote (sync)."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.ui.formatters import format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Pull data from remote")
console = Console()


@app.command()
@command_wrapper
async def pull(
    force: bool = typer.Option(False, "--force", "-f", help="Force pull"),
) -> None:
    """Pull data from remote context."""
    from todopro_cli.services.sync_service import SyncService

    strategy = get_strategy_context()
    sync_service = SyncService(factory)

    await sync_service.pull(force=force)
    format_success("Data pulled from remote")
