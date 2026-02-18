"""Utility commands."""

import typer
from rich.console import Console

from todopro_cli.utils.ui.formatters import format_error
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Utility commands")
console = Console()


def handle_api_error(exception: Exception, action: str) -> None:
    """Handle API errors uniformly."""
    format_error(f"Error {action}: {str(exception)}")
    raise typer.Exit(1)
