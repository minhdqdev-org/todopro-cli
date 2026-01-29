"""Configuration management commands."""

import typer
from rich.console import Console
from rich.table import Table

from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Configuration management commands")
console = Console()


@app.command("view")
def view_config(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """View current configuration."""
    try:
        config_manager = get_config_manager(profile)
        config_dict = config_manager.config.model_dump()
        format_output(config_dict, output)
    except Exception as e:
        format_error(f"Failed to view config: {str(e)}")
        raise typer.Exit(1) from e


@app.command("get")
def get_config(
    key: str = typer.Argument(..., help="Configuration key (e.g., api.endpoint)"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Get a configuration value."""
    try:
        config_manager = get_config_manager(profile)
        value = config_manager.get(key)
        if value is None:
            format_error(f"Configuration key '{key}' not found")
            raise typer.Exit(1)
        console.print(value)
    except Exception as e:
        format_error(f"Failed to get config: {str(e)}")
        raise typer.Exit(1) from e


@app.command("set")
def set_config(
    key: str = typer.Argument(..., help="Configuration key (e.g., api.endpoint)"),
    value: str = typer.Argument(..., help="Configuration value"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Set a configuration value."""
    try:
        config_manager = get_config_manager(profile)

        # Try to convert value to appropriate type
        parsed_value: str | int | bool = value
        if value.lower() in ("true", "false"):
            parsed_value = value.lower() == "true"
        elif value.isdigit():
            parsed_value = int(value)

        config_manager.set(key, parsed_value)
        format_success(f"Configuration '{key}' set to '{parsed_value}'")
    except Exception as e:
        format_error(f"Failed to set config: {str(e)}")
        raise typer.Exit(1) from e


@app.command("reset")
def reset_config(
    key: str | None = typer.Argument(None, help="Configuration key to reset"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reset configuration to defaults."""
    try:
        if not yes:
            msg = "entire configuration" if not key else f"'{key}'"
            confirm = typer.confirm(f"Are you sure you want to reset {msg}?")
            if not confirm:
                format_error("Cancelled")
                raise typer.Exit(0)

        config_manager = get_config_manager(profile)
        config_manager.reset(key)

        if key:
            format_success(f"Configuration '{key}' reset to default")
        else:
            format_success("Configuration reset to defaults")
    except Exception as e:
        format_error(f"Failed to reset config: {str(e)}")
        raise typer.Exit(1) from e


@app.command("list")
def list_profiles(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """List all configuration profiles."""
    try:
        config_manager = get_config_manager(profile)
        profiles = config_manager.list_profiles()

        if not profiles:
            console.print("[yellow]No profiles found[/yellow]")
            return

        for prof in profiles:
            marker = " *" if prof == profile else ""
            console.print(f"{prof}{marker}")
    except Exception as e:
        format_error(f"Failed to list profiles: {str(e)}")
        raise typer.Exit(1) from e


@app.command("use-context")
def use_context(
    context_name: str = typer.Argument(..., help="Context name (dev/staging/prod)"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Switch to a different context (environment)."""
    try:
        config_manager = get_config_manager(profile)

        # Initialize contexts if they don't exist
        if not config_manager.config.contexts:
            config_manager.init_default_contexts()

        config_manager.use_context(context_name)
        context = config_manager.get_current_context()

        if context:
            format_success(
                f"Switched to context '{context.name}'\n"
                f"Endpoint: {context.endpoint}\n"
                f"Description: {context.description}"
            )
    except ValueError as e:
        format_error(str(e))
        raise typer.Exit(1) from e
    except Exception as e:
        format_error(f"Failed to switch context: {str(e)}")
        raise typer.Exit(1) from e


@app.command("current-context")
def current_context(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Show the current context."""
    try:
        config_manager = get_config_manager(profile)

        # Initialize contexts if they don't exist
        if not config_manager.config.contexts:
            config_manager.init_default_contexts()

        context = config_manager.get_current_context()

        if not context:
            format_error("No current context set")
            raise typer.Exit(1)

        if output == "table":
            table = Table(title="Current Context")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Name", context.name)
            table.add_row("Endpoint", context.endpoint)
            table.add_row("Description", context.description)

            console.print(table)
        else:
            format_output(context.model_dump(), output)

    except Exception as e:
        format_error(f"Failed to get current context: {str(e)}")
        raise typer.Exit(1) from e


@app.command("get-contexts")
def get_contexts(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all available contexts."""
    try:
        config_manager = get_config_manager(profile)

        # Initialize contexts if they don't exist
        if not config_manager.config.contexts:
            config_manager.init_default_contexts()

        contexts = config_manager.list_contexts()
        current = config_manager.config.current_context

        if output == "table":
            table = Table(title="Available Contexts")
            table.add_column("Current", style="yellow")
            table.add_column("Name", style="cyan")
            table.add_column("Endpoint", style="green")
            table.add_column("Description", style="white")

            for name, ctx in contexts.items():
                marker = "*" if name == current else ""
                table.add_row(marker, ctx.name, ctx.endpoint, ctx.description)

            console.print(table)
        else:
            format_output([ctx.model_dump() for ctx in contexts.values()], output)

    except Exception as e:
        format_error(f"Failed to list contexts: {str(e)}")
        raise typer.Exit(1) from e


@app.command("set-context")
def set_context(
    name: str = typer.Argument(..., help="Context name"),
    endpoint: str = typer.Option(..., "--endpoint", help="API endpoint URL"),
    description: str = typer.Option("", "--description", help="Context description"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Add or update a context."""
    try:
        config_manager = get_config_manager(profile)

        # Initialize contexts if they don't exist
        if not config_manager.config.contexts:
            config_manager.init_default_contexts()

        config_manager.add_context(name, endpoint, description)
        format_success(f"Context '{name}' created/updated successfully")

    except Exception as e:
        format_error(f"Failed to set context: {str(e)}")
        raise typer.Exit(1) from e


@app.command("delete-context")
def delete_context(
    name: str = typer.Argument(..., help="Context name to delete"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a context."""
    try:
        if not yes:
            confirm = typer.confirm(
                f"Are you sure you want to delete context '{name}'?"
            )
            if not confirm:
                format_error("Cancelled")
                raise typer.Exit(0)

        config_manager = get_config_manager(profile)
        config_manager.remove_context(name)
        config_manager.clear_context_credentials(name)

        format_success(f"Context '{name}' deleted successfully")

    except ValueError as e:
        format_error(str(e))
        raise typer.Exit(1) from e
    except Exception as e:
        format_error(f"Failed to delete context: {str(e)}")
        raise typer.Exit(1) from e
