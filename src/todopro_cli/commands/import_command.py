"""Import command — import data from files or third-party services."""

from __future__ import annotations

import os

import typer
from rich.table import Table

from todopro_cli.services.todoist import (
    TodoistClient,
    TodoistImportOptions,
    TodoistImportService,
)
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_info, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Import data from files or third-party services")
console = get_console()


@app.command("data")
@command_wrapper
async def import_data(
    input_file: str = typer.Argument(..., help="Input file path"),
    merge: bool = typer.Option(False, "--merge", help="Merge with existing data"),
) -> None:
    """Import data from JSON file."""
    from todopro_cli.services.config_service import get_storage_strategy_context
    from todopro_cli.services.data_service import DataService

    storage_strategy_context = get_storage_strategy_context()
    data_service = DataService(storage_strategy_context)

    await data_service.import_data(input_file, merge=merge)
    format_success(f"Data imported from: {input_file}")


@app.command("todoist")
@command_wrapper
async def import_todoist(
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Todoist personal API token (or set TODOIST_API_KEY env var)",
        envvar="TODOIST_API_KEY",
    ),
    project_prefix: str = typer.Option(
        "[Todoist]",
        "--project-prefix",
        help="Prefix added to every imported project name to avoid conflicts",
    ),
    max_tasks: int = typer.Option(
        500,
        "--max-tasks",
        help="Maximum tasks to import per project",
        min=1,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Fetch and count data without writing anything",
    ),
) -> None:
    """Import tasks, projects, and labels from Todoist using the v1 API.

    Requires a Todoist personal API token. Set TODOIST_API_KEY in your
    environment or pass it with --api-key.

    Examples:
        todopro import todoist --api-key YOUR_TOKEN
        TODOIST_API_KEY=YOUR_TOKEN todopro import todoist
        todopro import todoist --dry-run --api-key YOUR_TOKEN
        todopro import todoist --project-prefix "" --max-tasks 200
    """
    from todopro_cli.services.config_service import get_storage_strategy_context

    resolved_key = api_key or os.environ.get("TODOIST_API_KEY")
    if not resolved_key:
        format_error(
            "Todoist API key required. Use --api-key or set TODOIST_API_KEY env var."
        )
        raise typer.Exit(1)

    options = TodoistImportOptions(
        project_name_prefix=project_prefix,
        max_tasks_per_project=max_tasks,
        dry_run=dry_run,
    )

    if dry_run:
        format_info("Dry-run mode — no data will be written.")

    format_info("Connecting to Todoist API…")

    client = TodoistClient(resolved_key)
    storage = get_storage_strategy_context()
    service = TodoistImportService(client, storage)

    try:
        result = await service.import_all(options)
    except ValueError as exc:
        format_error(str(exc))
        raise typer.Exit(1) from exc

    _print_import_result(result, dry_run=dry_run)

    if result.has_errors:
        format_error(f"{len(result.errors)} error(s) occurred during import.")
        for err in result.errors[:10]:
            console.print(f"  [red]• {err}[/red]")
        raise typer.Exit(1)

    format_success("✓ Todoist import completed")


def _print_import_result(result, *, dry_run: bool) -> None:
    """Render a Rich table summarising import counts."""
    title = "Import Preview (dry-run)" if dry_run else "Import Results"
    table = Table(title=title, show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Created", justify="right", style="green")
    table.add_column("Skipped", justify="right", style="yellow")

    table.add_row("Projects", str(result.projects_created), str(result.projects_skipped))
    table.add_row("Labels", str(result.labels_created), str(result.labels_skipped))
    table.add_row("Tasks", str(result.tasks_created), str(result.tasks_skipped))

    console.print(table)

