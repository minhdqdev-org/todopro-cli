"""Utility commands."""

import asyncio

import typer
from todopro_cli.utils.typer_helpers import SuggestingGroup
from rich.console import Console

from todopro_cli.api.client import get_client
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_success

app = typer.Typer(cls=SuggestingGroup, help="Utility commands")
console = Console()


@app.command()
def health(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Check API connectivity and health."""
    try:
        config_manager = get_config_manager(profile)
        endpoint = config_manager.get("api.endpoint")

        console.print(f"[cyan]Checking API health at:[/cyan] {endpoint}")

        async def do_health() -> None:
            client = get_client(profile)
            try:
                # Try a simple health check endpoint
                try:
                    response = await client.get("/health")
                    if response.status_code == 200:
                        format_success("API is healthy")
                        if verbose:
                            console.print(f"Status: {response.status_code}")
                            console.print(f"Response: {response.text}")
                    else:
                        format_error(f"API returned status code {response.status_code}")
                        raise typer.Exit(1)
                except Exception as e:
                    # If /health doesn't exist, try the base endpoint
                    if "404" in str(e):
                        response = await client.get("/")
                        if response.status_code < 400:
                            format_success("API is reachable")
                            if verbose:
                                console.print(f"Status: {response.status_code}")
                        else:
                            raise
                    else:
                        raise
            except Exception as e:
                format_error(f"API health check failed: {str(e)}")
                raise typer.Exit(1)
            finally:
                await client.close()

        asyncio.run(do_health())

    except typer.Exit:
        raise
    except Exception as e:
        format_error(f"Health check failed: {str(e)}")
        raise typer.Exit(1)


@app.command()
def errors(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of errors to show"),
    clear: bool = typer.Option(False, "--clear", help="Clear old errors (>30 days)"),
    all_errors: bool = typer.Option(False, "--all", help="Show all errors including acknowledged"),
) -> None:
    """View error logs from background tasks."""
    from todopro_cli.utils.error_logger import (
        get_recent_errors,
        get_unread_errors,
        clear_old_errors,
        get_log_directory,
    )
    from rich.table import Table
    from datetime import datetime
    
    if clear:
        removed = clear_old_errors(days=30)
        format_success(f"Cleared {removed} old error(s)")
        return
    
    # Get errors
    if all_errors:
        errors_list = get_recent_errors(limit=limit)
    else:
        errors_list = get_unread_errors()
        if not errors_list:
            # If no unread, show recent
            errors_list = get_recent_errors(limit=limit)
    
    if not errors_list:
        console.print("[green]No errors found! ✓[/green]")
        return
    
    # Display errors in a table
    table = Table(title=f"Error Logs ({len(errors_list)} shown)", show_header=True)
    table.add_column("Time", style="cyan", width=20)
    table.add_column("Command", style="yellow", width=15)
    table.add_column("Error", style="red")
    table.add_column("Retries", justify="right", width=8)
    
    for error in errors_list[:limit]:
        timestamp = error.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            time_str = timestamp
        
        command = error.get("command", "unknown")
        error_msg = error.get("error", "")
        retries = error.get("retries", 0)
        
        # Truncate long errors
        if len(error_msg) > 80:
            error_msg = error_msg[:77] + "..."
        
        # Show context if available
        context = error.get("context", {})
        if context.get("task_content"):
            error_msg = f"{error_msg}\n[dim]Task: {context['task_content']}[/dim]"
        
        table.add_row(time_str, command, error_msg, str(retries))
    
    console.print(table)
    console.print()
    console.print(f"[dim]Log file: {get_log_directory() / 'errors.jsonl'}[/dim]")
    console.print(f"[dim]Clear old errors: [cyan]todopro errors --clear[/cyan][/dim]")


def handle_api_error(exception: Exception, action: str) -> None:
    """Handle API errors uniformly."""
    format_error(f"Error {action}: {str(exception)}")
    raise typer.Exit(1)
