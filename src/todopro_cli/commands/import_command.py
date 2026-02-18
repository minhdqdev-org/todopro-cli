"""Import command - Import data."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Import data")
console = Console()


@app.command("data")
@command_wrapper
async def import_data(
    input_file: str = typer.Argument(..., help="Input file path"),
    merge: bool = typer.Option(False, "--merge", help="Merge with existing data"),
) -> None:
    """Import data from JSON file."""
    from todopro_cli.services.data_service import DataService

    strategy = get_strategy_context()
    data_service = DataService(factory)

    await data_service.import_data(input_file, merge=merge)
    format_success(f"Data imported from: {input_file}")
