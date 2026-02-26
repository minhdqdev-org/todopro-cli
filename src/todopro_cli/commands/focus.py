"""Focus mode commands with fullscreen Pomodoro timer.

REFACTORED: Uses Strategy Pattern with TaskService instead of direct API calls.
This version follows the architecture defined in docs/IMPROVE_ARCHITECTURE.md
"""

import asyncio
import uuid
from datetime import datetime, timedelta

import typer
from rich.prompt import Confirm, Prompt

# Import focus mode modules
from todopro_cli.models.focus.cycling import CycleState, PomodoroConfig
from todopro_cli.models.focus.history import HistoryLogger
from todopro_cli.models.focus.state import SessionState, SessionStateManager
from todopro_cli.models.focus.suggestions import TaskSuggestionEngine
from todopro_cli.models.focus.templates import TemplateManager
from todopro_cli.models.focus.ui import (
    TimerDisplay,
    show_completion_message,
    show_stopped_message,
)
from todopro_cli.services.config_service import (
    get_config_service,
    get_storage_strategy_context,
)

# Import strategy context and service layer
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.ui.console import get_console

console = get_console()
app = typer.Typer(help="Focus mode with Pomodoro timer")


def run_async(coro):
    """Helper to run async coroutines in sync Typer commands."""
    return asyncio.run(coro)


def get_task_service() -> TaskService:
    """
    Get TaskService instance with the correct repository strategy.

    This is the Strategy Pattern in action:
    - Context Manager reads active context configuration
    - Bootstrap creates appropriate strategy (Local or Remote)
    - TaskService is injected with the correct repository
    - Service code doesn't know which backend it's using

    Returns:
        TaskService: Service with injected repository strategy
    """
    return TaskService(get_storage_strategy_context().task_repository)


def _get_template_manager() -> TemplateManager:
    """Create a TemplateManager with injected config dependencies."""
    svc = get_config_service()
    return TemplateManager(config=svc.load_config(), save_config=svc.save_config)


def _get_suggestion_engine() -> TaskSuggestionEngine:
    """Create a TaskSuggestionEngine with injected config."""
    svc = get_config_service()
    return TaskSuggestionEngine(config=svc.load_config())


