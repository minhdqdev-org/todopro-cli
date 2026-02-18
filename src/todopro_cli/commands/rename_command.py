"""Rename command - Rename contexts."""

import typer
from rich.console import Console

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Rename contexts")
console = Console()


@app.command("context")
@command_wrapper
async def rename_context(
    old_name: str = typer.Argument(..., help="Current context name"),
    new_name: str = typer.Argument(..., help="New context name"),
) -> None:
    """Rename a storage context."""
    from todopro_cli.services.context_service import ContextService

    context_service = ContextService()
    context_service.rename_context(old_name, new_name)
    format_success(f"Context renamed: {old_name} → {new_name}")
