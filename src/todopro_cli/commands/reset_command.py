"""Reset command - Reset configuration and goals."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Reset configuration and goals")
console = Console()


@app.command("config")
@command_wrapper
async def reset_config(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Reset configuration to defaults."""
    from todopro_cli.services.config_service import ConfigService

    if not force:
        confirm = typer.confirm("Reset all configuration to defaults?")
        if not confirm:
            raise typer.Exit(0)

    config_service = ConfigService()
    config_service.reset()
    format_success("Configuration reset to defaults")


@app.command("goals")
@command_wrapper
async def reset_goals(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Reset all focus goals."""
    from todopro_cli.services.focus_service import FocusService

    if not force:
        confirm = typer.confirm("Reset all goals?")
        if not confirm:
            raise typer.Exit(0)

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    await service.reset_goals()
    format_success("All goals reset")
