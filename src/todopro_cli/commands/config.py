"""Configuration management commands."""

from typing import Optional

import typer
from rich.console import Console

from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success

app = typer.Typer(help="Configuration management commands")
console = Console()


@app.command("view")
def view_config(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """View current configuration."""
    try:
        config_manager = get_config_manager(profile)
        config_dict = config_manager.config.model_dump()
        format_output(config_dict, output)
    except Exception as e:
        format_error(f"Failed to view config: {str(e)}")
        raise typer.Exit(1)


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
        raise typer.Exit(1)


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
        raise typer.Exit(1)


@app.command("reset")
def reset_config(
    key: Optional[str] = typer.Argument(None, help="Configuration key to reset"),
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
        raise typer.Exit(1)


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
        raise typer.Exit(1)
