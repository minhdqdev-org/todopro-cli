"""Resume command - Resume paused focus sessions."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_output, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Resume focus sessions")
console = Console()


@app.command("focus")
@command_wrapper
async def resume_focus(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Resume a paused focus session."""
    from todopro_cli.services.focus_service import FocusService

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    session = await service.resume_session()
    format_success("Focus session resumed")
    format_output(session.model_dump(), output)
