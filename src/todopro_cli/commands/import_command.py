"""Import command — import data from files or third-party services."""

from __future__ import annotations

import asyncio
import os

import httpx
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
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

app = typer.Typer(
    cls=SuggestingGroup, help="Import data from files or third-party services"
)
console = get_console()

# Statuses the backend import job reports as terminal.
_TERMINAL_OK = {"completed", "succeeded", "success", "done", "finished"}
_TERMINAL_FAIL = {"failed", "error", "errored", "cancelled", "canceled"}


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
    include_completed: bool = typer.Option(
        False,
        "--include-completed",
        help="Also import completed tasks (recent history)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Fetch and count data without writing anything",
    ),
) -> None:
    """Import tasks, projects, and labels from Todoist.

    In a **remote** (cloud) context the import is delegated to the TodoPro
    backend for full fidelity — sections, subtasks, recurrence, comments and
    completed tasks — running as a background job with live progress. Use
    --dry-run to preview the counts the backend found before committing.

    In a **local** (SQLite) context the import runs client-side (projects,
    labels, tasks, due dates, optional completed history).

    Requires a Todoist personal API token. Set TODOIST_API_KEY in your
    environment or pass it with --api-key.

    Examples:
        todopro import todoist --api-key YOUR_TOKEN
        TODOIST_API_KEY=YOUR_TOKEN todopro import todoist
        todopro import todoist --dry-run --api-key YOUR_TOKEN
        todopro import todoist --include-completed --api-key YOUR_TOKEN
        todopro import todoist --project-prefix "" --max-tasks 200
    """
    from todopro_cli.services.config_service import (
        get_config_service,
        get_storage_strategy_context,
    )

    resolved_key = api_key or os.environ.get("TODOIST_API_KEY")
    if not resolved_key:
        format_error(
            "Todoist API key required. Use --api-key or set TODOIST_API_KEY env var."
        )
        raise typer.Exit(1)

    # Decide execution path from the active context. Remote → backend importer;
    # local/unknown → the client-side SQLite path.
    try:
        current_context = get_config_service().get_current_context()
    except (ValueError, KeyError):
        current_context = None
    is_remote = current_context is not None and current_context.type == "remote"

    if is_remote:
        await _run_remote(
            resolved_key, include_completed=include_completed, dry_run=dry_run
        )
        return

    # ---- Local (client-side SQLite) path -------------------------------
    options = TodoistImportOptions(
        project_name_prefix=project_prefix,
        max_tasks_per_project=max_tasks,
        include_completed=include_completed,
        dry_run=dry_run,
    )

    if dry_run:
        format_info("Dry-run mode — no data will be written.")
    format_info("Connecting to Todoist API…")

    service = TodoistImportService(
        TodoistClient(resolved_key), get_storage_strategy_context()
    )
    try:
        result = await service.import_all(options)
    except ValueError as exc:
        format_error(str(exc))
        raise typer.Exit(1) from exc

    _print_local_result(result, dry_run=dry_run)

    if result.has_errors:
        format_error(f"{len(result.errors)} error(s) occurred during import.")
        for err in result.errors[:10]:
            console.print(f"  [red]• {err}[/red]")
        raise typer.Exit(1)

    format_success("✓ Todoist import completed")


