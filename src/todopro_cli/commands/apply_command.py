"""Command 'apply' of todopro-cli — apply saved filters to list tasks."""

import typer

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.filters import FiltersAPI
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer(help="Apply saved resources")
console = get_console()


@app.command("filter")
@command_wrapper
async def apply_filter(
    name: str = typer.Argument(..., help="Filter name or ID"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
) -> None:
    """Apply a saved filter to list matching tasks."""
    client = get_client()
    api = FiltersAPI(client)
    try:
        # Resolve name → ID if needed
        filter_id = name
        if not _looks_like_uuid(name):
            found = await api.find_filter_by_name(name)
            if found is None:
                console.print(f"[red]Error: Filter '{name}' not found.[/red]")
                raise typer.Exit(1)
            filter_id = found["id"]
            console.print(f"[dim]Applying filter: {found.get('name', filter_id)}[/dim]")

        tasks = await api.apply_filter(filter_id)
        result = {"tasks": tasks}
        format_output(result, output)
    finally:
        await client.close()


def _looks_like_uuid(value: str) -> bool:
    """Heuristic: a UUID is 36 chars with dashes at positions 8, 13, 18, 23."""
    return len(value) == 36 and value.count("-") == 4
