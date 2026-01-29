"""Main entry point for TodoPro CLI."""

import typer
from rich.console import Console

from todopro_cli import __version__
from todopro_cli.commands import (  # contexts, timer
    analytics,
    auth,
    config,
    labels,
    projects,
    tasks,
)
from todopro_cli.utils.typer_helpers import SuggestingGroup

# Create main app with custom group class
app = typer.Typer(
    name="todopro",
    cls=SuggestingGroup,
    help="A professional command-line interface for TodoPro task management",
    no_args_is_help=True,
)

console = Console()


# Add subcommands
app.add_typer(auth.app, name="auth", help="Authentication commands")
app.add_typer(tasks.app, name="tasks", help="Task management commands")
app.add_typer(projects.app, name="projects", help="Project management commands")
app.add_typer(labels.app, name="labels", help="Label management commands")
app.add_typer(config.app, name="config", help="Configuration management")
app.add_typer(
    analytics.app, name="analytics", help="Analytics and productivity insights"
)
# TODO: Convert Click groups to Typer apps - these are incompatible with Typer 0.9.0
# app.add_typer(contexts.contexts, name="contexts", help="Context management (@home, @office)")
# app.add_typer(timer.timer, name="timer", help="Pomodoro timer for focus sessions")


# Add top-level commands
@app.command()
def version() -> None:
    """Show version information and API health."""
    console.print(f"[bold]TodoPro CLI[/bold] version [cyan]{__version__}[/cyan]")
    console.print()
    
    # Check API health
    import asyncio
    from todopro_cli.api.client import get_client
    from todopro_cli.config import get_config_manager
    
    try:
        config_manager = get_config_manager("default")
        credentials = config_manager.load_credentials()
        
        if not credentials:
            console.print("[yellow]Not logged in - unable to check API health[/yellow]")
            return
        
        async def check_health():
            client = get_client("default")
            try:
                # Try a simple request to check connectivity
                response = await client.get("/v1/tasks", params={"limit": 1})
                if response.status_code == 200:
                    console.print("[green]✓ API is healthy[/green]")
                else:
                    console.print(f"[yellow]⚠ API returned status {response.status_code}[/yellow]")
            except Exception as e:
                console.print(f"[red]✗ API health check failed: {str(e)}[/red]")
            finally:
                await client.close()
        
        asyncio.run(check_health())
    except Exception:
        # Silently skip health check if there's an error
        pass



@app.command()
def login(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    save_profile: bool = typer.Option(
        False, "--save-profile", help="Save as default profile"
    ),
) -> None:
    """Login to TodoPro."""
    # Delegate to auth command
    auth.login(
        email=email,
        password=password,
        profile=profile,
        endpoint=endpoint,
        save_profile=save_profile,
    )


@app.command()
def whoami(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Show current user information."""
    # Delegate to auth command
    auth.whoami(profile=profile, output=output)


@app.command()
def logout(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    all_profiles: bool = typer.Option(False, "--all", help="Logout from all profiles"),
) -> None:
    """Logout from TodoPro."""
    # Delegate to auth command
    auth.logout(profile=profile, all_profiles=all_profiles)


@app.command()
def today(
    output: str = typer.Option("pretty", "--output", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show tasks for today (overdue + today's tasks)."""
    tasks.today(output=output, compact=compact, profile=profile)


@app.command()
def next(
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show the next task to do right now."""
    tasks.next_task(output=output, profile=profile)


@app.command()
def complete(
    task_ids: list[str] = typer.Argument(..., help="Task ID(s) - can specify multiple"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    sync: bool = typer.Option(
        False, "--sync", help="Wait for completion (synchronous mode)"
    ),
) -> None:
    """Mark one or more tasks as completed."""
    tasks.complete_task(task_ids=task_ids, output=output, profile=profile, sync=sync)


@app.command()
def reschedule(
    task_id: str | None = typer.Argument(
        None, help="Task ID or suffix (omit to reschedule all overdue tasks)"
    ),
    date: str | None = typer.Option(
        None, "--date", "-d", help="New due date (today/tomorrow/YYYY-MM-DD)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Reschedule a task or all overdue tasks to today."""
    tasks.reschedule(target=task_id, date=date, yes=yes, profile=profile)


@app.command("add")
def quick_add(
    input_text: str | None = typer.Argument(None, help="Natural language task description"),
    output: str = typer.Option("table", "--output", help="Output format"),
    show_parsed: bool = typer.Option(
        False, "--show-parsed", help="Show parsed details"
    ),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """
    Quick add a task using natural language.

    Examples:
      todopro add "Buy milk tomorrow at 2pm #groceries p1 @shopping"
      todopro add "Review PR #work p2 @code-review"
      todopro add "Team meeting every Monday at 10am #meetings"
    """
    # If no input text, enter interactive mode
    if input_text is None:
        from rich.console import Console
        from rich.panel import Panel
        
        console = Console()
        console.print(Panel(
            "[dim]Type the task here (!!1, !!2 for priority, @label for label, #project for project,...)[/dim]",
            border_style="blue",
            padding=(0, 1)
        ))
        
        input_text = typer.prompt("❯", prompt_suffix=" ")
        
        if not input_text or not input_text.strip():
            console.print("[yellow]No task entered. Cancelled.[/yellow]")
            raise typer.Exit(0)
    
    tasks.quick_add(text=input_text, yes=False, profile=profile)


@app.command()
def describe(
    resource_type: str = typer.Argument(..., help="Resource type (project)"),
    resource_id: str = typer.Argument(..., help="Resource ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Describe a resource in detail."""
    if resource_type.lower() == "project":
        projects.describe_project(
            project_id=resource_id, output=output, profile=profile
        )
    else:
        console.print(f"[red]Unknown resource type: {resource_type}[/red]")
        raise typer.Exit(1)


@app.command()
def errors(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of errors to show"),
    clear: bool = typer.Option(False, "--clear", help="Clear old errors (>30 days)"),
    all_errors: bool = typer.Option(
        False, "--all", help="Show all errors including acknowledged"
    ),
) -> None:
    """View error logs from background tasks."""
    utils.errors(limit=limit, clear=clear, all_errors=all_errors)


# Main entry point
def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
