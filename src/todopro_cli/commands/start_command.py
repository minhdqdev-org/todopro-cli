"""Start command - Start focus sessions and timers."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Start focus sessions and timers")
console = get_console()


@app.command("focus")
def start_focus(
    task_id: str = typer.Argument(..., help="Task ID to focus on"),
    duration: int = typer.Option(25, "--duration", help="Session duration in minutes"),
    template: str | None = typer.Option(None, "--template", help="Template name"),
) -> None:
    """Start a focus session on a task."""

    if template is not None:
        from todopro_cli.commands.focus import start_focus as _impl

        _impl(task_id=task_id, duration=duration, template=template)
