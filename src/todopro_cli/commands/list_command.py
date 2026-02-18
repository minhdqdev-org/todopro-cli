"""List command - List resources (tasks, projects, labels, etc.)."""

import typer
from rich.console import Console

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.task_service import TaskService
from todopro_cli.services.project_service import ProjectService
from todopro_cli.services.label_service import LabelService
from todopro_cli.services.cache_service import get_background_cache
from todopro_cli.utils.ui.formatters import format_output
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="List resources")
console = Console()


@app.command("tasks")
@command_wrapper
async def list_tasks(
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    project: str | None = typer.Option(None, "--project", help="Filter by project ID"),
    priority: int | None = typer.Option(None, "--priority", help="Filter by priority"),
    search: str | None = typer.Option(None, "--search", help="Search tasks"),
    limit: int = typer.Option(30, "--limit", help="Limit results"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    output: str = typer.Option("pretty", "--output", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """List tasks."""
    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    tasks = await task_service.list_tasks(
        status=status,
        project_id=project,
        priority=priority,
        search=search,
        limit=limit,
        offset=offset,
    )

    # Filter out tasks being completed in background
    cache = get_background_cache()
    completing_tasks = set(cache.get_completing_tasks())

    if completing_tasks:
        tasks = [
            task
            for task in tasks
            if not any(task.id.endswith(short_id) for short_id in completing_tasks)
        ]

    result = {"tasks": [t.model_dump() for t in tasks]}
    format_output(result, output, compact=compact)


@app.command("projects")
@command_wrapper
async def list_projects(
    include_archived: bool = typer.Option(
        False, "--archived", help="Include archived projects"
    ),
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all projects."""
    strategy = get_strategy_context()
    project_repo = strategy.project_repository
    project_service = ProjectService(project_repo)

    projects = await project_service.list_projects(include_archived=include_archived)
    result = {"projects": [p.model_dump() for p in projects]}
    format_output(result, output)


@app.command("labels")
@command_wrapper
async def list_labels(
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all labels."""
    strategy = get_strategy_context()
    label_repo = strategy.label_repository
    label_service = LabelService(label_repo)

    labels = await label_service.list_labels()
    result = {"labels": [l.model_dump() for l in labels]}
    format_output(result, output)


@app.command("contexts")
@command_wrapper
async def list_contexts() -> None:
    """List all storage contexts (local/remote)."""
    from todopro_cli.services.config_service import get_config_service
    
    config_service = get_config_service()
    contexts = config_service.list_contexts()
    current_context = config_service.get_current_context()

    console.print("\n[bold]Available Contexts:[/bold]")
    for ctx in contexts:
        current = "✓" if ctx.name == current_context.name else " "
        type_color = "cyan" if ctx.type == "local" else "magenta"
        console.print(f"  [{current}] [bold]{ctx.name}[/bold] - [{type_color}]{ctx.type}[/{type_color}]")
        console.print(f"      Source: {ctx.source}")
        if ctx.description:
            console.print(f"      {ctx.description}")
    console.print()


@app.command("location-contexts")
@command_wrapper
async def list_location_contexts(
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all location contexts (@home, @office, etc.)."""
    from todopro_cli.services.location_context_service import LocationContextService

    strategy = get_strategy_context()
    repo = factory.get_location_context_repository()
    service = LocationContextService(repo)

    contexts = await service.list_contexts()
    result = {"contexts": [c.model_dump() for c in contexts]}
    format_output(result, output)


@app.command("goals")
@command_wrapper
async def list_goals(
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all focus goals."""
    from todopro_cli.services.focus_service import FocusService

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    goals = await service.list_goals()
    result = {"goals": [g.model_dump() for g in goals]}
    format_output(result, output)


@app.command("achievements")
@command_wrapper
async def list_achievements(
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all achievements."""
    from todopro_cli.services.achievement_service import AchievementService

    strategy = get_strategy_context()
    repo = factory.get_achievement_repository()
    service = AchievementService(repo)

    achievements = await service.list_achievements()
    result = {"achievements": [a.model_dump() for a in achievements]}
    format_output(result, output)


@app.command("focus-templates")
@command_wrapper
async def list_focus_templates(
    output: str = typer.Option("table", "--output", help="Output format"),
) -> None:
    """List all focus session templates."""
    from todopro_cli.services.focus_service import FocusService

    strategy = get_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    templates = await service.list_templates()
    result = {"templates": [t.model_dump() for t in templates]}
    format_output(result, output)
