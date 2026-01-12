"""Main entry point for TodoPro CLI."""

import typer
from rich.console import Console

from todopro_cli import __version__
from todopro_cli.commands import auth, config, labels, projects, tasks, utils

# Create main app
app = typer.Typer(
    name="todopro",
    help="A professional command-line interface for TodoPro task management",
    no_args_is_help=True,
)

console = Console()


# Add subcommands
app.add_typer(auth.app, name="login", help="Login to TodoPro")
app.add_typer(auth.app, name="auth", help="Authentication commands")
app.add_typer(tasks.app, name="tasks", help="Task management commands")
app.add_typer(projects.app, name="projects", help="Project management commands")
app.add_typer(labels.app, name="labels", help="Label management commands")
app.add_typer(config.app, name="config", help="Configuration management")
app.add_typer(utils.app, name="utils", help="Utility commands")


# Add top-level commands
@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]TodoPro CLI[/bold] version [cyan]{__version__}[/cyan]")


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


# Main entry point
def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
