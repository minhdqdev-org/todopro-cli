"""Set command - Set configuration and goals."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_output, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Set configuration and goals")
console = Console()


@app.command("config")
@command_wrapper
async def set_config(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Set a configuration value."""
    from todopro_cli.services.config_service import ConfigService

    config_service = ConfigService()
    config_service.set(key, value)
    format_success(f"Configuration updated: {key}={value}")

    result = {"key": key, "value": value}
    format_output(result, output)


@app.command("goal")
@command_wrapper
async def set_goal(
    goal_type: str = typer.Argument(..., help="Goal type (daily/weekly/monthly)"),
    target: int = typer.Argument(..., help="Target value"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Set a focus goal."""
    from todopro_cli.services.focus_service import FocusService

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    goal = await service.set_goal(goal_type=goal_type, target=target)
    format_success(f"Goal set: {goal_type} = {target}")
    format_output(goal.model_dump(), output)


@app.command("timezone")
@command_wrapper
async def set_timezone(
    timezone: str = typer.Argument(..., help="Timezone (e.g., America/New_York)"),
) -> None:
    """Set user timezone."""
    from todopro_cli.services.auth_service import AuthService

    auth_service = AuthService()
    await auth_service.set_timezone(timezone)
    format_success(f"Timezone set: {timezone}")
