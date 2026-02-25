"""Import command - Import data."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper
from todopro_cli.utils.ui.console import get_console
app = typer.Typer(cls=SuggestingGroup, help="Import data")
console = get_console()


@app.command("data")
@command_wrapper
async def import_data(
    input_file: str = typer.Argument(..., help="Input file path"),
    merge: bool = typer.Option(False, "--merge", help="Merge with existing data"),
) -> None:
    """Import data from JSON file."""
    from todopro_cli.services.data_service import DataService

    storage_strategy_context = get_storage_strategy_context()
    data_service = DataService(factory)

    await data_service.import_data(input_file, merge=merge)
    format_success(f"Data imported from: {input_file}")
