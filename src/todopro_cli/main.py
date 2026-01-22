"""Main entry point for TodoPro CLI."""

import typer
from rich.console import Console

from todopro_cli import __version__
from todopro_cli.commands import analytics, auth, config, labels, projects, tasks, utils

# Create main app
app = typer.Typer(
    name="todopro",
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
app.add_typer(analytics.app, name="analytics", help="Analytics and productivity insights")
app.add_typer(utils.app, name="utils", help="Utility commands")


# Add top-level commands
@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]TodoPro CLI[/bold] version [cyan]{__version__}[/cyan]")


@app.command()
def login(
    email: str | None = typer.Option(None, "--email", "-e", help="Email address"),
    password: str | None = typer.Option(None, "--password", "-p", help="Password"),
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
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
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
def health(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Check API connectivity and health."""
    # Delegate to utils command
    utils.health(verbose=verbose, profile=profile)


@app.command()
def today(
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show tasks for today (overdue + today's tasks)."""
    tasks.today(output=output, compact=compact, profile=profile)


@app.command()
def next(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show the next task to do right now."""
    tasks.next_task(output=output, profile=profile)


@app.command()
def complete(
    task_id: str = typer.Argument(..., help="Task ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Mark a task as completed."""
    tasks.complete_task(task_id=task_id, output=output, profile=profile)


@app.command()
def describe(
    resource_type: str = typer.Argument(..., help="Resource type (project)"),
    resource_id: str = typer.Argument(..., help="Resource ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Describe a resource in detail."""
    if resource_type.lower() == "project":
        projects.describe_project(project_id=resource_id, output=output, profile=profile)
    else:
        console.print(f"[red]Unknown resource type: {resource_type}[/red]")
        raise typer.Exit(1)


# Main entry point
def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
