"""Pull command - Pull data from remote (sync)."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Pull data from remote")
console = get_console()


@app.command()
@command_wrapper
async def pull(
    force: bool = typer.Option(False, "--force", "-f", help="Force pull"),
) -> None:
    """Pull data from remote context."""
    from todopro_cli.services.sync_service import SyncService

    storage_strategy_context = get_storage_strategy_context()
    sync_service = SyncService(factory)

    await sync_service.pull(force=force)
    format_success("Data pulled from remote")
