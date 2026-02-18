"""Start command - Start focus sessions and timers."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.ui.formatters import format_success, format_output
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Start focus sessions and timers")
console = Console()


@app.command("focus")
@command_wrapper
async def start_focus(
    task_id: str | None = typer.Option(None, "--task", help="Task ID to focus on"),
    duration: int = typer.Option(25, "--duration", help="Session duration in minutes"),
    template: str | None = typer.Option(None, "--template", help="Template ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Start a focus session."""
    from todopro_cli.services.focus_service import FocusService

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    session = await service.start_session(
        task_id=task_id,
        duration=duration,
        template_id=template,
    )
    format_success("Focus session started")
    format_output(session.model_dump(), output)


@app.command("timer")
@command_wrapper
async def start_timer(
    duration: int = typer.Argument(25, help="Duration in minutes"),
    task_id: str | None = typer.Option(None, "--task", help="Task ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Start a Pomodoro timer."""
    from todopro_cli.services.timer_service import TimerService

    strategy = get_strategy_context()
    timer_repo = factory.get_timer_repository()
    service = TimerService(timer_repo)

    session = await service.start_timer(duration=duration, task_id=task_id)
    format_success(f"Timer started: {duration} minutes")
    format_output(session.model_dump(), output)
