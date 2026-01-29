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


def handle_api_error(exception: Exception, action: str) -> None:
    """Handle API errors uniformly."""
    format_error(f"Error {action}: {str(exception)}")
    raise typer.Exit(1)