@app.command("start")
def start_focus(
    task_id: str = typer.Argument(..., help="Task ID to focus on"),
    duration: int = typer.Option(25, "--duration", "-d", help="Duration in minutes"),
    template: str = typer.Option(
        None,
        "--template",
        "-t",
        help="Use a template (deep_work, standard, quick_task)",
    ),
):
    """Start a focus session on a task."""
    # Apply template if specified
    if template:
        tm = _get_template_manager()
        template_data = tm.get_template(template)
        if template_data:
            duration = template_data["duration"]
            console.print(f"[dim]Using template: {template} ({duration} minutes)[/dim]")
        else:
            console.print(
                f"[yellow]Template '{template}' not found, using default duration[/yellow]"
            )

    state_manager = SessionStateManager()

    # Check for existing session
    existing = state_manager.load()
    if existing and existing.status in ("active", "paused"):
        console.print("[red]Error: Another focus session is already active[/red]")
        console.print(f"Task: {existing.task_title} (#{existing.task_id[:8]})")
        console.print(f"Status: {existing.status}")
        console.print(
            "\nUse 'todopro focus resume' to continue or 'todopro focus stop' to cancel it."
        )
        raise typer.Exit(1)

    # Fetch task details using TaskService instead of direct API call
    task_service = get_task_service()

    try:
        # Use service layer - works with both SQLite and REST API
        task = run_async(task_service.get_task(task_id))
        task_title = task.content  # Task model uses 'content' field
    except Exception as e:
        console.print(f"[red]Error fetching task: {e}[/red]")
        raise typer.Exit(1) from e

    # Get current context
    config_service = get_config_service()
    current_context = config_service.config.current_context_name

    # Create session state
    now = datetime.now().astimezone()
    end_time = now + timedelta(minutes=duration)

    session = SessionState(
        session_id=str(uuid.uuid4()),
        task_id=task_id,
        task_title=task_title,
        start_time=now.isoformat(),
        end_time=end_time.isoformat(),
        duration_minutes=duration,
        status="active",
        session_type="focus",
        context=current_context,
    )

    # Save initial state
    state_manager.save(session)

    # Show confirmation
    console.print("\n[bold green]🍅 Focus session started[/bold green]")
    console.print(f"Task: {task_title} (#{task_id[:8]})")
    console.print(f"Duration: {duration} minutes")
    console.print(f"End time: {end_time.strftime('%I:%M %p')}")
    console.print("\nStarting fullscreen timer...\n")

    # Run fullscreen timer
    display = TimerDisplay(console)

    def on_pause():
        """Handle pause event."""
        session.status = "paused"
        session.pause_time = datetime.now().astimezone().isoformat()
        state_manager.save(session)

    def on_resume():
        """Handle resume event."""
        if session.pause_time:
            pause_dt = datetime.fromisoformat(session.pause_time.replace("Z", "+00:00"))
            now_dt = datetime.now().astimezone()
            paused_duration = int((now_dt - pause_dt).total_seconds())
            session.accumulated_paused_seconds += paused_duration

            # Extend end time
            end_dt = session.end_datetime
            new_end = end_dt + timedelta(seconds=paused_duration)
            session.end_time = new_end.isoformat()

        session.status = "active"
        session.pause_time = None
        state_manager.save(session)

    def on_stop():
        """Handle stop event."""
        session.status = "cancelled"
        state_manager.save(session)

    def on_complete():
        """Handle completion event."""
        session.status = "completed"
        state_manager.save(session)

    # Run the timer
    result = display.run_timer(
        session,
        on_pause=on_pause,
        on_resume=on_resume,
        on_stop=on_stop,
        on_complete=on_complete,
    )

    # Handle result
    if result == "completed":
        show_completion_message(session, console)

        # Ask if task is complete
        task_completed = False
        if Confirm.ask("\nDid you complete this task?", default=False):
            task_completed = True
            try:
                # Use TaskService to complete task instead of direct API call
                run_async(task_service.complete_task(task_id))
                console.print("[green]✓ Task marked as completed[/green]")
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not update task status: {e}[/yellow]"
                )

        # Log to history
        try:
            history = HistoryLogger()
            history.log_session(session, completed_task=task_completed)
        except Exception as e:
            console.print(f"[dim]Note: Could not log to history: {e}[/dim]")

        # Clean up state file
        state_manager.delete()

    elif result == "stopped":
        show_stopped_message(session, console)

        # Log to history as cancelled
        try:
            history = HistoryLogger()
            history.log_session(session, completed_task=False)
        except Exception as e:
            console.print(f"[dim]Note: Could not log to history: {e}[/dim]")

        # Clean up state file
        state_manager.delete()

    else:  # interrupted
        console.print("\n[yellow]Session interrupted. State saved.[/yellow]")
        console.print("Use 'todopro focus resume' to continue.")


