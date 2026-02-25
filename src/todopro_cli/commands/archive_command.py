"""Archive/Unarchive commands - Archive and unarchive projects."""

import typer

from todopro_cli.services.project_service import get_project_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output, format_success
from todopro_cli.utils.uuid_utils import resolve_project_uuid

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Archive projects")
console = get_console()


@app.command("project")
@command_wrapper
async def archive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Archive a project."""

    project_service = get_project_service()

    project_id = await resolve_project_uuid(project_id, project_service.repository)
    project = await project_service.archive_project(project_id)
    format_success(f"Project archived: {project.id}")
    format_output(project.model_dump(), output)
