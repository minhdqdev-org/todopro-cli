"""Create command - Create new resources."""

import typer

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.filters import FiltersAPI
from todopro_cli.services.label_service import get_label_service
from todopro_cli.services.project_service import get_project_service
from todopro_cli.services.task_service import get_task_service
from todopro_cli.utils.recurrence import resolve_rrule
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Create resources")
console = get_console()


@app.command("task")
@command_wrapper
async def create_task(
    content: str = typer.Argument(..., help="Task content"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    project: str | None = typer.Option(None, "--project", help="Project ID"),
    due: str | None = typer.Option(None, "--due", help="Due date"),
    priority: int | None = typer.Option(None, "--priority", help="Priority (1-4)"),
    labels: str | None = typer.Option(None, "--labels", help="Comma-separated labels"),
    recur: str | None = typer.Option(
        None,
        "--recur",
        help="Recurrence pattern: daily, weekdays, weekly, bi-weekly, monthly",
    ),
    recur_end: str | None = typer.Option(
        None, "--recur-end", help="Recurrence end date (YYYY-MM-DD)"
    ),
    parent: str | None = typer.Option(
        None, "--parent", help="Parent task ID (creates subtask)"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new task."""
    task_service = get_task_service()

    label_list = None
    if labels:
        label_list = [l.strip() for l in labels.split(",")]

    # Resolve recurrence pattern to RRULE
    recurrence_rule = None
    if recur:
        recurrence_rule = resolve_rrule(recur)
        if recurrence_rule is None:
            console.print(
                f"[red]Error: Unknown recurrence pattern '{recur}'. "
                f"Valid options: daily, weekdays, weekly, bi-weekly, monthly[/red]"
            )
            raise typer.Exit(1)

    task = await task_service.add_task(
        content=content,
        description=description,
        project_id=project,
        due_date=due,
        priority=priority or 4,
        labels=label_list,
        is_recurring=bool(recur),
        recurrence_rule=recurrence_rule,
        recurrence_end=recur_end,
        parent_id=parent,
    )
    format_success(f"Task created: {task.id}")
    if recur:
        console.print(f"[dim]Recurrence: {recur}[/dim]")
    if parent:
        console.print(f"[dim]Subtask of: {parent}[/dim]")
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

    project_service = get_project_service()

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
    label_service = get_label_service()

    label = await label_service.create_label(name=name, color=color)
    format_success(f"Label created: {label.id}")
    format_output(label.model_dump(), output)


@app.command("context")
@command_wrapper
async def create_context(
    name: str = typer.Argument(..., help="Context name"),
    backend: str = typer.Option(
        "sqlite", "--backend", help="Backend type (sqlite/rest)"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new storage context."""
    from todopro_cli.services.location_context_service import ContextService

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
#     storage_strategy_context = get_storage_strategy_context()
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


@app.command("filter")
@command_wrapper
async def create_filter(
    name: str = typer.Argument(..., help="Filter name"),
    color: str = typer.Option(
        "#0066CC", "--color", help="Color in hex format (e.g., #FF5733)"
    ),
    priority: str | None = typer.Option(
        None,
        "--priority",
        help="Comma-separated priority values (e.g., 3,4 for high/urgent)",
    ),
    project: str | None = typer.Option(
        None, "--project", help="Comma-separated project IDs"
    ),
    label: str | None = typer.Option(None, "--label", help="Comma-separated label IDs"),
    due_within: int | None = typer.Option(
        None, "--due-within", help="Include tasks due within N days"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a saved filter/smart view."""
    priority_list = None
    if priority:
        try:
            priority_list = [int(p.strip()) for p in priority.split(",")]
        except ValueError:
            console.print(
                "[red]Error: Priority must be comma-separated integers (1-4)[/red]"
            )
            raise typer.Exit(1)

    project_ids = [p.strip() for p in project.split(",")] if project else None
    label_ids = [l.strip() for l in label.split(",")] if label else None

    client = get_client()
    api = FiltersAPI(client)
    try:
        result = await api.create_filter(
            name=name,
            color=color,
            priority=priority_list,
            project_ids=project_ids,
            label_ids=label_ids,
            due_within_days=due_within,
        )
        format_success(f"Filter created: {result.get('name', name)}")
        format_output(result, output)
    finally:
        await client.close()
