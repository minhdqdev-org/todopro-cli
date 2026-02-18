"""Statistics and analytics commands for focus sessions."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from todopro_cli.focus.analytics import FocusAnalytics
from todopro_cli.focus.history import HistoryLogger

console = Console()
app = typer.Typer(help="Focus mode statistics and analytics")


def format_duration(minutes: float) -> str:
    """Format minutes as hours and minutes."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def render_progress_bar(value: float, max_value: float, width: int = 10) -> str:
    """Render a progress bar using block characters."""
    if max_value == 0:
        ratio = 0
    else:
        ratio = min(value / max_value, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


@app.command("today")
@app.command()
def show_today(
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show today's focus summary (default command)."""
    analytics = FocusAnalytics()
    summary = analytics.get_daily_summary()

    if output == "json":
        console.print_json(data=summary)
        return

    # Format date
    date_str = datetime.fromisoformat(summary["date"]).strftime("%B %d, %Y")

    # Build display
    console.print(f"\n[bold cyan]🍅 Focus Summary - {date_str}[/bold cyan]\n")

    # Overview metrics
    console.print(
        f"Sessions Completed: [bold]{summary['completed_sessions']}[/bold] pomodoros"
    )
    console.print(
        f"Total Focus Time: [bold]{format_duration(summary['total_focus_minutes'])}[/bold]"
    )
    console.print(f"Break Time: {format_duration(summary['break_minutes'])}")

    if summary["most_focused_context"]:
        console.print(
            f"Most Focused Project: [bold]{summary['most_focused_context']}[/bold] ({summary['most_focused_sessions']} sessions)"
        )

    console.print(
        f"Tasks Completed: [bold]{summary['tasks_completed']}[/bold]/{summary['total_sessions']}"
    )

    # Session breakdown
    if summary["sessions"]:
        console.print("\n[bold]Session Breakdown:[/bold]")
        for session in summary["sessions"]:
            start_time = datetime.fromisoformat(
                session["start_time"].replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(
                session["end_time"].replace("Z", "+00:00")
            )

            time_range = (
                f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            )
            title = session["task_title"] or "Unknown Task"

            # Status indicator
            if session["status"] == "completed":
                if session["completed_task"]:
                    status = "[green]✓[/green]"
                    color = "green"
                else:
                    status = "[yellow]○[/yellow]"
                    color = "yellow"
            elif session["status"] == "cancelled":
                status = "[red]✗[/red]"
                color = "red"
            else:
                status = "[dim]?[/dim]"
                color = "dim"

            bar = "▓" * 5
            console.print(f"  {bar} {time_range}  {title} {status}")

    console.print()


@app.command("week")
def show_week(
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show weekly focus report (last 7 days)."""
    analytics = FocusAnalytics()
    summary = analytics.get_weekly_summary()

    if output == "json":
        console.print_json(data=summary)
        return

    # Format date range
    start_date = datetime.fromisoformat(summary["start_date"])
    end_date = datetime.fromisoformat(summary["end_date"])
    date_range = f"{start_date.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"

    console.print(f"\n[bold cyan]🍅 Weekly Focus Report ({date_range})[/bold cyan]\n")

    # Daily breakdown
    console.print("[bold]Daily Breakdown:[/bold]")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    max_sessions = max(
        (d["total_sessions"] for d in summary["daily_summaries"]), default=1
    )

    for i, daily in enumerate(summary["daily_summaries"]):
        date = datetime.fromisoformat(daily["date"])
        day_name = days[date.weekday()]
        bar = render_progress_bar(daily["total_sessions"], max_sessions, width=10)

        console.print(
            f"  {day_name} ({date.strftime('%b %d')}):  {bar} "
            f"{daily['total_sessions']} sessions  ({format_duration(daily['total_focus_minutes'])})"
        )

    # Weekly totals
    console.print(
        f"\nTotal: [bold]{summary['total_sessions']}[/bold] sessions ([bold]{format_duration(summary['total_focus_minutes'])}[/bold])"
    )
    console.print(
        f"Daily Average: {summary['daily_average_sessions']} sessions ({format_duration(summary['daily_average_minutes'])})"
    )
    console.print(
        f"Most Productive Day: {summary['most_productive_day']['date']} ({summary['most_productive_day']['sessions']} sessions)"
    )

    # Peak hours
    if summary["peak_hours"]:
        console.print("\nPeak Focus Hours:", end="")
        for peak in summary["peak_hours"]:
            hour = peak["hour"]
            console.print(f" {hour:02d}:00-{hour + 1:02d}:00", end="")
        console.print()

    # Project distribution
    if summary["context_distribution"]:
        console.print("\n[bold]Project Distribution:[/bold]")
        max_minutes = max(
            (c["minutes"] for c in summary["context_distribution"]), default=1
        )

        for ctx_data in summary["context_distribution"][:5]:  # Top 5
            bar = render_progress_bar(ctx_data["minutes"], max_minutes, width=12)
            pct = (
                (ctx_data["minutes"] / summary["total_focus_minutes"] * 100)
                if summary["total_focus_minutes"] > 0
                else 0
            )
            console.print(
                f"  {ctx_data['context']:20s} {bar} {pct:3.0f}% ({ctx_data['sessions']} sessions)"
            )

    console.print()


@app.command("month")
def show_month(
    month_str: str = typer.Argument(
        None, help="Month in YYYY-MM format (default: current month)"
    ),
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show monthly overview."""
    # Parse month
    if month_str:
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            console.print(
                "[red]Error: Month must be in YYYY-MM format (e.g., 2026-02)[/red]"
            )
            raise typer.Exit(1)
    else:
        now = datetime.now()
        year, month = now.year, now.month

    analytics = FocusAnalytics()
    summary = analytics.get_monthly_summary(year, month)

    if output == "json":
        console.print_json(data=summary)
        return

    month_name = datetime(year, month, 1).strftime("%B %Y")

    console.print(f"\n[bold cyan]🍅 Monthly Overview - {month_name}[/bold cyan]\n")

    # Main metrics
    console.print(f"Total Sessions: [bold]{summary['total_sessions']}[/bold]")
    console.print(
        f"Focus Time: [bold]{format_duration(summary['total_focus_minutes'])}[/bold]"
    )
    console.print(f"Tasks: {summary['tasks_completed']} completed")
    console.print(f"Completion Rate: {summary['completion_rate']}%")
    console.print(f"Average Session: {summary['avg_session_length']} minutes")

    # Week-by-week breakdown
    if summary["weeks"]:
        console.print("\n[bold]Week-by-Week Breakdown:[/bold]")
        for i, week in enumerate(summary["weeks"], 1):
            console.print(
                f"  Week {i} ({week['start']} to {week['end']}): {week['sessions']} sessions, {format_duration(week['focus_minutes'])}"
            )

    # Month-over-month comparison
    if summary["comparison"]:
        comp = summary["comparison"]
        console.print("\n[bold]vs Previous Month:[/bold]")

        def format_change(pct: float) -> str:
            sign = "+" if pct >= 0 else ""
            color = "green" if pct >= 0 else "red"
            return f"[{color}]{sign}{pct:.0f}%[/{color}]"

        console.print(f"  Sessions: {format_change(comp['sessions_change_pct'])}")
        console.print(f"  Focus Time: {format_change(comp['minutes_change_pct'])}")
        console.print(
            f"  Completion Rate: {format_change(comp['completion_rate_change_pct'])}"
        )

    console.print()


@app.command("streak")
def show_streak(
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show focus streak information."""
    analytics = FocusAnalytics()
    streak = analytics.get_current_streak()

    if output == "json":
        console.print_json(data=streak)
        return

    current = streak["current_streak"]
    longest = streak["longest_streak"]

    # Streak emoji
    if current >= 30:
        emoji = "🏆"
    elif current >= 14:
        emoji = "🔥🔥🔥"
    elif current >= 7:
        emoji = "🔥🔥"
    elif current >= 3:
        emoji = "🔥"
    else:
        emoji = ""

    console.print(f"\n{emoji} [bold cyan]Current Streak: {current} days[/bold cyan]")

    if longest > 0:
        console.print(f"   Longest Streak: {longest} days", end="")
        if streak["longest_streak_start"] and streak["longest_streak_end"]:
            start_date = datetime.fromisoformat(
                streak["longest_streak_start"]
            ).strftime("%b %d")
            end_date = datetime.fromisoformat(streak["longest_streak_end"]).strftime(
                "%b %d, %Y"
            )
            console.print(f" ({start_date}-{end_date})")
        else:
            console.print()

    if current > 0:
        console.print(f"\n   Keep it going! Focus today to reach {current + 1} days.")
    else:
        console.print("\n   Start a new streak today!")

    console.print()


@app.command("score")
def show_score(
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show productivity score."""
    analytics = FocusAnalytics()
    score_data = analytics.get_productivity_score()

    if output == "json":
        console.print_json(data=score_data)
        return

    score = score_data["score"]
    grade = score_data["grade"]
    components = score_data["components"]

    console.print(
        f"\n[bold cyan]Productivity Score: {score}/100 ({grade})[/bold cyan]\n"
    )

    # Component breakdown
    for name, data in components.items():
        bar = render_progress_bar(
            data["score"], 25 if name != "completion" else 100, width=10
        )
        console.print(f"  {name.capitalize():15s} {data['value']}/{data['max']}  {bar}")

    # Motivation message
    if score >= 90:
        msg = "Outstanding! You're in the top 10% this week. 🎉"
    elif score >= 80:
        msg = "Great work! Keep up the momentum."
    elif score >= 70:
        msg = "Good progress. Room for improvement."
    elif score >= 60:
        msg = "You're on track. Try to focus more consistently."
    else:
        msg = "Time to build better focus habits!"

    console.print(f"\n{msg}\n")


@app.command("project")
def show_project(
    context: str = typer.Argument(..., help="Project/context name"),
    days: int = typer.Option(30, "--days", help="Number of days to analyze"),
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show statistics for a specific project."""
    analytics = FocusAnalytics()
    stats = analytics.get_project_stats(context, days)

    if output == "json":
        console.print_json(data=stats)
        return

    console.print(f"\n[bold cyan]🍅 Project: {context}[/bold cyan]\n")

    console.print(f"[bold]Overview (Last {days} days):[/bold]")
    console.print(f"  Total Sessions: {stats['total_sessions']}")
    console.print(f"  Focus Time: {format_duration(stats['total_focus_minutes'])}")
    console.print(
        f"  Tasks: {stats['tasks_completed']} completed, {stats['tasks_in_progress']} in progress"
    )
    console.print(f"  Avg Session: {stats['avg_session_minutes']} minutes")

    # Top tasks
    if stats["top_tasks"]:
        console.print("\n[bold]Top Tasks (by focus time):[/bold]")
        max_minutes = max((t["minutes"] for t in stats["top_tasks"]), default=1)

        for i, task in enumerate(stats["top_tasks"], 1):
            bar = render_progress_bar(task["minutes"], max_minutes, width=8)
            console.print(
                f"  {i}. {task['title']:40s} {format_duration(task['minutes']):>8s}  {bar}"
            )

    console.print()


@app.command("heatmap")
def show_heatmap(
    days: int = typer.Option(30, "--days", help="Number of days to analyze"),
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show time-of-day focus heatmap."""
    analytics = FocusAnalytics()
    heatmap_data = analytics.get_heatmap_data(days)

    if output == "json":
        console.print_json(data=heatmap_data)
        return

    console.print(f"\n[bold cyan]Focus Heatmap (Last {days} days)[/bold cyan]\n")

    heatmap = heatmap_data["heatmap"]
    days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Find max value for scaling
    max_sessions = 1
    for day_data in heatmap.values():
        max_sessions = max(max_sessions, max(day_data.values(), default=1))

    # Print header
    console.print("       ", end="")
    for day in days_labels:
        console.print(f" {day:3s}", end="")
    console.print()

    # Print hours
    for hour in range(6, 23):  # 6 AM to 10 PM
        console.print(f"{hour:02d}:00 ", end="")
        for day in range(7):
            sessions = heatmap.get(day, {}).get(hour, 0)

            # Determine shading
            if sessions == 0:
                char = "░"
            elif sessions >= max_sessions * 0.75:
                char = "▓▓▓"
            elif sessions >= max_sessions * 0.5:
                char = "▓▓ "
            elif sessions >= max_sessions * 0.25:
                char = "▓  "
            else:
                char = "░  "

            console.print(f" {char}", end="")
        console.print()

    # Peak times
    if heatmap_data["peak_times"]:
        console.print("\n[bold]Peak Focus Times:[/bold]")
        for peak in heatmap_data["peak_times"][:3]:
            day_name = days_labels[peak["day"]]
            hour = peak["hour"]
            console.print(
                f"  {day_name}, {hour:02d}:00-{hour + 1:02d}:00 ({peak['sessions']} sessions)"
            )

    console.print()


@app.command("export")
def export_data(
    format: str = typer.Option("json", "--format", help="Export format (csv, json)"),
    output: Path = typer.Option(None, "--output", help="Output file (default: stdout)"),
    from_date: str = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: str = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    context: str = typer.Option(None, "--context", help="Filter by context/project"),
    completed_only: bool = typer.Option(
        False, "--completed-only", help="Export only completed sessions"
    ),
):
    """Export focus session data."""
    # Query sessions
    logger = HistoryLogger()

    sql = "SELECT * FROM pomodoro_sessions WHERE 1=1"
    params = []

    if from_date:
        sql += " AND start_time >= ?"
        params.append(from_date)

    if to_date:
        sql += " AND start_time < ?"
        params.append(to_date)

    if context:
        sql += " AND context = ?"
        params.append(context)

    if completed_only:
        sql += " AND status = 'completed'"

    sql += " ORDER BY start_time"

    # Execute query
    import sqlite3

    with sqlite3.connect(logger.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        sessions = [dict(row) for row in cursor.fetchall()]

    # Export
    if format == "csv":
        output_file = output or sys.stdout

        if output:
            f = open(output, "w", newline="")
        else:
            f = sys.stdout

        try:
            fieldnames = [
                "id",
                "task_id",
                "task_title",
                "start_time",
                "end_time",
                "duration_minutes",
                "actual_focus_minutes",
                "completed_task",
                "status",
                "session_type",
                "context",
                "created_at",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sessions)
        finally:
            if output:
                f.close()
                console.print(
                    f"[green]Exported {len(sessions)} sessions to {output}[/green]"
                )

    elif format == "json":
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_sessions": len(sessions),
            "sessions": sessions,
        }

        if output:
            with open(output, "w") as f:
                json.dump(export_data, f, indent=2)
            console.print(
                f"[green]Exported {len(sessions)} sessions to {output}[/green]"
            )
        else:
            console.print_json(data=export_data)

    else:
        console.print(f"[red]Unsupported format: {format}[/red]")
        raise typer.Exit(1)


@app.command("quality")
def show_quality(
    days: int = typer.Option(7, "--days", help="Number of days to analyze"),
    output: str = typer.Option(None, "--output", "-o", help="Output format (json)"),
):
    """Show focus quality metrics."""
    analytics = FocusAnalytics()

    # Get sessions for analysis
    logger = HistoryLogger()
    from_date = (
        datetime.now() - __import__("datetime").timedelta(days=days)
    ).isoformat()

    import sqlite3

    conn = sqlite3.connect(logger.db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            COUNT(*) as total_sessions,
            AVG(duration_minutes) as avg_duration,
            AVG(actual_focus_minutes) as avg_focus,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'interrupted' THEN 1 ELSE 0 END) as interrupted,
            AVG(actual_focus_minutes * 100.0 / duration_minutes) as focus_efficiency
        FROM pomodoro_sessions
        WHERE start_time >= ?
    """,
        (from_date,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row or row[0] == 0:
        console.print("[yellow]No sessions found in the specified period[/yellow]")
        return

    total, avg_dur, avg_focus, completed, interrupted, efficiency = row

    metrics = {
        "period_days": days,
        "total_sessions": total,
        "completed_sessions": completed,
        "interrupted_sessions": interrupted,
        "avg_duration_minutes": round(avg_dur, 1) if avg_dur else 0,
        "avg_focus_minutes": round(avg_focus, 1) if avg_focus else 0,
        "focus_efficiency_pct": round(efficiency, 1) if efficiency else 0,
        "completion_rate_pct": round(completed / total * 100, 1) if total > 0 else 0,
        "interruption_rate_pct": round(interrupted / total * 100, 1)
        if total > 0
        else 0,
    }

    if output == "json":
        console.print_json(data=metrics)
        return

    console.print(
        f"\n[bold cyan]📊 Focus Quality Metrics[/bold cyan] (Last {days} days)\n"
    )

    # Overall stats
    console.print("[bold]Session Overview[/bold]")
    console.print(f"  Total Sessions:     {total}")
    console.print(
        f"  Completed:          {completed} ({metrics['completion_rate_pct']}%)"
    )
    console.print(
        f"  Interrupted:        {interrupted} ({metrics['interruption_rate_pct']}%)"
    )

    # Quality metrics
    console.print("\n[bold]Quality Indicators[/bold]")

    # Focus Efficiency
    efficiency_bar = render_progress_bar(metrics["focus_efficiency_pct"], 100, width=20)
    efficiency_color = (
        "green" if efficiency >= 80 else "yellow" if efficiency >= 60 else "red"
    )
    console.print(
        f"  Focus Efficiency:   [{efficiency_color}]{efficiency_bar} {metrics['focus_efficiency_pct']}%[/{efficiency_color}]"
    )

    # Completion Rate
    completion_bar = render_progress_bar(metrics["completion_rate_pct"], 100, width=20)
    completion_color = (
        "green"
        if metrics["completion_rate_pct"] >= 80
        else "yellow"
        if metrics["completion_rate_pct"] >= 60
        else "red"
    )
    console.print(
        f"  Completion Rate:    [{completion_color}]{completion_bar} {metrics['completion_rate_pct']}%[/{completion_color}]"
    )

    # Average duration
    avg_dur_str = format_duration(metrics["avg_duration_minutes"])
    avg_focus_str = format_duration(metrics["avg_focus_minutes"])
    console.print("\n[bold]Session Length[/bold]")
    console.print(f"  Avg Planned:        {avg_dur_str}")
    console.print(f"  Avg Actual Focus:   {avg_focus_str}")

    # Quality assessment
    console.print("\n[bold]Assessment[/bold]")
    if efficiency >= 90 and metrics["completion_rate_pct"] >= 90:
        console.print("  [green]✨ Excellent focus quality! Keep it up![/green]")
    elif efficiency >= 75 and metrics["completion_rate_pct"] >= 75:
        console.print("  [cyan]👍 Good focus quality. Room for improvement.[/cyan]")
    elif efficiency >= 60 and metrics["completion_rate_pct"] >= 60:
        console.print(
            "  [yellow]⚠️  Fair focus quality. Consider reducing distractions.[/yellow]"
        )
    else:
        console.print(
            "  [red]📉 Focus quality needs attention. Try shorter sessions or minimize interruptions.[/red]"
        )

    console.print()
