"""Create command - Create new resources."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.task_service import TaskService
from todopro_cli.services.project_service import ProjectService
from todopro_cli.services.label_service import LabelService
from todopro_cli.utils.ui.formatters import format_output, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Create resources")
console = Console()


@app.command("task")
@command_wrapper
async def create_task(
    content: str = typer.Argument(..., help="Task content"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    project: str | None = typer.Option(None, "--project", help="Project ID"),
    due: str | None = typer.Option(None, "--due", help="Due date"),
    priority: int | None = typer.Option(None, "--priority", help="Priority (1-4)"),
    labels: str | None = typer.Option(None, "--labels", help="Comma-separated labels"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new task."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    label_list = None
    if labels:
        label_list = [l.strip() for l in labels.split(",")]

    task = await task_service.add_task(
        content=content,
        description=description,
        project_id=project,
        due_date=due,
        priority=priority or 1,
        labels=label_list,
    )
    format_success(f"Task created: {task.id}")
    format_output(task.model_dump(), output)


@app.command("project")
@command_wrapper
async def create_project(
    name: str = typer.Argument(..., help="Project name"),
    color: str | None = typer.Option(None, "--color", help="Project color"),
    favorite: bool = typer.Option(False, "--favorite", help="Mark as favorite"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new project."""
    if json_opt:
        output = "json"

    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    project = await project_service.create_project(
        name=name, color=color, is_favorite=favorite
    )

    if output == "json":
        from todopro_cli.utils.ui.formatters import format_output
        format_output({"project": project.model_dump()}, "json")
        return

    format_success(f"Project created: {project.name}")
    console.print(f"\n[bold cyan]ID:[/bold cyan] {project.id}")


@app.command("label")
@command_wrapper
async def create_label(
    name: str = typer.Argument(..., help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new label."""
    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    label = await label_service.create_label(name=name, color=color)
    format_success(f"Label created: {label.id}")
    format_output(label.model_dump(), output)


@app.command("context")
@command_wrapper
async def create_context(
    name: str = typer.Argument(..., help="Context name"),
    backend: str = typer.Option("sqlite", "--backend", help="Backend type (sqlite/rest)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new storage context."""
    from todopro_cli.services.context_service import ContextService

    context_service = ContextService()
    context = context_service.create_context(name=name, backend_type=backend)
    format_success(f"Context created: {name}")
    format_output(context, output)


# @app.command("location-context")  # DISABLED: Gamification/location - deferred, references undefined factory
# @command_wrapper
# async def create_location_context(
#     name: str = typer.Argument(..., help="Location context name (e.g., @home, @office)"),
#     latitude: float | None = typer.Option(None, "--lat", help="Latitude"),
#     longitude: float | None = typer.Option(None, "--lon", help="Longitude"),
#     radius: float = typer.Option(100.0, "--radius", help="Radius in meters"),
#     output: str = typer.Option("table", "--output", "-o", help="Output format"),
# ) -> None:
#     """Create a new location context."""
#     from todopro_cli.services.location_context_service import LocationContextService
#
#     strategy = get_strategy_context()
#     repo = factory.get_location_context_repository()
#     service = LocationContextService(repo)
#
#     context = await service.create_context(
#         name=name,
#         latitude=latitude,
#         longitude=longitude,
#         radius=radius,
#     )
#     format_success(f"Location context created: {name}")
#     format_output(context.model_dump(), output)
