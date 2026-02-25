"""Status command - Show status (focus, encryption, etc.)."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Show status")
console = get_console()


@app.command("focus")
def status_focus(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show current focus session status."""
    from todopro_cli.commands.focus import focus_status as _impl

    _impl()
