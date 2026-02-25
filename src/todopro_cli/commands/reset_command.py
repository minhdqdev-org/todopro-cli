"""Reset command - Reset configuration and goals."""

import typer

from todopro_cli.services.config_service import get_config_service
from todopro_cli.services.goal_service import get_goal_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Reset configuration and goals")
console = get_console()


@app.command("config")
@command_wrapper
async def reset_config(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Reset configuration to defaults."""

    if not force:
        confirm = typer.confirm("Reset all configuration to defaults?")
        if not confirm:
            raise typer.Exit(0)

    get_config_service().reset_config()
    format_success("Configuration reset to defaults")


@app.command("goals")
@command_wrapper
async def reset_goals(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Reset all focus goals to defaults."""

    if not force:
        confirm = typer.confirm("Reset all goals?")
        if not confirm:
            raise typer.Exit(0)

    get_goal_service().reset_goals()
    format_success("All goals reset")
