"""Pomodoro timer commands for TodoPro CLI."""

import click
import time
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from todopro_cli.api.client import APIClient
from todopro_cli.commands.utils import handle_api_error

console = Console()


@click.group()
def timer():
    """Pomodoro timer for focus sessions."""
    pass


@timer.command("start")
@click.option("--task-id", help="Task ID to track time for")
@click.option("--duration", default=25, type=int, help="Session duration in minutes")
@click.option("--type", type=click.Choice(['work', 'short_break', 'long_break']), default='work')
def start_timer(task_id, duration, type):
    """Start a Pomodoro timer session."""
    client = APIClient()
    
    try:
        # Start session on server
        data = {
            "session_type": type,
            "duration": duration
        }
        if task_id:
            data["task_id"] = task_id
        
        session = client.post("/v1/pomodoro/start", data)
        session_id = session['id']
        
        # Display session info
        console.print(f"\n[bold green]Starting {type.replace('_', ' ').title()} Session[/bold green]")
        console.print(f"Duration: {duration} minutes")
        if task_id:
            console.print(f"Task: {session.get('task_content', task_id)}")
        console.print()
        
        # Countdown timer
        total_seconds = duration * 60
        start_time = time.time()
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Timer running...", total=total_seconds)
                
                while time.time() - start_time < total_seconds:
                    elapsed = int(time.time() - start_time)
                    remaining = total_seconds - elapsed
                    
                    mins = remaining // 60
                    secs = remaining % 60
                    progress.update(task, description=f"⏱️  {mins:02d}:{secs:02d} remaining")
                    
                    time.sleep(1)
                
                # Session complete
                console.print("\n[bold green]🎉 Session Complete![/bold green]")
                
                # Mark as complete on server
                client.post(f"/v1/pomodoro/{session_id}/complete", {})
                console.print("[dim]Session saved successfully[/dim]\n")
                
        except KeyboardInterrupt:
            # Session interrupted
            console.print("\n[yellow]⚠️  Session Interrupted[/yellow]")
            client.post(f"/v1/pomodoro/{session_id}/interrupt", {
                "notes": "Interrupted by user"
            })
            console.print("[dim]Session marked as interrupted[/dim]\n")
            
    except Exception as e:
        handle_api_error(e, "starting timer")


@timer.command("history")
@click.option("--task-id", help="Filter by task ID")
@click.option("--limit", default=20, type=int, help="Number of sessions to show")
def timer_history(task_id, limit):
    """Show Pomodoro session history."""
    client = APIClient()
    
    try:
        params = {"limit": limit}
        if task_id:
            params["task_id"] = task_id
        
        result = client.get("/v1/pomodoro/history", params=params)
        sessions = result.get('sessions', [])
        
        if not sessions:
            console.print("[yellow]No timer sessions found[/yellow]")
            return
        
        # Display table
        table = Table(title=f"Recent Timer Sessions ({len(sessions)})", show_header=True)
        table.add_column("Date", style="cyan")
        table.add_column("Type")
        table.add_column("Task")
        table.add_column("Duration", justify="right")
        table.add_column("Status", justify="center")
        
        for session in sessions:
            started = datetime.fromisoformat(session['started_at'].replace('Z', '+00:00'))
            date_str = started.strftime("%Y-%m-%d %H:%M")
            
            session_type = session['session_type'].replace('_', ' ').title()
            task = session.get('task_content', '—')[:30]
            duration = f"{session['actual_duration_minutes']}m"
            
            if session['is_completed']:
                status = "✓"
                status_color = "green"
            elif session['is_interrupted']:
                status = "✗"
                status_color = "yellow"
            else:
                status = "○"
                status_color = "dim"
            
            table.add_row(
                date_str,
                session_type,
                task,
                duration,
                f"[{status_color}]{status}[/{status_color}]"
            )
        
        console.print(table)
        
    except Exception as e:
        handle_api_error(e, "fetching timer history")


@timer.command("stats")
@click.option("--task-id", help="Filter by task ID")
@click.option("--days", default=7, type=int, help="Number of days to analyze")
def timer_stats(task_id, days):
    """Show Pomodoro statistics."""
    client = APIClient()
    
    try:
        params = {"days": days}
        if task_id:
            params["task_id"] = task_id
        
        stats = client.get("/v1/pomodoro/stats", params=params)
        
        console.print(f"\n[bold]Pomodoro Statistics (Last {days} days)[/bold]\n")
        
        console.print(f"Total Sessions: {stats['total_sessions']}")
        console.print(f"  Completed: [green]{stats['completed_sessions']}[/green]")
        console.print(f"  Interrupted: [yellow]{stats['interrupted_sessions']}[/yellow]")
        console.print(f"  Completion Rate: {stats['completion_rate']}%")
        console.print()
        console.print(f"Total Focus Time: {stats['total_work_hours']} hours")
        console.print(f"  ({stats['total_work_minutes']} minutes)")
        console.print()
        
    except Exception as e:
        handle_api_error(e, "fetching timer stats")


@timer.command("quick")
@click.argument("minutes", type=int, default=25)
def quick_timer(minutes):
    """Quick countdown timer (no server tracking)."""
    console.print(f"\n[bold]⏱️  {minutes}-minute timer started[/bold]\n")
    
    total_seconds = minutes * 60
    start_time = time.time()
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Focus time...", total=total_seconds)
            
            while time.time() - start_time < total_seconds:
                elapsed = int(time.time() - start_time)
                remaining = total_seconds - elapsed
                
                mins = remaining // 60
                secs = remaining % 60
                progress.update(task, description=f"⏱️  {mins:02d}:{secs:02d} remaining")
                
                time.sleep(1)
            
            console.print("\n[bold green]🎉 Time's up![/bold green]\n")
            
            # Beep (if terminal supports it)
            console.bell()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Timer stopped[/yellow]\n")
