"""Command 'reschedule' of todopro-cli"""

import typer

from todopro_cli.utils.ui.console import get_console

from .decorators import command_wrapper
from .tasks_command import reschedule

app = typer.Typer()
console = get_console()


@app.command("reschedule")
@command_wrapper
def reschedule_command(
    task_id: str | None = typer.Argument(
        None, help="Task ID or suffix (omit to reschedule all overdue tasks)"
    ),
    date: str | None = typer.Option(
        None, "--date", "-d", help="New due date (today/tomorrow/YYYY-MM-DD)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reschedule a task or all overdue tasks to today."""
    reschedule(target=task_id, date=date, yes=yes)
