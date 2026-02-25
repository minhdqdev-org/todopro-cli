"""Utility commands."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_error

app = typer.Typer(cls=SuggestingGroup, help="Utility commands")
console = get_console()


def handle_api_error(exception: Exception, action: str) -> None:
    """Handle API errors uniformly."""
    format_error(f"Error {action}: {str(exception)}")
    raise typer.Exit(1)
