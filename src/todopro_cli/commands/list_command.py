"""List command - List resources (tasks, projects, labels, etc.)."""

import typer

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.filters import FiltersAPI
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.services.cache_service import get_background_cache
from todopro_cli.services.label_service import LabelService
from todopro_cli.services.project_service import ProjectService
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="List resources")
console = get_console()


@app.command("tasks")
@command_wrapper
async def list_tasks(
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    project: str | None = typer.Option(None, "--project", help="Filter by project ID"),
    priority: int | None = typer.Option(None, "--priority", help="Filter by priority"),
    search: str | None = typer.Option(None, "--search", help="Search tasks"),
    recurring: bool = typer.Option(
        False, "--recurring", help="Show only recurring tasks"
    ),
    limit: int = typer.Option(30, "--limit", help="Limit results (default 30)"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
) -> None:
    """List tasks."""
    import sys

    if json_opt:
        output = "json"

    storage_strategy_context = get_storage_strategy_context()
    task_repo = strategy_context.task_repository
    task_service = TaskService(task_repo)

    # When using default limit, check total count first and warn if large
    _BIG_TASK_THRESHOLD = 100
    if limit <= _BIG_TASK_THRESHOLD:
        # Quick count with a high limit to detect large sets
        count_check = await task_service.list_tasks(
            status=status,
            project_id=project,
            priority=priority,
            search=search,
            limit=_BIG_TASK_THRESHOLD + 1,
            offset=0,
        )
        total = len(count_check)
        if (
            total > _BIG_TASK_THRESHOLD
            and sys.stdin.isatty()
            and output not in ("json",)
        ):
            console.print(
                f"[yellow]Found {total}+ tasks. Showing first {limit}.[/yellow]"
            )
            console.print(
                f"[dim]Use --limit {total} to show all, or --limit N for a different amount.[/dim]"
            )

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

    # Apply recurring filter client-side (API may not support it for all backends)
    if recurring:
        tasks = [t for t in tasks if getattr(t, "is_recurring", False)]

    result = {"tasks": [t.model_dump() for t in tasks]}
    format_output(result, output, compact=compact)


@app.command("projects")
@command_wrapper
async def list_projects(
    include_archived: bool = typer.Option(
        False, "--archived", help="Include archived projects"
    ),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """List all projects."""
    if json_opt:
        output = "json"

    storage_strategy_context = get_storage_strategy_context()
    project_repo = storage_strategy_context.project_repository
    project_service = ProjectService(project_repo)

    projects = await project_service.list_projects(
        is_archived=None if include_archived else False
    )
    result = {"projects": [p.model_dump() for p in projects]}
    format_output(result, output)


@app.command("labels")
@command_wrapper
async def list_labels(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """List all labels."""
    storage_strategy_context = get_storage_strategy_context()
    label_repo = storage_strategy_context.label_repository
    label_service = LabelService(label_repo)

    labels = await label_service.list_labels()
    result = {"labels": [l.model_dump() for l in labels]}
    format_output(result, output)


@app.command("contexts")
@command_wrapper
async def list_contexts(
    limit: int = typer.Option(
        10, "--limit", "-n", help="Maximum number of contexts to show"
    ),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """List all storage contexts (local/remote)."""
    from todopro_cli.services.config_service import get_config_service

    if json_opt:
        output = "json"

    config_service = get_config_service()
    all_contexts = config_service.list_contexts()
    current_context = config_service.get_current_context()

    contexts = all_contexts[:limit]

    if output == "json":
        result = {
            "contexts": [
                {
                    "name": ctx.name,
                    "type": ctx.type,
                    "source": ctx.source,
                    "description": ctx.description or "",
                    "is_current": ctx.name == current_context.name,
                }
                for ctx in contexts
            ]
        }
        format_output(result, "json")
        return

    console.print("\n[bold]Available Contexts:[/bold]")
    for ctx in contexts:
        current = "✓" if ctx.name == current_context.name else " "
        type_color = "cyan" if ctx.type == "local" else "magenta"
        console.print(
            f"  [{current}] [bold]{ctx.name}[/bold] - [{type_color}]{ctx.type}[/{type_color}]"
        )
        console.print(f"      Source: {ctx.source}")
        if ctx.description:
            console.print(f"      {ctx.description}")
    if len(all_contexts) > limit:
        console.print(
            f"\n[dim]Showing {limit} of {len(all_contexts)} contexts. Use --limit N for more.[/dim]"
        )
    console.print()


@app.command("location-contexts")
@command_wrapper
async def list_location_contexts(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """List all location contexts (@home, @office, etc.)."""
    from todopro_cli.services.location_context_service import LocationContextService

    storage_strategy_context = get_storage_strategy_context()
    repo = factory.get_location_context_repository()
    service = LocationContextService(repo)

    contexts = await service.list_contexts()
    result = {"contexts": [c.model_dump() for c in contexts]}
    format_output(result, output)


@app.command("goals")
@command_wrapper
async def list_goals(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """List all focus goals."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    goals = await service.list_goals()
    result = {"goals": [g.model_dump() for g in goals]}
    format_output(result, output)


@app.command("achievements")
@command_wrapper
async def list_achievements(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """List all achievements."""
    from todopro_cli.services.achievement_service import AchievementService

    storage_strategy_context = get_storage_strategy_context()
    repo = factory.get_achievement_repository()
    service = AchievementService(repo)

    achievements = await service.list_achievements()
    result = {"achievements": [a.model_dump() for a in achievements]}
    format_output(result, output)


@app.command("focus-templates")
@command_wrapper
async def list_focus_templates(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """List all focus session templates."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    templates = await service.list_templates()
    result = {"templates": [t.model_dump() for t in templates]}
    format_output(result, output)


# Singular aliases
app.command("task")(list_tasks)
app.command("project")(list_projects)
app.command("label")(list_labels)
app.command("context")(list_contexts)


@app.command("filters")
@command_wrapper
async def list_filters(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """List saved filters/smart views."""
    client = get_client()
    api = FiltersAPI(client)
    try:
        filters = await api.list_filters()
        result = {"filters": filters}
        format_output(result, output)
    finally:
        await client.close()


app.command("filter")(list_filters)


@app.command("subtasks")
@command_wrapper
async def list_subtasks(
    parent_id: str = typer.Argument(..., help="Parent task ID"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
) -> None:
    """List subtasks of a task."""
    client = get_client()
    api = TasksAPI(client)
    try:
        result = await api.list_subtasks(parent_id)
    finally:
        await client.close()

    tasks = (
        result
        if isinstance(result, list)
        else result.get("tasks", result.get("results", []))
    )
    if not tasks:
        console.print(f"[yellow]No subtasks found for task {parent_id[:8]}…[/yellow]")
        return
    format_output({"tasks": tasks}, output)
