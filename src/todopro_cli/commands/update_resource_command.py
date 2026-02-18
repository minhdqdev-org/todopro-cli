"""Update resources command - Update existing resources."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.task_service import TaskService
from todopro_cli.services.project_service import ProjectService
from todopro_cli.services.label_service import LabelService
from todopro_cli.utils.ui.formatters import format_output, format_success, format_error
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Update resources")
console = Console()


@app.command("task")
@command_wrapper
async def update_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    content: str | None = typer.Option(None, "--content", help="Task content"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    project: str | None = typer.Option(None, "--project", help="Project ID"),
    due: str | None = typer.Option(None, "--due", help="Due date"),
    priority: int | None = typer.Option(None, "--priority", help="Priority (1-4)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a task."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    if not any([content, description, project, due, priority is not None]):
        format_error("No updates specified")
        raise typer.Exit(1)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.update_task(
        resolved_id,
        content=content,
        description=description,
        project_id=project,
        due_date=due,
        priority=priority,
    )
    format_success(f"Task updated: {task.id}")
    format_output(task.model_dump(), output)


@app.command("project")
@command_wrapper
async def update_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    name: str | None = typer.Option(None, "--name", help="Project name"),
    color: str | None = typer.Option(None, "--color", help="Project color"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a project."""
    if name is None and color is None:
        format_error("No updates specified")
        raise typer.Exit(1)

    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project = await project_service.update_project(
        project_id, name=name, color=color
    )
    format_success(f"Project updated: {project.id}")
    format_output(project.model_dump(), output)


@app.command("label")
@command_wrapper
async def update_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    name: str | None = typer.Option(None, "--name", help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a label."""
    if not any([name, color]):
        format_error("No updates specified")
        raise typer.Exit(1)

    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    label = await label_service.update_label(label_id, name=name, color=color)
    format_success(f"Label updated: {label.id}")
    format_output(label.model_dump(), output)
