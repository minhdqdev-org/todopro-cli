"""Configuration management commands."""

import typer
from rich.table import Table

from todopro_cli.models.config_models import Context
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Configuration management commands")
console = get_console()


@app.command("view")
def view_config(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """View current configuration."""
    try:
        config_service = get_config_service()
        config_dict = config_service.config.model_dump()
        format_output(config_dict, output)
    except Exception as e:
        format_error(f"Failed to view config: {str(e)}")
        raise typer.Exit(1) from e


@app.command("get")
def get_config(
    key: str = typer.Argument(..., help="Configuration key (e.g., api.endpoint)"),
) -> None:
    """Get a configuration value."""
    try:
        config_service = get_config_service()
        value = config_service.get(key)
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
) -> None:
    """Set a configuration value."""

    config_service = get_config_service()

    # Try to convert value to appropriate type
    parsed_value: str | int | bool = value
    if value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"
    elif value.isdigit():
        parsed_value = int(value)

    config_service.set(key, parsed_value)
    format_success(f"Configuration '{key}' set to '{parsed_value}'")


@app.command("reset")
def reset_config(
    key: str | None = typer.Argument(None, help="Configuration key to reset"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reset configuration to defaults."""
    if not yes:
        msg = "entire configuration" if not key else f"'{key}'"
        confirm = typer.confirm(f"Are you sure you want to reset {msg}?")
        if not confirm:
            format_error("Cancelled")
            raise typer.Exit(0)

    config_service = get_config_service()
    config_service.reset(key)

    if key:
        format_success(f"Configuration '{key}' reset to default")
    else:
        format_success("Configuration reset to defaults")


# @app.command("list")
# def list_profiles(
#
# ) -> None:
#     """List all configuration profiles."""
#     try:
#         config_service = get_config_service(profile)
#         profiles = config_service.list_profiles()

#         if not profiles:
#             console.print("[yellow]No profiles found[/yellow]")
#             return

#         for prof in profiles:
#             marker = " *" if prof == profile else ""
#             console.print(f"{prof}{marker}")
#     except Exception as e:
#         format_error(f"Failed to list profiles: {str(e)}")
#         raise typer.Exit(1) from e


@app.command("use-context")
@command_wrapper(auth_required=False)
def use_context(
    context_name: str = typer.Argument(..., help="Context name (dev/staging/prod)"),
) -> None:
    """Switch to a different context (environment)."""
    try:
        config_service = get_config_service()

        # Initialize contexts if they don't exist
        if not config_service.config.contexts:
            config_service.init_default_contexts()

        config_service.use_context(context_name)
        context = config_service.get_current_context()

        if context:
            format_success(
                f"Switched to context '{context.name}'\n"
                f"Source: {context.source}\n"
                f"Description: {context.description}"
            )
    except ValueError as e:
        format_error(str(e))
        raise typer.Exit(1) from e
    except Exception as e:
        format_error(f"Failed to switch context: {str(e)}")
        raise typer.Exit(1) from e


@app.command("current-context")
@command_wrapper(auth_required=False)
def current_context(
    output: str = typer.Option("default", "--output", "-o", help="Output format"),
) -> None:
    """Show the current context."""

    config_service = get_config_service()

    # Initialize contexts if they don't exist
    if not config_service.config.contexts:
        config_service.init_default_contexts()

    context = config_service.get_current_context()

    if not context:
        format_error("No current context set")
        raise typer.Exit(1)

    if output == "table":
        table = Table(title="Current Context")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Name", context.name)
        table.add_row("Type", context.type)
        table.add_row("Source", context.source)
        table.add_row("Description", context.description)

        console.print(table)
    else:
        format_output(context.model_dump(), output)


@app.command("get-contexts")
@command_wrapper(auth_required=False)
def get_contexts(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """List all available contexts."""
    config_service = get_config_service()

    # Initialize contexts if they don't exist
    if not config_service.config.contexts:
        config_service.init_default_contexts()

    contexts = config_service.list_contexts()
    current = config_service.config.current_context_name

    if output == "table":
        table = Table(title="Available Contexts")
        table.add_column("Current", style="yellow")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Source", style="green")
        table.add_column("Description", style="white")

        for ctx in contexts:
            marker = "*" if ctx.name == current else ""
            table.add_row(marker, ctx.name, ctx.type, ctx.source, ctx.description)

        console.print(table)
    else:
        format_output([ctx.model_dump() for ctx in contexts], output)


@app.command("set-context")
@command_wrapper(auth_required=False)
def set_context(
    name: str = typer.Argument(..., help="Context name"),
    endpoint: str = typer.Option(..., "--endpoint", help="API endpoint URL"),
    description: str = typer.Option("", "--description", help="Context description"),
) -> None:
    """Add or update a context."""
    config_service = get_config_service()

    # Initialize contexts if they don't exist
    if not config_service.config.contexts:
        config_service.init_default_contexts()

    # `set-context` manages remote (API) environments; the endpoint is its source.
    existing = config_service.get_context(name)
    if existing is not None:
        existing.source = endpoint.rstrip("/")
        existing.type = "remote"
        if description:
            existing.description = description
        config_service.save_config()
    else:
        config_service.add_context(
            Context(
                name=name,
                type="remote",
                source=endpoint.rstrip("/"),
                description=description,
            )
        )
    format_success(f"Context '{name}' created/updated successfully")


@app.command("delete-context")
@command_wrapper(auth_required=False)
def delete_context(
    name: str = typer.Argument(..., help="Context name to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a context."""

    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete context '{name}'?")
        if not confirm:
            format_error("Cancelled")
            raise typer.Exit(0)

    config_service = get_config_service()
    config_service.remove_context(name)
    config_service.clear_context_credentials(name)

    format_success(f"Context '{name}' deleted successfully")
