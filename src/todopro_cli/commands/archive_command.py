"""Archive/Unarchive commands - Archive and unarchive projects."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.project_service import ProjectService
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_output, format_success
from todopro_cli.utils.uuid_utils import resolve_project_uuid

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Archive projects")
console = Console()


@app.command("project")
@command_wrapper
async def archive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Archive a project."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project_id = await resolve_project_uuid(project_id, project_repo)
    project = await project_service.archive_project(project_id)
    format_success(f"Project archived: {project.id}")
    format_output(project.model_dump(), output)
