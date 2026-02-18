"""Check command - Check achievements and location."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.ui.formatters import format_output
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Check achievements and location")
console = Console()


@app.command("achievements")
@command_wrapper
async def check_achievements(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Check for new achievements."""
    from todopro_cli.services.achievement_service import AchievementService

    strategy = get_strategy_context()
    repo = factory.get_achievement_repository()
    service = AchievementService(repo)

    new_achievements = await service.check_achievements()
    result = {"achievements": [a.model_dump() for a in new_achievements]}
    format_output(result, output)


@app.command("location")
@command_wrapper
async def check_location(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Check current location context."""
    from todopro_cli.services.location_context_service import LocationContextService

    strategy = get_strategy_context()
    repo = factory.get_location_context_repository()
    service = LocationContextService(repo)

    location = await service.check_current_location()
    format_output(location.model_dump() if location else {"location": "Unknown"}, output)
