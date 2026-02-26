"""Set command - Set configuration and goals."""

from datetime import UTC

import typer

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Set configuration and goals")
console = get_console()


@app.command("config")
@command_wrapper
async def set_config(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Set a configuration value."""
    from todopro_cli.services.config_service import ConfigService

    config_service = ConfigService()
    config_service.set(key, value)
    format_success(f"Configuration updated: {key}={value}")

    result = {"key": key, "value": value}
    format_output(result, output)


@app.command("goal")
@command_wrapper
async def set_goal(
    goal_type: str = typer.Argument(
        ...,
        help="Goal type: daily-sessions, daily-minutes, weekly-sessions, weekly-minutes, streak-target",
    ),
    target: int = typer.Argument(..., help="Target value"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Set a focus goal."""
    from todopro_cli.models.focus.goals import GoalsManager
    from todopro_cli.services.config_service import get_config_service
    from todopro_cli.utils.ui.formatters import format_success

    svc = get_config_service()
    manager = GoalsManager(config=svc.load_config(), save_config=svc.save_config)
    manager.set_goal(goal_type.replace("-", "_"), target)
    format_success(f"Goal set: {goal_type} = {target}")


@app.command("timezone")
@command_wrapper
async def set_timezone(
    timezone: str = typer.Argument(..., help="Timezone (e.g., America/New_York)"),
) -> None:
    """Set user timezone."""
    from todopro_cli.services.auth_service import AuthService

    auth_service = AuthService()
    await auth_service.set_timezone(timezone)
    format_success(f"Timezone set: {timezone}")


@app.command("reminder")
@command_wrapper
async def set_reminder(
    task_id: str = typer.Argument(..., help="Task ID"),
    when: str = typer.Argument(
        ...,
        help="When to remind: '30min', '1h', '2h', '1d', or ISO datetime (YYYY-MM-DDTHH:MM:SS)",
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Set a reminder for a task.

    Time formats: 30min, 1h, 2h, 1d, or ISO datetime.
    """
    from datetime import datetime, timedelta

    # Parse human-readable time offset or ISO datetime
    now = datetime.now(tz=UTC)
    reminder_dt: datetime | None = None

    _OFFSETS = {
        "30min": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "2h": timedelta(hours=2),
        "3h": timedelta(hours=3),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
        "1d": timedelta(days=1),
        "2d": timedelta(days=2),
    }

    if when in _OFFSETS:
        reminder_dt = now + _OFFSETS[when]
    else:
        try:
            reminder_dt = datetime.fromisoformat(when)
            if reminder_dt.tzinfo is None:
                reminder_dt = reminder_dt.replace(tzinfo=UTC)
        except ValueError:
            console.print(
                f"[red]Error: Cannot parse '{when}'. "
                f"Use '30min', '1h', '2h', '1d', or ISO format (YYYY-MM-DDTHH:MM:SS).[/red]"
            )
            raise typer.Exit(1)

    if reminder_dt <= now:
        console.print("[red]Error: Reminder time must be in the future.[/red]")
        raise typer.Exit(1)

    client = get_client()
    api = TasksAPI(client)
    try:
        result = await api.set_reminder(task_id, reminder_dt.isoformat())
        format_success(
            f"Reminder set for task {task_id} at {reminder_dt.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        format_output(result, output)
    finally:
        await client.close()
