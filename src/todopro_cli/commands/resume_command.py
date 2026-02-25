"""Resume command - Resume paused focus sessions."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Resume focus sessions")
console = get_console()


@app.command("focus")
def resume_focus(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
):
    """Resume a paused focus session."""
    from todopro_cli.commands.focus import resume_focus as _impl

    _impl()