@app.command("resume")
def resume_focus():
    """Resume a paused or interrupted focus session."""
    state_manager = SessionStateManager()
    session = state_manager.load()

    if not session:
        console.print("[yellow]No active focus session found[/yellow]")
        raise typer.Exit(0)

    # Check if session expired
    remaining = session.time_remaining()
    if remaining <= 0:
        console.print("[yellow]Session has expired[/yellow]")
        console.print(f"Task: {session.task_title} (#{session.task_id[:8]})")

        if Confirm.ask("Did you complete this task?", default=False):
            # Mark as completed using TaskService
            task_service = get_task_service()
            try:
                run_async(task_service.complete_task(session.task_id))
                console.print("[green]✓ Task marked as completed[/green]")
            except Exception:
                pass

        state_manager.delete()
        raise typer.Exit(0)

    # Resume session
    console.print("\n[bold cyan]Resuming focus session[/bold cyan]")
    console.print(f"Task: {session.task_title} (#{session.task_id[:8]})")
    console.print(f"Time remaining: {remaining // 60}:{remaining % 60:02d}")
    console.print()

    # If paused, calculate pause duration and update
    if session.status == "paused" and session.pause_time:
        pause_dt = datetime.fromisoformat(session.pause_time.replace("Z", "+00:00"))
        now_dt = datetime.now().astimezone()
        paused_duration = int((now_dt - pause_dt).total_seconds())
        session.accumulated_paused_seconds += paused_duration

        # Extend end time
        end_dt = session.end_datetime
        new_end = end_dt + timedelta(seconds=paused_duration)
        session.end_time = new_end.isoformat()
        session.pause_time = None

    session.status = "active"
    state_manager.save(session)

    # Run timer (same as start)
    display = TimerDisplay(console)

    def on_pause():
        session.status = "paused"
        session.pause_time = datetime.now().astimezone().isoformat()
        state_manager.save(session)

    def on_resume():
        if session.pause_time:
            pause_dt = datetime.fromisoformat(session.pause_time.replace("Z", "+00:00"))
            now_dt = datetime.now().astimezone()
            paused_duration = int((now_dt - pause_dt).total_seconds())
            session.accumulated_paused_seconds += paused_duration

            end_dt = session.end_datetime
            new_end = end_dt + timedelta(seconds=paused_duration)
            session.end_time = new_end.isoformat()

        session.status = "active"
        session.pause_time = None
        state_manager.save(session)

    def on_stop():
        session.status = "cancelled"
        state_manager.save(session)

    def on_complete():
        session.status = "completed"
        state_manager.save(session)

    result = display.run_timer(
        session,
        on_pause=on_pause,
        on_resume=on_resume,
        on_stop=on_stop,
        on_complete=on_complete,
    )

    # Handle completion
    if result == "completed":
        show_completion_message(session, console)

        task_completed = False
        if Confirm.ask("\nDid you complete this task?", default=False):
            task_completed = True
            # Use TaskService instead of direct API call
            task_service = get_task_service()
            try:
                run_async(task_service.complete_task(session.task_id))
                console.print("[green]✓ Task marked as completed[/green]")
            except Exception:
                pass

        try:
            history = HistoryLogger()
            history.log_session(session, completed_task=task_completed)
        except Exception as e:
            console.print(f"[dim]Note: Could not log to history: {e}[/dim]")

        state_manager.delete()

    elif result == "stopped":
        show_stopped_message(session, console)

        try:
            history = HistoryLogger()
            history.log_session(session, completed_task=False)
        except Exception as e:
            console.print(f"[dim]Note: Could not log to history: {e}[/dim]")

        state_manager.delete()

    else:
        console.print("\n[yellow]Session paused. State saved.[/yellow]")
        console.print("Use 'todopro focus resume' to continue.")


@app.command("stop")
def stop_focus():
    """Stop the current focus session."""
    state_manager = SessionStateManager()
    session = state_manager.load()

    if not session:
        console.print("[yellow]No active focus session found[/yellow]")
        raise typer.Exit(0)

    console.print("\n[yellow]Stopping focus session[/yellow]")
    console.print(f"Task: {session.task_title} (#{session.task_id[:8]})")

    # Mark as cancelled
    session.status = "cancelled"
    state_manager.save(session)

    # Log to history
    try:
        history = HistoryLogger()
        history.log_session(session, completed_task=False)
    except Exception as e:
        console.print(f"[dim]Note: Could not log to history: {e}[/dim]")

    # Clean up
    state_manager.delete()
    console.print("[green]✓ Session stopped[/green]\n")


@app.command("status")
def focus_status():
    """Show current focus session status."""
    state_manager = SessionStateManager()
    session = state_manager.load()

    if not session:
        console.print("[dim]No active focus session[/dim]")
        raise typer.Exit(0)

    console.print("\n[bold cyan]Current Focus Session[/bold cyan]\n")
    console.print(f"Task: {session.task_title}")
    console.print(f"ID: #{session.task_id[:8]}")
    console.print(f"Status: {session.status}")
    console.print(f"Duration: {session.duration_minutes} minutes")

    remaining = session.time_remaining()
    if remaining > 0:
        console.print(f"Time remaining: {remaining // 60}:{remaining % 60:02d}")
    else:
        console.print("[yellow]Session has expired[/yellow]")

    console.print()


