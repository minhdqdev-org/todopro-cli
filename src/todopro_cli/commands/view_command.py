"""Command 'view' of todopro-cli"""

import typer

from todopro_cli.utils.ui.board_view import run_board_view
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error

app = typer.Typer()
console = get_console()


@app.command()
def view(
    project_code: str = typer.Argument(..., help="Project code or ID"),
    layout: str = typer.Option("board", "--layout", help="View layout (board)"),
) -> None:
    """View project in interactive TUI board mode."""
    # Delegate to projects command
    """View project in interactive TUI mode."""
    if layout != "board":
        format_error(f"Unsupported layout: {layout}. Only 'board' layout is supported.")
        raise typer.Exit(1)

    run_board_view(project_code)
