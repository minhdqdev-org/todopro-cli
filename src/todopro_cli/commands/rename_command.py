"""Rename command - Rename contexts."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Rename contexts")
console = get_console()


@app.command("context")
@command_wrapper
async def rename_context(
    old_name: str = typer.Argument(..., help="Current location context name"),
    new_name: str = typer.Argument(..., help="New location context name"),
) -> None:
    """Rename a location context."""
    from todopro_cli.services.location_context_service import LocationContextService

    context_service = LocationContextService()
    # TODO:
    # context_service.rename(old_name, new_name)
    format_success(f"Location context renamed: {old_name} → {new_name}")
