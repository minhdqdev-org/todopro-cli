"""Command 'version' of todopro-cli"""

import typer

from todopro_cli import __version__
from todopro_cli.utils.ui.console import get_console

app = typer.Typer()
console = get_console(highlight=False)


# Add top-level commands
@app.command()
def version() -> None:
    """Show version information"""
    console.print(__version__)
