"""Check command - Check achievements and location."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Check achievements and location")
console = get_console()


@app.command("achievements")
@command_wrapper
async def check_achievements(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Check for new achievements."""
    from todopro_cli.services.achievement_service import (
        get_achievement_service,
    )

    service = get_achievement_service()

    new_achievements = await service.check_achievements()
    result = {"achievements": [a.model_dump() for a in new_achievements]}
    format_output(result, output)


@app.command("location")
@command_wrapper
async def check_location(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Check current location context."""
    from todopro_cli.services.location_context_service import (
        get_location_context_service,
    )

    service = get_location_context_service()

    location = await service.check_current_location()
    format_output(
        location.model_dump() if location else {"location": "Unknown"}, output
    )
