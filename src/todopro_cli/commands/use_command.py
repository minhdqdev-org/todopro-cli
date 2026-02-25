"""Use command - Switch/use contexts."""

import typer

from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Switch/use contexts")
console = get_console()


@app.command("context")
@command_wrapper
async def use_context(
    name: str = typer.Argument(..., help="Context name (local/cloud)"),
) -> None:
    """Switch to a different storage context."""

    config_service = get_config_service()

    # Check if already using this context
    try:
        current = config_service.get_current_context()
        if current and current.name == name:
            console.print(
                f"[yellow]ℹ[/yellow] Already using context '[cyan]{name}[/cyan]' ([dim]{current.type}[/dim])"
            )
            console.print(f"  Source: [dim]{current.source}[/dim]")
            return
    except (ValueError, KeyError):
        # No current context, continue with switch
        pass

    ctx = config_service.use_context(name)
    format_success(f"Switched to context: {ctx.name}")