@app.command("cycle")
def auto_cycle(
    task_id: str = typer.Argument(
        None, help="Initial task ID (if not provided, will suggest)"
    ),
    work: int = typer.Option(25, "--work", "-w", help="Work duration (minutes)"),
    short_break: int = typer.Option(
        5, "--short-break", "-s", help="Short break duration (minutes)"
    ),
    long_break: int = typer.Option(
        15, "--long-break", "-l", help="Long break duration (minutes)"
    ),
    cycles: int = typer.Option(4, "--cycles", "-c", help="Cycles before long break"),
):
    """Start an automatic Pomodoro cycle with breaks."""
    # Get initial task
    if not task_id:
        console.print("[cyan]No task specified. Suggesting tasks...[/cyan]\n")
        task_service = get_task_service()
        try:
            raw_tasks = run_async(task_service.list_tasks(status="active"))
            tasks_dicts = [
                {"id": t.id, "title": t.content, "priority": t.priority,
                 "due_date": t.due_date, "labels": t.labels,
                 "estimated_minutes": getattr(t, "estimated_minutes", 25)}
                for t in raw_tasks
            ]
        except Exception:
            tasks_dicts = []
        engine = _get_suggestion_engine()
        suggestions = engine.suggest_tasks(tasks=tasks_dicts, limit=5)

        if not suggestions:
            console.print("[yellow]No tasks available for focus[/yellow]")
            raise typer.Exit(0)

        # Show suggestions
        console.print("[bold]Suggested tasks:[/bold]\n")
        for i, item in enumerate(suggestions, 1):
            task = item["task"]
            score = item["score"]
            console.print(f"{i}. {task['title']} (score: {score:.1f})")

        # Let user choose
        choice = Prompt.ask("\nSelect task", default="1")
        try:
            idx = int(choice) - 1
            task_id = suggestions[idx]["task"]["id"]
        except (ValueError, IndexError) as e:
            console.print("[red]Invalid selection[/red]")
            raise typer.Exit(1) from e

    # Get task details using TaskService
    task_service = get_task_service()
    try:
        current_task = run_async(task_service.get_task(task_id))
        current_task_id = task_id
        current_task_title = current_task.content
    except Exception as e:
        console.print(f"[red]Error fetching task: {e}[/red]")
        raise typer.Exit(1) from e

    # Initialize cycle config
    config = PomodoroConfig(
        focus_duration=work,
        short_break=short_break,
        long_break=long_break,
        sessions_before_long_break=cycles,
    )

    cycle_state = CycleState()
    history = HistoryLogger()
    state_manager = SessionStateManager()

    config_service = get_config_service()
    current_context = config_service.get_current_context()

    console.print("\n[bold green]🍅 Starting auto-cycle mode[/bold green]")
    console.print(
        f"Work: {work}m | Short break: {short_break}m | Long break: {long_break}m"
    )
    console.print(f"Cycles before long break: {cycles}\n")

    # Main cycle loop
    while True:
        # Determine phase and duration
        phase = cycle_state.current_phase
        duration = cycle_state.get_duration(config)

        if phase == "focus":
            session_type = "focus"
            console.print(f"\n[bold cyan]Focus: {current_task_title}[/bold cyan]")
        elif phase == "short_break":
            session_type = "short_break"
            console.print("\n[bold yellow]Short Break[/bold yellow]")
        else:  # long_break
            session_type = "long_break"
            console.print("\n[bold magenta]Long Break[/bold magenta]")

        # Create session
        now = datetime.now().astimezone()
        end_time = now + timedelta(minutes=duration)

        session = SessionState(
            session_id=str(uuid.uuid4()),
            task_id=current_task_id if phase == "focus" else "break",
            task_title=(
                current_task_title
                if phase == "focus"
                else f"{phase.replace('_', ' ').title()}"
            ),
            start_time=now.isoformat(),
            end_time=end_time.isoformat(),
            duration_minutes=duration,
            status="active",
            session_type=session_type,
            context=current_context,
        )

        state_manager.save(session)

        # Run timer
        display = TimerDisplay(console)

        def on_pause():
            session.status = "paused"
            session.pause_time = datetime.now().astimezone().isoformat()
            state_manager.save(session)

        def on_resume():
            if session.pause_time:
                pause_dt = datetime.fromisoformat(
                    session.pause_time.replace("Z", "+00:00")
                )
                now_dt = datetime.now().astimezone()
                paused_duration = int((now_dt - pause_dt).total_seconds())
                session.accumulated_paused_seconds += paused_duration

                end_dt = session.end_datetime
                new_end = end_dt + timedelta(seconds=paused_duration)
                session.end_time = new_end.isoformat()

            session.status = "active"
            session.pause_time = None
            state_manager.save(session)

        def on_stop():
            session.status = "cancelled"
            state_manager.save(session)

        def on_complete():
            session.status = "completed"
            state_manager.save(session)

        result = display.run_timer(
            session,
            on_pause=on_pause,
            on_resume=on_resume,
            on_stop=on_stop,
            on_complete=on_complete,
        )

        # Handle result
        if result == "completed":
            # Log session
            history.log_session(
                session,
                completed_task=(phase == "focus"),
            )
            state_manager.delete()

            # Check if we should continue
            if cycle_state.current_phase == "focus":
                # Ask if task is done
                if Confirm.ask(
                    f"\nDid you complete the task '{current_task_title}'?",
                    default=False,
                ):
                    # Mark task complete using TaskService
                    try:
                        run_async(task_service.complete_task(current_task_id))
                        console.print("[green]✓ Task marked as completed[/green]")

                        # Get next task
                        try:
                            raw_tasks = run_async(task_service.list_tasks(status="active"))
                            tasks_dicts = [
                                {"id": t.id, "title": t.content, "priority": t.priority,
                                 "due_date": t.due_date, "labels": t.labels,
                                 "estimated_minutes": getattr(t, "estimated_minutes", 25)}
                                for t in raw_tasks
                            ]
                        except Exception:
                            tasks_dicts = []
                        engine = _get_suggestion_engine()
                        suggestions = engine.suggest_tasks(tasks=tasks_dicts, limit=1)

                        if suggestions:
                            current_task_id = suggestions[0]["task"]["id"]
                            current_task_title = suggestions[0]["task"]["title"]
                            console.print(f"[dim]Next task: {current_task_title}[/dim]")
                    except Exception:
                        pass

            # Advance cycle
            cycle_state.advance(config)

            # Ask to continue
            next_phase_name = cycle_state.current_phase.replace("_", " ").title()

            if not Confirm.ask(f"\nContinue to {next_phase_name}?", default=True):
                console.print("\n[yellow]Auto-cycle stopped.[/yellow]")
                console.print(
                    f"Completed {cycle_state.total_sessions_completed} sessions\n"
                )
                break

        elif result == "stopped":
            # User stopped
            history.log_session(session, completed_task=False)
            state_manager.delete()

            console.print("\n[yellow]Auto-cycle stopped.[/yellow]")
            console.print(
                f"Completed {cycle_state.total_sessions_completed} sessions\n"
            )
            break

        else:
            # Interrupted
            console.print("\n[yellow]Session interrupted. State saved.[/yellow]")
            break


