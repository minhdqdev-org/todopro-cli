"""Stop command - Stop focus sessions."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Stop focus sessions")
console = get_console()


@app.command("focus")
def stop_focus(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Stop the current focus session."""
    from todopro_cli.commands.focus import stop_focus as _impl

    _impl()