async def _run_remote(token: str, *, include_completed: bool, dry_run: bool) -> None:
    """Drive the backend Todoist importer (preview or background job)."""
    from todopro_cli.services.api.client import get_client

    client = get_client()
    try:
        if dry_run:
            # POST /api/v1/import/todoist/preview → {projects, sections, labels,
            # tasks, completed_tasks, comments}
            format_info("Asking the backend to preview your Todoist account…")
            try:
                response = await client.post(
                    "/v1/import/todoist/preview", json={"token": token}
                )
            except httpx.HTTPStatusError as exc:
                format_error(f"Preview failed: {_extract_error(exc.response)}")
                raise typer.Exit(1) from exc
            _print_remote_counts(response.json(), title="Import Preview (dry-run)")
            return

        # POST /api/v1/import/todoist/ → 202 {"job_id"}
        format_info("Starting Todoist import on the backend…")
        try:
            response = await client.post(
                "/v1/import/todoist/",
                json={
                    "token": token,
                    "options": {"include_completed": include_completed},
                },
            )
        except httpx.HTTPStatusError as exc:
            format_error(f"Import failed to start: {_extract_error(exc.response)}")
            raise typer.Exit(1) from exc

        payload = response.json()
        job_id = payload.get("job_id")
        if not job_id:
            # Small imports may return the final summary synchronously.
            _print_remote_counts(payload.get("counts", payload), title="Import Results")
            format_success("✓ Todoist import completed")
            return

        # Poll GET /api/v1/import/todoist/jobs/<id>/ until terminal.
        final: dict = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task_id = progress.add_task("Importing from Todoist…", total=None)
            while True:
                await asyncio.sleep(1.5)
                try:
                    poll = await client.get(f"/v1/import/todoist/jobs/{job_id}/")
                except httpx.HTTPStatusError as exc:
                    format_error(
                        f"Failed to poll import job: {_extract_error(exc.response)}"
                    )
                    raise typer.Exit(1) from exc

                data = poll.json()
                status = str(data.get("status", "")).lower()
                phase = data.get("phase") or status or "working"
                progress.update(
                    task_id, description=f"Importing from Todoist — {phase}…"
                )

                if status in _TERMINAL_OK or status in _TERMINAL_FAIL:
                    final = data
                    break

        _print_remote_counts(final.get("counts", {}), title="Import Results")

        dropped = final.get("dropped_pro_fields") or []
        if dropped:
            console.print(
                "\n[yellow]Some Pro-only fields were skipped "
                "(upgrade to keep them):[/yellow]"
            )
            for item in dropped if isinstance(dropped, list) else [dropped]:
                console.print(f"  [yellow]• {item}[/yellow]")

        errors = final.get("errors") or []
        if errors:
            format_error(f"{len(errors)} error(s) occurred during import.")
            for err in errors[:10]:
                console.print(f"  [red]• {err}[/red]")

        if str(final.get("status", "")).lower() in _TERMINAL_FAIL:
            raise typer.Exit(1)

        format_success("✓ Todoist import completed")
    finally:
        await client.close()


def _extract_error(response: httpx.Response) -> str:
    """Best-effort extraction of an error message from an API response."""
    try:
        data = response.json()
    except Exception:
        return response.text or f"HTTP {response.status_code}"
    err = data.get("error")
    if isinstance(err, dict):
        return err.get("message") or str(err)
    if isinstance(err, str):
        return err
    return data.get("detail") or str(data)


def _print_remote_counts(counts: dict, *, title: str) -> None:
    """Render the backend's per-entity counts as a Rich table."""
    table = Table(title=title, show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right", style="green")

    for key in (
        "projects",
        "sections",
        "labels",
        "tasks",
        "completed_tasks",
        "comments",
    ):
        if key in counts:
            label = key.replace("_", " ").title()
            table.add_row(label, str(counts.get(key, 0)))

    console.print(table)


def _print_local_result(result, *, dry_run: bool) -> None:
    """Render a Rich table summarising local import counts."""
    title = "Import Preview (dry-run)" if dry_run else "Import Results"
    table = Table(title=title, show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Created", justify="right", style="green")
    table.add_column("Skipped", justify="right", style="yellow")

    table.add_row(
        "Projects", str(result.projects_created), str(result.projects_skipped)
    )
    table.add_row("Labels", str(result.labels_created), str(result.labels_skipped))
    table.add_row("Tasks", str(result.tasks_created), str(result.tasks_skipped))
    if result.tasks_completed:
        table.add_row("Completed tasks", str(result.tasks_completed), "0")

    console.print(table)
