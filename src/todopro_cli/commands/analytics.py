"""Analytics commands for TodoPro CLI.

Analytics commands to view productivity stats from terminal.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from todopro_cli.api.analytics import AnalyticsAPI
from todopro_cli.api.client import get_client
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Analytics commands")
console = Console()


def check_auth(profile: str = "default") -> None:
    """Check if user is authenticated."""
    config_manager = get_config_manager(profile)
    credentials = config_manager.load_credentials()
    if not credentials:
        format_error("Not logged in. Use 'todopro login' to authenticate.")
        raise typer.Exit(1)


@app.command("stats")
def analytics_stats(
    output: str = typer.Option("table", "--output", help="Output format (table/json)"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show productivity score and basic statistics."""
    check_auth(profile)

    try:

        async def do_stats() -> None:
            client = get_client(profile)
            analytics_api = AnalyticsAPI(client)

            try:
                # Fetch productivity score and completion stats
                score_data = await analytics_api.get_productivity_score()
                stats_data = await analytics_api.get_completion_stats()

                if output == "json":
                    import json

                    combined = {
                        "productivity_score": score_data,
                        "completion_stats": stats_data,
                    }
                    print(json.dumps(combined, indent=2, default=str))
                else:
                    # Display productivity score
                    score = score_data.get("score", 0)
                    trend = score_data.get("trend", 0)
                    breakdown = score_data.get("breakdown", {})

                    console.print("\n[bold cyan]Productivity Score[/bold cyan]")
                    score_table = Table(show_header=False, box=None)
                    score_table.add_column("Field", style="cyan")
                    score_table.add_column("Value", style="bold white")

                    # Format score with color based on value
                    score_color = "red"
                    if score >= 80:
                        score_color = "green"
                    elif score >= 60:
                        score_color = "blue"
                    elif score >= 40:
                        score_color = "yellow"

                    score_table.add_row(
                        "Score", f"[{score_color}]{score:.1f}/100[/{score_color}]"
                    )

                    # Format trend
                    trend_str = f"+{trend:.1f}%" if trend > 0 else f"{trend:.1f}%"
                    trend_color = (
                        "green" if trend > 0 else "red" if trend < 0 else "white"
                    )
                    score_table.add_row(
                        "Trend", f"[{trend_color}]{trend_str}[/{trend_color}]"
                    )

                    console.print(score_table)

                    # Display breakdown
                    console.print("\n[bold cyan]Score Breakdown[/bold cyan]")
                    breakdown_table = Table(show_header=True, box=None)
                    breakdown_table.add_column("Component", style="cyan")
                    breakdown_table.add_column("Weight", style="dim")
                    breakdown_table.add_column("Score", style="bold white")

                    breakdown_table.add_row(
                        "Completion Count",
                        "40%",
                        f"{breakdown.get('completion_count', 0):.1f}",
                    )
                    breakdown_table.add_row(
                        "Completion Rate",
                        "30%",
                        f"{breakdown.get('completion_rate', 0):.1f}",
                    )
                    breakdown_table.add_row(
                        "On-Time Rate", "30%", f"{breakdown.get('on_time_rate', 0):.1f}"
                    )

                    console.print(breakdown_table)

                    # Display completion stats
                    console.print("\n[bold cyan]Completion Statistics[/bold cyan]")
                    stats_table = Table(show_header=False, box=None)
                    stats_table.add_column("Metric", style="cyan")
                    stats_table.add_column("Value", style="bold white")

                    stats_table.add_row(
                        "Total Completed", str(stats_data.get("total_completed", 0))
                    )
                    stats_table.add_row(
                        "Completion Rate",
                        f"{stats_data.get('completion_rate', 0):.1f}%",
                    )
                    stats_table.add_row(
                        "On-Time Rate", f"{stats_data.get('on_time_rate', 0):.1f}%"
                    )
                    stats_table.add_row(
                        "Avg Completion Time",
                        f"{stats_data.get('avg_completion_time_hours', 0):.1f}h",
                    )

                    console.print(stats_table)
                    console.print()

            finally:
                await client.close()

        asyncio.run(do_stats())

    except Exception as e:
        format_error(f"Failed to fetch analytics: {str(e)}")
        raise typer.Exit(1) from e


@app.command("streaks")
def analytics_streaks(
    output: str = typer.Option("table", "--output", help="Output format (table/json)"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show current and longest task completion streak."""
    check_auth(profile)

    try:

        async def do_streaks() -> None:
            client = get_client(profile)
            analytics_api = AnalyticsAPI(client)

            try:
                streaks_data = await analytics_api.get_streaks()

                if output == "json":
                    import json

                    print(json.dumps(streaks_data, indent=2, default=str))
                else:
                    current_streak = streaks_data.get("current_streak", 0)
                    longest_streak = streaks_data.get("longest_streak", 0)

                    console.print("\n[bold cyan]Task Completion Streaks[/bold cyan]")
                    streak_table = Table(show_header=False, box=None)
                    streak_table.add_column("Type", style="cyan")
                    streak_table.add_column("Days", style="bold white")

                    # Color code based on streak length
                    current_color = (
                        "green"
                        if current_streak >= 7
                        else "yellow"
                        if current_streak >= 3
                        else "white"
                    )
                    longest_color = (
                        "green"
                        if longest_streak >= 30
                        else "blue"
                        if longest_streak >= 7
                        else "white"
                    )

                    streak_table.add_row(
                        "Current Streak",
                        f"[{current_color}]{current_streak} days[/{current_color}]",
                    )
                    streak_table.add_row(
                        "Longest Streak",
                        f"[{longest_color}]{longest_streak} days[/{longest_color}]",
                    )

                    console.print(streak_table)
                    console.print()

                    # Show motivation message
                    if current_streak >= longest_streak and current_streak > 0:
                        console.print(
                            "[bold green]🔥 You're on your best streak ever![/bold green]"
                        )
                    elif current_streak >= 7:
                        console.print(
                            "[green]✨ Great consistency! Keep it up![/green]"
                        )
                    elif current_streak >= 3:
                        console.print("[yellow]💪 Building momentum![/yellow]")

            finally:
                await client.close()

        asyncio.run(do_streaks())

    except Exception as e:
        format_error(f"Failed to fetch streaks: {str(e)}")
        raise typer.Exit(1) from e


@app.command("export")
def analytics_export(
    format: str = typer.Option("csv", "--format", help="Export format (csv/json)"),
    output: str | None = typer.Option(None, "--output", help="Output file path"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Export analytics data to file."""
    check_auth(profile)

    # Validate format
    if format not in ("csv", "json"):
        format_error("Invalid format. Use 'csv' or 'json'")
        raise typer.Exit(1)

    # Determine output filename
    if output is None:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"todopro_analytics_{timestamp}.{format}"

    try:

        async def do_export() -> None:
            client = get_client(profile)
            analytics_api = AnalyticsAPI(client)

            try:
                console.print(
                    f"[cyan]Exporting analytics data as {format.upper()}...[/cyan]"
                )

                # Fetch export data
                data = await analytics_api.export_data(format=format)

                # Write to file
                output_path = Path(output)
                output_path.write_bytes(data)

                format_success(f"Analytics data exported to: {output_path.absolute()}")

            finally:
                await client.close()

        asyncio.run(do_export())

    except Exception as e:
        format_error(f"Failed to export analytics: {str(e)}")
        raise typer.Exit(1) from e
