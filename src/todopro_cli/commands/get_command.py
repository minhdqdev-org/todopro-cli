"""Get command - Get single resource details."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.label_service import LabelService
from todopro_cli.services.project_service import ProjectService
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Get resource details")
console = Console()


@app.command("task")
@command_wrapper
async def get_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get task details."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.get_task(resolved_id)
    format_output(task.model_dump(), output)


@app.command("project")
@command_wrapper
async def get_project(
    project_id: str = typer.Argument(..., help="Project ID or suffix"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get project details."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project = await project_service.get_project(project_id)
    format_output(project.model_dump(), output)


@app.command("label")
@command_wrapper
async def get_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get label details."""
    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    label = await label_service.get_label(label_id)
    format_output(label.model_dump(), output)


@app.command("config")
@command_wrapper
async def get_config(
    key: str = typer.Argument(..., help="Configuration key"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get a configuration value."""
    from todopro_cli.services.config_service import ConfigService

    config_service = ConfigService()
    value = config_service.get(key)

    result = {"key": key, "value": value}
    format_output(result, output)


# @app.command("focus-template")  # DISABLED: Focus mode - deferred, references undefined factory
# @command_wrapper
# async def get_focus_template(
#     template_id: str = typer.Argument(..., help="Template ID"),
#     output: str = typer.Option("table", "--output", "-o", help="Output format"),
# ) -> None:
#     """Get focus template details."""
#     from todopro_cli.services.focus_service import FocusService
#
#     strategy = get_strategy_context()
#     focus_repo = factory.get_focus_session_repository()
#     service = FocusService(focus_repo)
#
#     template = await service.get_template(template_id)
#     format_output(template.model_dump(), output)
