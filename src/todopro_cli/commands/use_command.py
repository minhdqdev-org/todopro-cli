"""Use command - Switch/use contexts."""

import typer
from rich.console import Console

from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Switch/use contexts")
console = Console()


@app.command("context")
@command_wrapper
async def use_context(
    name: str = typer.Argument(..., help="Context name (local/cloud)"),
) -> None:
    """Switch to a different storage context."""

    config_service = get_config_service()
    config_service.use_context(name)
    format_success(f"Switched to context: {name}")
