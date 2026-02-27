"""Unarchive command - Unarchive projects."""

import typer

from todopro_cli.services.config_service import get_storage_strategy_context
from todopro_cli.services.project_service import ProjectService
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Unarchive projects")
console = get_console()


@app.command("project")
@command_wrapper
async def unarchive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Unarchive a project."""
    storage_strategy_context = get_storage_strategy_context()
    project_repo = storage_strategy_context.project_repository
    project_service = ProjectService(project_repo)

    project = await project_service.unarchive_project(project_id)
    format_success(f"Project unarchived: {project.id}")
    format_output(project.model_dump(), output)
