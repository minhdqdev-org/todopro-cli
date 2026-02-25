"""Command 'describe' of todopro-cli"""

import asyncio

import typer

from todopro_cli.services.project_service import ProjectService
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output
from todopro_cli.utils.uuid_utils import resolve_project_uuid

from .decorators import command_wrapper

app = typer.Typer()
console = get_console()


def run_async(func, *args, **kwargs):
    """Run an async function in a synchronous context."""
    return asyncio.run(func(*args, **kwargs))


@app.command()
@command_wrapper
def describe(
    resource_type: str = typer.Argument(..., help="Resource type (project)"),
    resource_id: str = typer.Argument(..., help="Resource ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Describe a resource in detail."""
    if resource_type.lower() == "project":
        project_id = resource_id
        storage_strategy_context = get_storage_strategy_context()
        project_repo = storage_strategy_context.project_repository
        project_service = ProjectService(project_repo)

        # Resolve partial UUID prefix to full UUID
        project_id = run_async(resolve_project_uuid, project_id, project_repo)

        project = run_async(project_service.get_project, project_id)

        console.print("\n[bold cyan]Project Details:[/bold cyan]")
        format_output(project.model_dump(), output)

        # Get stats using service layer
        stats = run_async(project_service.get_project_stats, project_id)

        console.print("\n[bold]Statistics:[/bold]")
        for key, label in [
            ("total_tasks", "Total tasks"),
            ("completed_tasks", "Completed"),
            ("pending_tasks", "Pending"),
            ("overdue_tasks", "Overdue"),
        ]:
            console.print(f"  {label}: {stats.get(key, 0)}")

        if "completion_rate" in stats:
            console.print(f"  Completion rate: {stats['completion_rate']}%")
    else:
        console.print(f"[red]Unknown resource type: {resource_type}[/red]")
        raise typer.Exit(1)
