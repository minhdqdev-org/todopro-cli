"""Export command - Export data and analytics."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Export data")
console = Console()


@app.command("data")
@command_wrapper
async def export_data(
    output_file: str = typer.Argument(..., help="Output file path"),
    compress: bool = typer.Option(False, "--compress", help="Compress output"),
) -> None:
    """Export all data to JSON file."""
    from todopro_cli.services.data_service import DataService

    strategy = get_strategy_context()
    data_service = DataService(factory)

    await data_service.export_data(output_file, compress=compress)
    format_success(f"Data exported to: {output_file}")


@app.command("stats")
@command_wrapper
async def export_stats(
    output_file: str = typer.Argument(..., help="Output file path"),
) -> None:
    """Export focus statistics to file."""
    from todopro_cli.services.focus_service import FocusService

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    await service.export_stats(output_file)
    format_success(f"Stats exported to: {output_file}")


@app.command("analytics")
@command_wrapper
async def export_analytics(
    output_file: str = typer.Argument(..., help="Output file path"),
) -> None:
    """Export productivity analytics to file."""
    from todopro_cli.services.analytics_service import AnalyticsService

    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    service = AnalyticsService(task_repo)

    await service.export_analytics(output_file)
    format_success(f"Analytics exported to: {output_file}")
