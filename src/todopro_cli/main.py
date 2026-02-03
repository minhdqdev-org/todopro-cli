"""Main entry point for TodoPro CLI."""

import asyncio
import subprocess

import typer
from rich.console import Console

from todopro_cli import __version__
from todopro_cli.api.client import get_client
from todopro_cli.commands import (
    analytics,
    auth,
    config,
    contexts,
    data,
    encryption,
    labels,
    projects,
    tasks,
    timer,
)
from todopro_cli.commands.utils import errors as show_errors
from todopro_cli.config import get_config_manager
from todopro_cli.ui.textual_prompt import get_interactive_input
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.update_checker import check_for_updates, is_update_available

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
app.add_typer(encryption.app, name="encryption", help="Manage end-to-end encryption")
app.add_typer(data.app, name="data", help="Data management (import, export, purge)")
app.add_typer(contexts.app, name="contexts", help="Context management (@home, @office)")
app.add_typer(timer.app, name="timer", help="Pomodoro timer for focus sessions")


# Add top-level commands
@app.command()
def version() -> None:
    """Show version information and API health."""
    console.print(f"[bold]TodoPro CLI[/bold] version [cyan]{__version__}[/cyan]")
    console.print()

    # Check API health

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
                    console.print(
                        f"[yellow]⚠ API returned status {response.status_code}[/yellow]"
                    )
            except Exception as e:
                console.print(f"[red]✗ API health check failed: {str(e)}[/red]")
            finally:
                await client.close()

        asyncio.run(check_health())
    except Exception:
        # Silently skip health check if there's an error
        pass


@app.command()
def update(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Update TodoPro CLI to the latest version."""

    console.print("[bold]Checking for updates...[/bold]")

    try:
        is_available, latest_version = is_update_available()

        if not is_available:
            if latest_version:
                console.print(
                    f"[green]✓[/green] You're already on the latest version ([cyan]{__version__}[/cyan])"
                )
            else:
                console.print(
                    "[yellow]⚠[/yellow] Unable to check for updates. Please try again later."
                )
            return

        console.print(
            f"\n[green]✨ New version available:[/green] [bold cyan]{latest_version}[/bold cyan]"
        )
        console.print(f"[dim]Current version: {__version__}[/dim]\n")

        # Prompt user if not in non-interactive mode
        if not yes:
            confirm = typer.confirm("Do you want to update now?", default=True)
            if not confirm:
                console.print("[yellow]Update cancelled.[/yellow]")
                return

        console.print("\n[bold]Updating TodoPro CLI...[/bold]")

        # Run uv tool upgrade
        result = subprocess.run(
            ["uv", "tool", "upgrade", "todopro-cli"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print(
                f"\n[green]✓ Successfully updated to version {latest_version}![/green]"
            )
            console.print("[dim]Run 'todopro version' to verify the update.[/dim]")
        else:
            console.print("\n[red]✗ Update failed.[/red]")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            console.print("\n[yellow]You can try updating manually with:[/yellow]")
            console.print("  [cyan]uv tool upgrade todopro-cli[/cyan]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]✗ 'uv' command not found. Please install uv first:[/red]")
        console.print("  [cyan]curl -LsSf https://astral.sh/uv/install.sh | sh[/cyan]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        raise typer.Exit(1) from e


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
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show tasks for today (overdue + today's tasks)."""
    tasks.today(output=output, json=json, compact=compact, profile=profile)


@app.command()
def next(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    json: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show the next task to do right now."""
    tasks.next_task(output=output, json=json, profile=profile)


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
def add(
    input_text: str | None = typer.Argument(
        None, help="Natural language task description"
    ),
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
        try:
            input_text = asyncio.run(get_interactive_input(profile=profile))
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0) from None

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
    show_errors(limit=limit, clear=clear, all_errors=all_errors)


# Main entry point
def main():
    """Main entry point."""

    try:
        app()
    finally:
        # Check for updates after command execution (non-blocking)
        check_for_updates()


if __name__ == "__main__":
    main()
