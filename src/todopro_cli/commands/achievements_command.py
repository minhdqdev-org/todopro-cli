"""Achievements and gamification commands."""

import typer
from rich.panel import Panel

from todopro_cli.focus.achievements import ACHIEVEMENTS, AchievementTracker
from todopro_cli.utils.ui.console import get_console

console = get_console()
app = typer.Typer(help="Focus achievements and gamification")


def render_progress_bar(value: float, max_value: float, width: int = 20) -> str:
    """Render a progress bar using block characters."""
    ratio = 0 if max_value == 0 else min(value / max_value, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


@app.command()
@app.command("list")
def list_achievements(
    show_all: bool = typer.Option(
        False, "--all", help="Show all achievements including unearned"
    ),
):
    """Show earned achievements and badges."""
    tracker = AchievementTracker()

    # Check for new achievements
    newly_earned = tracker.check_achievements()

    # Show celebration for newly earned
    if newly_earned:
        console.print()
        for achievement in newly_earned:
            panel = Panel(
                f"[bold cyan]{achievement.icon} {achievement.name}[/bold cyan]\n{achievement.description}",
                title="[bold green]🎉 Achievement Unlocked! 🎉[/bold green]",
                border_style="green",
            )
            console.print(panel)
        console.print()

    # Get earned achievements
    earned = tracker.get_earned_achievements()

    if not earned and not show_all:
        console.print(
            "[yellow]No achievements earned yet. Start focusing to earn badges![/yellow]"
        )
        console.print("\nTip: Use [cyan]--all[/cyan] to see available achievements")
        return

    # Show earned achievements
    if earned:
        console.print("\n[bold cyan]🏆 Earned Achievements[/bold cyan]\n")

        # Group by category
        categories = {"Streaks": [], "Milestones": [], "Quality": [], "Special": []}

        for achievement in earned:
            req_type = achievement.requirement["type"]
            if "streak" in req_type:
                categories["Streaks"].append(achievement)
            elif req_type in ["total_sessions", "total_hours"]:
                categories["Milestones"].append(achievement)
            elif req_type in ["perfect_sessions", "high_efficiency"]:
                categories["Quality"].append(achievement)
            else:
                categories["Special"].append(achievement)

        for category, achievements in categories.items():
            if not achievements:
                continue

            console.print(f"[bold]{category}[/bold]")
            for achievement in achievements:
                console.print(
                    f"  {achievement.icon} {achievement.name} - {achievement.description}"
                )
            console.print()

    # Show available achievements if requested
    if show_all:
        progress = tracker.get_progress()

        if progress:
            console.print("\n[bold cyan]📋 Available Achievements[/bold cyan]\n")

            for _, data in sorted(
                progress.items(), key=lambda x: x[1]["percentage"], reverse=True
            ):
                achievement = data["achievement"]
                current = data["current"]
                required = data["required"]
                percentage = data["percentage"]

                bar = render_progress_bar(current, required)

                # Format current value based on type
                if achievement.requirement["type"] in ["total_hours", "daily_hours"]:
                    current_str = f"{current:.1f}h"
                    required_str = f"{required}h"
                elif isinstance(current, bool):
                    current_str = "✓" if current else "✗"
                    required_str = "✓"
                else:
                    current_str = str(int(current))
                    required_str = str(required)

                console.print(f"  {achievement.icon} [bold]{achievement.name}[/bold]")
                console.print(f"     {achievement.description}")
                console.print(
                    f"     {bar} {current_str}/{required_str} ({percentage:.0f}%)"
                )
                console.print()


@app.command("check")
def check_new_achievements():
    """Check for newly earned achievements."""
    tracker = AchievementTracker()
    newly_earned = tracker.check_achievements()

    if newly_earned:
        console.print()
        for achievement in newly_earned:
            panel = Panel(
                f"[bold cyan]{achievement.icon} {achievement.name}[/bold cyan]\n{achievement.description}",
                title="[bold green]🎉 Achievement Unlocked! 🎉[/bold green]",
                border_style="green",
            )
            console.print(panel)
        console.print()
        console.print(
            f"[green]✓ Unlocked {len(newly_earned)} new achievement(s)![/green]"
        )
    else:
        console.print(
            "[yellow]No new achievements at this time. Keep focusing![/yellow]"
        )


@app.command("stats")
def achievement_stats():
    """Show achievement statistics and progress."""
    tracker = AchievementTracker()

    earned = tracker.get_earned_achievements()
    total = len(ACHIEVEMENTS)
    percentage = (len(earned) / total * 100) if total > 0 else 0

    console.print("\n[bold cyan]🎮 Achievement Statistics[/bold cyan]\n")

    # Overall progress
    bar = render_progress_bar(len(earned), total, width=30)
    console.print(f"Overall Progress: {bar} {len(earned)}/{total} ({percentage:.1f}%)")
    console.print()

    # Category breakdown
    categories = {"Streaks": 0, "Milestones": 0, "Quality": 0, "Special": 0}

    for achievement in earned:
        req_type = achievement.requirement["type"]
        if "streak" in req_type:
            categories["Streaks"] += 1
        elif req_type in ["total_sessions", "total_hours"]:
            categories["Milestones"] += 1
        elif req_type in ["perfect_sessions", "high_efficiency"]:
            categories["Quality"] += 1
        else:
            categories["Special"] += 1

    console.print("[bold]By Category:[/bold]")
    for category, count in categories.items():
        # Count total in category
        total_in_cat = sum(
            1
            for a in ACHIEVEMENTS
            if ("streak" in a.requirement["type"] and category == "Streaks")
            or (
                a.requirement["type"] in ["total_sessions", "total_hours"]
                and category == "Milestones"
            )
            or (
                a.requirement["type"] in ["perfect_sessions", "high_efficiency"]
                and category == "Quality"
            )
            or (
                a.requirement["type"]
                not in [
                    "streak",
                    "total_sessions",
                    "total_hours",
                    "perfect_sessions",
                    "high_efficiency",
                ]
                and category == "Special"
            )
        )

        cat_bar = render_progress_bar(count, total_in_cat, width=15)
        console.print(f"  {category:12s} {cat_bar} {count}/{total_in_cat}")

    console.print()

    # Next achievements
    progress = tracker.get_progress()
    closest = sorted(progress.items(), key=lambda x: x[1]["percentage"], reverse=True)[
        :3
    ]

    if closest:
        console.print("[bold]Closest Achievements:[/bold]")
        for _, data in closest:
            achievement = data["achievement"]
            percentage = data["percentage"]
            console.print(
                f"  {achievement.icon} {achievement.name} - {percentage:.0f}% complete"
            )

    console.print()
