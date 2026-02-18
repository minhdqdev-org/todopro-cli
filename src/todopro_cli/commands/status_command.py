"""Status command - Show status (focus, encryption, etc.)."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Show status")
console = Console()


@app.command("focus")
@command_wrapper
async def status_focus(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show current focus session status."""
    from todopro_cli.services.focus_service import FocusService

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    status = await service.get_status()
    format_output(status.model_dump(), output)


@app.command("encryption")
@command_wrapper
async def status_encryption(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show encryption status."""
    from todopro_cli.services.encryption_service import EncryptionService

    service = EncryptionService()
    status = await service.get_status()
    format_output(status.model_dump(), output)
