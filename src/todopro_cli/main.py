"""Main entry point for TodoPro CLI."""

import typer
from rich.console import Console

from todopro_cli import __version__
from todopro_cli.commands import auth, config, projects, tasks

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
app.add_typer(config.app, name="config", help="Configuration management")


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


# Main entry point
def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
