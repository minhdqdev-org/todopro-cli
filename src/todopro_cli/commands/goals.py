"""Goals and targets commands."""

import typer
from rich.table import Table

from todopro_cli.models.focus.goals import GoalsManager
from todopro_cli.utils.ui.console import get_console

console = get_console()
app = typer.Typer(help="Focus goals and targets")


def format_duration(minutes: float) -> str:
    """Format minutes as hours and minutes."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def render_progress_bar(value: float, max_value: float, width: int = 12) -> str:
    """Render a progress bar using block characters."""
    if max_value == 0:
        ratio = 0
    else:
        ratio = min(value / max_value, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


@app.command("show")
@app.command()
def show_goals():
    """Show current goals and progress."""
    manager = GoalsManager()
    goals = manager.get_goals()
    progress = manager.get_all_progress()

    console.print("\n[bold cyan]🎯 Focus Goals & Progress[/bold cyan]\n")

    # Daily goals
    daily = progress["daily"]
    console.print("[bold]Daily Goals[/bold]")

    sessions = daily["sessions"]
    sessions_bar = render_progress_bar(sessions["current"], sessions["target"])
    sessions_status = "[green]✓[/green]" if sessions["achieved"] else ""
    console.print(
        f"  Sessions:     {sessions['current']}/{sessions['target']}  "
        f"{sessions_bar} {sessions['progress']:.0f}% {sessions_status}"
    )

    minutes = daily["minutes"]
    minutes_bar = render_progress_bar(minutes["current"], minutes["target"])
    minutes_status = "[green]✓[/green]" if minutes["achieved"] else ""
    console.print(
        f"  Focus Time:   {format_duration(minutes['current'])}/{format_duration(minutes['target'])}  "
        f"{minutes_bar} {minutes['progress']:.0f}% {minutes_status}"
    )

    # Weekly goals
    console.print("\n[bold]Weekly Goals[/bold]")

    weekly = progress["weekly"]
    sessions = weekly["sessions"]
    sessions_bar = render_progress_bar(sessions["current"], sessions["target"])
    sessions_status = "[green]✓[/green]" if sessions["achieved"] else ""
    console.print(
        f"  Sessions:     {sessions['current']}/{sessions['target']}  "
        f"{sessions_bar} {sessions['progress']:.0f}% {sessions_status}"
    )

    minutes = weekly["minutes"]
    minutes_bar = render_progress_bar(minutes["current"], minutes["target"])
    minutes_status = "[green]✓[/green]" if minutes["achieved"] else ""
    console.print(
        f"  Focus Time:   {format_duration(minutes['current'])}/{format_duration(minutes['target'])}  "
        f"{minutes_bar} {minutes['progress']:.0f}% {minutes_status}"
    )

    # Streak goal
    console.print("\n[bold]Streak Goal[/bold]")

    streak = progress["streak"]
    streak_bar = render_progress_bar(streak["current"], streak["target"])
    streak_status = "[green]✓ Target reached![/green]" if streak["achieved"] else ""
    console.print(
        f"  Current:      {streak['current']}/{streak['target']} days  "
        f"{streak_bar} {streak['progress']:.0f}% {streak_status}"
    )
    console.print(f"  Longest:      {streak['longest']} days")

    # Motivation
    console.print()
    achievements = manager.check_achievements()

    if len(achievements) >= 4:
        console.print(
            "[bold green]🎉 Amazing! You've hit most of your goals![/bold green]"
        )
    elif len(achievements) >= 2:
        console.print("[bold cyan]💪 Great progress! Keep it up![/bold cyan]")
    elif len(achievements) >= 1:
        console.print("[bold]✨ Nice! You've achieved some goals.[/bold]")
    else:
        # Calculate what's needed
        daily_sessions_left = max(
            0, daily["sessions"]["target"] - daily["sessions"]["current"]
        )
        weekly_sessions_left = max(
            0, weekly["sessions"]["target"] - weekly["sessions"]["current"]
        )

        if daily_sessions_left > 0:
            console.print(
                f"[dim]💡 Tip: {daily_sessions_left} more sessions today to hit your daily goal![/dim]"
            )
        elif weekly_sessions_left > 0:
            console.print(
                f"[dim]💡 Tip: {weekly_sessions_left} more sessions this week to hit your weekly goal![/dim]"
            )

    console.print()


@app.command("set")
def set_goal(
    goal_type: str = typer.Argument(
        ...,
        help="Goal type: daily-sessions, daily-minutes, weekly-sessions, weekly-minutes, streak-target",
    ),
    value: int = typer.Argument(..., help="Target value"),
):
    """Set a focus goal."""
    # Convert hyphenated to underscore
    goal_type = goal_type.replace("-", "_")

    try:
        manager = GoalsManager()
        manager.set_goal(goal_type, value)

        # Format display
        if "minutes" in goal_type:
            display_value = format_duration(value)
        elif "streak" in goal_type:
            display_value = f"{value} days"
        else:
            display_value = f"{value} sessions"

        console.print(
            f"\n[green]✓ Goal set: {goal_type.replace('_', ' ').title()} = {display_value}[/green]\n"
        )

    except ValueError as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
        raise typer.Exit(1)


@app.command("list")
def list_goals():
    """List all configured goals."""
    manager = GoalsManager()
    goals = manager.get_goals()

    console.print("\n[bold cyan]Focus Goals Configuration[/bold cyan]\n")

    table = Table(show_header=True)
    table.add_column("Goal", style="cyan")
    table.add_column("Target", justify="right")
    table.add_column("Type", style="dim")

    table.add_row("Daily Sessions", str(goals["daily_sessions"]), "sessions/day")
    table.add_row(
        "Daily Focus Time", format_duration(goals["daily_minutes"]), "focus time/day"
    )
    table.add_row("Weekly Sessions", str(goals["weekly_sessions"]), "sessions/week")
    table.add_row(
        "Weekly Focus Time", format_duration(goals["weekly_minutes"]), "focus time/week"
    )
    table.add_row("Streak Target", f"{goals['streak_target']} days", "consecutive days")

    console.print(table)
    console.print(
        "\n[dim]Use 'todopro goals set <type> <value>' to update goals[/dim]\n"
    )


@app.command("reset")
def reset_goals():
    """Reset goals to defaults."""
    manager = GoalsManager()

    defaults = {
        "daily_sessions": 8,
        "daily_minutes": 200,
        "weekly_sessions": 40,
        "weekly_minutes": 1000,
        "streak_target": 30,
    }

    manager.config.focus_goals = defaults
    manager.context_manager.save_config()

    console.print("\n[green]✓ Goals reset to defaults[/green]")
    console.print("\n[dim]Run 'todopro goals list' to see default values[/dim]\n")


@app.callback(invoke_without_command=True)
def goals_callback(ctx: typer.Context):
    """
    Manage focus goals and track progress.

    If no command given, show current progress.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(show_goals)
