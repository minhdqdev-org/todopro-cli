"""Remote (server-backed) rendering for `goals` and `achievements`.

The local implementations track *focus sessions* out of the config file and the
focus SQLite DB — per-device state that is lost on reinstall and never syncs.
Against a remote context the server is the source of truth, so these render
`analytics.Goal` / `analytics.UserAchievement` instead.

Kept in its own module so the local code paths in ``commands/goals.py`` and
``commands/achievements_command.py`` stay untouched.
"""

from __future__ import annotations

import asyncio

from rich.panel import Panel
from rich.table import Table

from todopro_cli.services.api.client import APIClient
from todopro_cli.services.api.goals import AchievementsAPI, GoalsAPI
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.ui.console import get_console

console = get_console()


def is_remote_context() -> bool:
    """True when the active context talks to the API rather than local SQLite."""
    try:
        context = get_config_service().config.get_current_context()
    except (ValueError, KeyError, AttributeError):
        return False
    return bool(context and context.type != "local")


def _run(coro):
    return asyncio.run(coro)


def render_progress_bar(value: float, max_value: float, width: int = 20) -> str:
    ratio = 0 if max_value == 0 else min(value / max_value, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


# ── goals ────────────────────────────────────────────────────────────────────


async def _fetch_progress() -> dict:
    client = APIClient()
    return await GoalsAPI(client).get_progress()


async def _fetch_goals(include_archived: bool = False) -> list[dict]:
    client = APIClient()
    return await GoalsAPI(client).list_goals(include_archived=include_archived)


async def _create_goal(period: str, target: int) -> dict:
    client = APIClient()
    return await GoalsAPI(client).create_goal(period, target)


async def _update_goal(goal_id: str, target: int) -> dict:
    client = APIClient()
    return await GoalsAPI(client).update_goal(goal_id, target_value=target)


def show_remote_goals() -> None:
    """`todopro goals` against a remote context."""
    payload = _run(_fetch_progress())
    goals = payload.get("goals", [])

    console.print("\n[bold cyan]🎯 Goals & Progress[/bold cyan]\n")
    if not goals:
        console.print("[yellow]No goals set.[/yellow]")
        console.print(
            "\n[dim]Set one with 'todopro goals set daily 5'[/dim]\n"
        )
        return

    for goal in goals:
        bar = render_progress_bar(goal["achieved_value"], goal["target_value"] or 1)
        status = "[green]✓[/green]" if goal["is_met"] else ""
        console.print(
            f"  [bold]{goal['period'].title():8}[/bold] "
            f"{goal['achieved_value']}/{goal['target_value']} tasks  "
            f"{bar} {goal['percent']}% {status}"
        )
        console.print(
            f"  [dim]{goal['period_start']} → {goal['period_end']}[/dim]\n"
        )

    if all(goal["is_met"] for goal in goals):
        console.print("[bold green]🎉 Every goal met. Nice work![/bold green]\n")


def list_remote_goals(include_archived: bool = False) -> None:
    goals = _run(_fetch_goals(include_archived))
    console.print("\n[bold cyan]Goals[/bold cyan]\n")
    if not goals:
        console.print("[yellow]No goals configured.[/yellow]\n")
        return

    table = Table(show_header=True)
    table.add_column("ID", style="dim")
    table.add_column("Period", style="cyan")
    table.add_column("Target", justify="right")
    table.add_column("Status")
    for goal in goals:
        table.add_row(
            str(goal["id"])[:8],
            goal["period"],
            f"{goal['target_value']} tasks",
            "active" if goal["is_active"] else "archived",
        )
    console.print(table)
    console.print("\n[dim]Update with 'todopro goals set <period> <value>'[/dim]\n")


def set_remote_goal(period: str, value: int) -> None:
    """Create or update the active goal for a period."""
    if period not in ("daily", "weekly"):
        console.print(
            f"\n[red]Error: unknown period '{period}'. Use 'daily' or 'weekly'.[/red]\n"
        )
        raise SystemExit(1)

    existing = next(
        (
            goal
            for goal in _run(_fetch_goals())
            if goal["period"] == period and goal["is_active"]
        ),
        None,
    )
    if existing:
        _run(_update_goal(str(existing["id"]), value))
        console.print(f"\n[green]✓ {period.title()} goal updated to {value} tasks[/green]\n")
    else:
        _run(_create_goal(period, value))
        console.print(f"\n[green]✓ {period.title()} goal set to {value} tasks[/green]\n")


# ── achievements ─────────────────────────────────────────────────────────────


async def _fetch_achievements() -> dict:
    client = APIClient()
    return await AchievementsAPI(client).list_achievements()


def show_remote_achievements(show_all: bool = False) -> None:
    payload = _run(_fetch_achievements())
    achievements = payload.get("achievements", [])
    earned = [a for a in achievements if a["earned"]]

    if not earned and not show_all:
        console.print(
            "\n[yellow]No achievements earned yet. Complete some tasks to earn badges![/yellow]"
        )
        console.print("\n[dim]Tip: use --all to see what's available[/dim]\n")
        return

    if earned:
        console.print("\n[bold cyan]🏆 Earned Achievements[/bold cyan]\n")
        for item in earned:
            console.print(
                Panel(
                    f"[bold cyan]{item['name']}[/bold cyan]\n{item['description']}\n"
                    f"[dim]Earned {item['earned_at'][:10]} · {item['points']} pts[/dim]",
                    border_style="green",
                )
            )

    if show_all:
        locked = [a for a in achievements if not a["earned"]]
        if locked:
            console.print("\n[bold]🔒 Locked[/bold]\n")
            table = Table(show_header=True)
            table.add_column("Achievement", style="cyan")
            table.add_column("How to earn")
            table.add_column("Points", justify="right")
            for item in locked:
                table.add_row(item["name"], item["description"], str(item["points"]))
            console.print(table)

    console.print(
        f"\n[bold]{payload.get('earned_count', len(earned))}/"
        f"{payload.get('total_count', len(achievements))}[/bold] earned · "
        f"[bold]{payload.get('points', 0)}[/bold] points\n"
    )