@app.command("templates")
def list_templates():
    """List available focus session templates."""
    tm = _get_template_manager()
    templates = tm.list_templates()

    console.print("\n[bold cyan]Focus Session Templates[/bold cyan]\n")

    from rich.table import Table

    table = Table(show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Duration", justify="right")
    table.add_column("Breaks", justify="center")
    table.add_column("Description", style="dim")

    for name, data in templates:
        breaks = "✓" if data.get("breaks_enabled", True) else "✗"
        table.add_row(name, f"{data['duration']}m", breaks, data.get("description", ""))

    console.print(table)
    console.print(
        "\nUse: [cyan]todopro focus start <task-id> --template=<name>[/cyan]\n"
    )


@app.command("template")
def manage_template(
    action: str = typer.Argument(..., help="create or delete"),
    name: str = typer.Argument(..., help="Template name"),
    duration: int = typer.Option(25, "--duration", "-d", help="Duration in minutes"),
    no_breaks: bool = typer.Option(False, "--no-breaks", help="Disable breaks"),
    description: str = typer.Option("", "--description", help="Template description"),
):
    """Create or delete a custom focus template."""
    tm = _get_template_manager()

    if action == "create":
        tm.create_template(
            name=name,
            duration=duration,
            breaks_enabled=not no_breaks,
            description=description,
        )
        console.print(
            f"[green]✓ Template '{name}' created ({duration} minutes)[/green]"
        )

    elif action == "delete":
        if tm.delete_template(name):
            console.print(f"[green]✓ Template '{name}' deleted[/green]")
        else:
            console.print(
                f"[yellow]Cannot delete template '{name}' (not found or is a default template)[/yellow]"
            )

    else:
        console.print(f"[red]Unknown action: {action}. Use 'create' or 'delete'[/red]")
        raise typer.Exit(1)
