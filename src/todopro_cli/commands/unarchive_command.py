"""Unarchive command - Unarchive projects."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.project_service import ProjectService
from todopro_cli.utils.ui.formatters import format_success, format_output
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Unarchive projects")
console = Console()


@app.command("project")
@command_wrapper
async def unarchive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """Unarchive a project."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project = await project_service.unarchive_project(project_id)
    format_success(f"Project unarchived: {project.id}")
    format_output(project.model_dump(), output)
