"""Data management commands (import, export, purge)."""

import asyncio
import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.prompt import Confirm, Prompt
from rich.table import Table

from todopro_cli.models import ProjectFilters, TaskFilters
from todopro_cli.services.api.client import get_client
from todopro_cli.services.config_service import (
    get_config_service,
    get_storage_strategy_context,
)
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import (
    format_error,
    format_info,
    format_success,
    format_warning,
)

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Data management commands")
console = get_console()

# How often to poll a queued `--archive` export job.
POLL_INTERVAL_SECONDS = 2.0


async def _export_archive(output: str | None, timeout: int) -> None:
    """Run the complete (ZIP) export: enqueue, poll, download.

    `GET /v1/export/data` only covers tasks, projects, labels and contexts.
    `POST /v1/export/archive` builds the full account picture (26 model
    groups) plus the user's uploaded files, off-request, and returns a job id
    to poll — a heavy account cannot finish inside the proxy timeout.
    """
    config_svc = get_config_service()
    try:
        if config_svc.config.get_current_context().type == "local":
            format_error(
                "--archive needs a remote context (the archive is built "
                "server-side). Use a plain `todopro data export` locally."
            )
            raise typer.Exit(1)
    except (ValueError, KeyError) as e:
        format_error("--archive needs a remote context; no remote context is active.")
        raise typer.Exit(1) from e

    client = get_client()
    try:
        format_info("Requesting a complete export archive...")
        # `request` is annotated as returning httpx.Response but every caller in
        # this module treats it as the decoded JSON body; keep that convention.
        queued: Any = await client.request("POST", "/v1/export/archive") or {}
        job_id = queued.get("job_id")
        if not job_id:
            format_error("Server did not return an export job id")
            raise typer.Exit(1)

        format_info(f"Export queued (job {job_id}). Waiting for it to finish...")

        deadline = asyncio.get_event_loop().time() + timeout
        download_url: str | None = None
        while True:
            # `ExportArchiveStatusView` returns the FLAT `_serialize_job` shape:
            # a top-level string `status` ("pending"/"running"/"ready"/"failed"/
            # "expired") and, only on a `ready` job, a top-level `download_url`.
            # There is no `ready` boolean and no nested `result` wrapper — the SPA
            # consumes this same flat shape.
            status: Any = (
                await client.request("GET", f"/v1/export/archive/{job_id}") or {}
            )
            job_status = status.get("status")
            if job_status == "ready":
                download_url = status.get("download_url")
                if not download_url:
                    format_error(
                        "Export is ready but the server returned no download URL."
                    )
                    raise typer.Exit(1)
                break
            if job_status in ("failed", "expired"):
                error = status.get("error") or job_status
                format_error(
                    f"Export failed on the server ({error}). Please try again."
                )
                raise typer.Exit(1)
            if asyncio.get_event_loop().time() >= deadline:
                format_error(
                    f"Export did not finish within {timeout}s. It may still be "
                    f"running — poll it later with job id {job_id}."
                )
                raise typer.Exit(1)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

        format_info("Downloading archive...")
        content = await client.download(download_url)
    finally:
        await client.close()

    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = f"todopro-export-{timestamp}.zip"
    output_path = Path(output)
    output_path.write_bytes(content)

    format_success(
        f"✓ Complete export ({len(content) / 1024 / 1024:.1f} MiB) written to: "
        f"{output_path.absolute()}"
    )
    format_info("The ZIP contains data.json plus your uploaded attachments.")


@app.command("export")
@command_wrapper
def export_data(
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: todopro-export-{timestamp}.json)",
    ),
    compress: bool = typer.Option(
        False,
        "--compress",
        "-z",
        help="Compress output with gzip",
    ),
    archive: bool = typer.Option(
        False,
        "--archive",
        "-a",
        help=(
            "Complete export: a ZIP with data.json plus your uploaded "
            "attachments (remote contexts only). Generated server-side."
        ),
    ),
    timeout: int = typer.Option(
        600,
        "--timeout",
        help="Seconds to wait for an --archive export to finish",
    ),
) -> None:
    """
    Export your data.

    By default this exports tasks, projects, labels and contexts as JSON.
    Use --archive for the *complete* export (every record group plus your
    uploaded attachments) as a ZIP — this is the one to use for a genuine
    data-portability / GDPR copy of your account.

    Examples:
        todopro data export
        todopro data export --output backup.json
        todopro data export --compress
        todopro data export --archive --output my-todopro-data.zip
    """

    if archive:
        asyncio.run(_export_archive(output, timeout))
        return

    async def do_export() -> None:
        # Detect context type
        config_svc = get_config_service()
        try:
            current_context = config_svc.config.get_current_context()
            is_local = current_context.type == "local"
        except (ValueError, KeyError):
            # No context, assume local
            is_local = True

        format_info("Exporting your data...")

        # Export from local SQLite or remote API
        if is_local:
            # Local export - read from SQLite repositories
            storage_strategy_context = get_storage_strategy_context()

            # Fetch all data
            tasks = await storage_strategy_context.task_repository.list_all(
                TaskFilters()
            )
            projects = await storage_strategy_context.project_repository.list_all(
                ProjectFilters()
            )
            labels = await storage_strategy_context.label_repository.list_all()

            # Get contexts from config (not in database)
            contexts = config_svc.config.contexts

            # Check E2EE status
            e2ee_enabled = (
                config_svc.config.e2ee.enabled if config_svc.config.e2ee else False
            )

            # Build response matching remote API format
            response = {
                "stats": {
                    "tasks_count": len(tasks),
                    "projects_count": len(projects),
                    "labels_count": len(labels),
                    "contexts_count": len(contexts),
                },
                "encryption": {"enabled": e2ee_enabled},
                "data": {
                    "tasks": [task.model_dump(mode="json") for task in tasks],
                    "projects": [
                        project.model_dump(mode="json") for project in projects
                    ],
                    "labels": [label.model_dump(mode="json") for label in labels],
                    "contexts": [
                        context.model_dump(mode="json") for context in contexts
                    ],
                },
            }
        else:
            # Remote export - call API
            client = get_client()
            params = {}
            if compress:
                params["compress"] = "true"
            # NOTE: the backend mounts tasks.urls under `api/v1/` and the
            # client's base_url already ends in `/api`, so the path here must
            # be `/v1/...`. It used to be `/api/export/data`, which resolved
            # to `/api/api/export/data` and 404'd on every remote export.
            response = await client.request("GET", "/v1/export/data", params=params)
            await client.close()

        # Determine output filename
        if output is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            extension = ".json.gz" if compress else ".json"
            filename = f"todopro-export-{timestamp}{extension}"
        else:
            filename = output

        # Write to file
        output_path = Path(filename)

        if compress and isinstance(response, bytes):
            # Response is already gzipped
            output_path.write_bytes(response)
        elif isinstance(response, dict):
            # JSON response - optionally compress
            json_str = json.dumps(response, indent=2)
            if compress:
                output_path.write_bytes(gzip.compress(json_str.encode("utf-8")))
            else:
                output_path.write_text(json_str, encoding="utf-8")
        else:
            format_error("Unexpected response format")
            raise typer.Exit(1)

        # Show stats
        if isinstance(response, dict):
            stats = response.get("stats", {})

            table = Table(title="Export Summary", show_header=True)
            table.add_column("Type", style="cyan")
            table.add_column("Count", justify="right", style="green")

            table.add_row("Tasks", str(stats.get("tasks_count", 0)))
            table.add_row("Projects", str(stats.get("projects_count", 0)))
            table.add_row("Labels", str(stats.get("labels_count", 0)))
            table.add_row("Contexts", str(stats.get("contexts_count", 0)))

            console.print(table)

            # Show encryption status
            encryption = response.get("encryption", {})
            if encryption.get("enabled"):
                format_info("🔐 Data includes encrypted fields")

        format_success(f"✓ Data exported to: {output_path.absolute()}")

    asyncio.run(do_export())


@app.command("import")
@command_wrapper
def import_data(
    file: str = typer.Argument(..., help="JSON file to import"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Import data from JSON file (exported via 'export' command).

    This will merge imported data with your existing data.
    Existing items with the same name will be skipped.

    Examples:
        todopro data import backup.json
        todopro data import backup.json --yes
    """

    file_path = Path(file)

    # Validate file exists
    if not file_path.exists():
        format_error(f"File not found: {file}")
        raise typer.Exit(5)  # Exit code 5: Resource not found

    # Read and parse file
    try:
        if file_path.suffix == ".gz":
            with gzip.open(file_path, "rt") as f:
                data = json.load(f)
        else:
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)
    except json.JSONDecodeError as e:
        format_error(f"Invalid JSON file: {str(e)}")
        raise typer.Exit(2) from e  # Exit code 2: Invalid arguments
    except Exception as e:
        format_error(f"Failed to read file: {str(e)}")
        raise typer.Exit(1) from e

    # Show preview
    stats = data.get("stats", {})

    table = Table(title="Import Preview", show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right", style="yellow")

    table.add_row(
        "Tasks",
        str(stats.get("tasks_count", len(data.get("data", {}).get("tasks", [])))),
    )
    table.add_row(
        "Projects",
        str(stats.get("projects_count", len(data.get("data", {}).get("projects", [])))),
    )
    table.add_row(
        "Labels",
        str(stats.get("labels_count", len(data.get("data", {}).get("labels", [])))),
    )
    table.add_row(
        "Contexts",
        str(stats.get("contexts_count", len(data.get("data", {}).get("contexts", [])))),
    )

    console.print(table)

    format_info("Note: Existing items with the same name will be skipped")

    # Confirm import
    if not yes and not Confirm.ask("Do you want to import this data?"):
        format_info("Import cancelled")
        raise typer.Exit(0)

    async def do_import() -> None:
        # Detect context type
        config_svc = get_config_service()
        try:
            current_context = config_svc.config.get_current_context()
            is_local = current_context.type == "local"
        except (ValueError, KeyError):
            # No context, assume local
            is_local = True

        format_info("Importing data...")

        # Import to local SQLite or remote API
        if is_local:
            # Local import - write to SQLite repositories
            storage_strategy_context = get_storage_strategy_context()

            # Track import results
            summary = {
                "projects": "0 created, 0 skipped",
                "labels": "0 created, 0 skipped",
                "contexts": "0 created, 0 skipped",
                "tasks": "0 created, 0 skipped",
            }
            details = {
                "projects": {"errors": []},
                "labels": {"errors": []},
                "tasks": {"errors": []},
            }

            import_data_payload = data.get("data", {})

            # The export (`ExportDataView`) writes each task with a `project_id`
            # (the *exported* project's id) and a `labels` list (exported label
            # ids). Those ids are meaningless locally, so as we create/dedupe
            # projects and labels we record exported-id -> local-id maps and use
            # them to re-link tasks. This preserves task->project and task->label
            # associations across an export/import round-trip.
            project_id_map: dict[str, str] = {}
            label_id_map: dict[str, str] = {}

            # Import projects first (tasks may reference them)
            projects_created = 0
            projects_skipped = 0
            for project_data in import_data_payload.get("projects", []):
                try:
                    # Check if project already exists by name
                    existing = (
                        await storage_strategy_context.project_repository.list_all(
                            ProjectFilters(search=project_data.get("name"))
                        )
                    )
                    # Filter by exact name match (search is substring search)
                    matching = [
                        p for p in existing if p.name == project_data.get("name")
                    ]
                    exported_id = project_data.get("id")
                    if matching:
                        # Map the exported id onto the existing local project so
                        # tasks that referenced it still link after dedupe.
                        if exported_id is not None:
                            project_id_map[str(exported_id)] = matching[0].id
                        projects_skipped += 1
                        continue

                    # Create project (excluding id to let DB generate new one)
                    from todopro_cli.models import ProjectCreate

                    project_create = ProjectCreate(
                        name=project_data["name"],
                        color=project_data.get("color"),
                        is_favorite=project_data.get("is_favorite", False),
                    )
                    created_project = (
                        await storage_strategy_context.project_repository.create(
                            project_create
                        )
                    )
                    if exported_id is not None:
                        project_id_map[str(exported_id)] = created_project.id
                    projects_created += 1
                except Exception as e:
                    details["projects"]["errors"].append(
                        f"{project_data.get('name', 'Unknown')}: {str(e)}"
                    )

            summary["projects"] = (
                f"{projects_created} created, {projects_skipped} skipped"
            )

            # Import labels
            labels_created = 0
            labels_skipped = 0
            for label_data in import_data_payload.get("labels", []):
                try:
                    # Check if label already exists by name
                    existing = (
                        await storage_strategy_context.label_repository.list_all()
                    )
                    matching_labels = [
                        lbl for lbl in existing if lbl.name == label_data.get("name")
                    ]
                    exported_label_id = label_data.get("id")
                    if matching_labels:
                        if exported_label_id is not None:
                            label_id_map[str(exported_label_id)] = matching_labels[0].id
                        labels_skipped += 1
                        continue

                    # Create label
                    from todopro_cli.models import LabelCreate

                    label_create = LabelCreate(
                        name=label_data["name"],
                        color=label_data.get("color"),
                    )
                    created_label = (
                        await storage_strategy_context.label_repository.create(
                            label_create
                        )
                    )
                    if exported_label_id is not None:
                        label_id_map[str(exported_label_id)] = created_label.id
                    labels_created += 1
                except Exception as e:
                    details["labels"]["errors"].append(
                        f"{label_data.get('name', 'Unknown')}: {str(e)}"
                    )

            summary["labels"] = f"{labels_created} created, {labels_skipped} skipped"

            # Import tasks
            tasks_created = 0
            tasks_skipped = 0
            for task_data in import_data_payload.get("tasks", []):
                try:
                    # Check if task already exists by content
                    existing = await storage_strategy_context.task_repository.list_all(
                        TaskFilters(search=task_data.get("content"))
                    )
                    # Skip if exact content match found
                    if any(t.content == task_data.get("content") for t in existing):
                        tasks_skipped += 1
                        continue

                    # Create task, re-linking project + labels via the id maps
                    # built above (the export emits `project_id` + `labels`).
                    from todopro_cli.models import TaskCreate

                    exported_project_id = task_data.get("project_id")
                    project_id = (
                        project_id_map.get(str(exported_project_id))
                        if exported_project_id is not None
                        else None
                    )
                    local_label_ids = [
                        label_id_map[str(lid)]
                        for lid in task_data.get("labels", [])
                        if str(lid) in label_id_map
                    ]

                    task_create = TaskCreate(
                        content=task_data["content"],
                        description=task_data.get("description"),
                        priority=task_data.get("priority", 4),
                        project_id=project_id,
                        labels=local_label_ids,
                    )
                    await storage_strategy_context.task_repository.add(task_create)
                    tasks_created += 1
                except Exception as e:
                    details["tasks"]["errors"].append(
                        f"{task_data.get('content', 'Unknown')[:30]}: {str(e)}"
                    )

            summary["tasks"] = f"{tasks_created} created, {tasks_skipped} skipped"

            # Contexts are handled by ConfigService (not in DB)
            summary["contexts"] = "N/A (contexts not imported to local)"

            # Build response matching remote API format
            response = {
                "summary": summary,
                "details": details,
            }
        else:
            # Remote import - call API
            client = get_client()
            response = await client.request("POST", "/v1/import/data", json=data)
            await client.close()

        # Show results
        if isinstance(response, dict):
            summary = response.get("summary", {})

            table = Table(title="Import Results", show_header=True)
            table.add_column("Type", style="cyan")
            table.add_column("Result", style="green")

            table.add_row("Projects", summary.get("projects", "N/A"))
            table.add_row("Labels", summary.get("labels", "N/A"))
            table.add_row("Contexts", summary.get("contexts", "N/A"))
            table.add_row("Tasks", summary.get("tasks", "N/A"))

            console.print(table)

            # Show errors if any
            details = response.get("details", {})
            total_errors = sum(len(d.get("errors", [])) for d in details.values())

            if total_errors > 0:
                format_warning(f"⚠ {total_errors} error(s) occurred during import")
                for resource_type, resource_details in details.items():
                    errors = resource_details.get("errors", [])
                    if errors:
                        format_error(f"\n{resource_type.capitalize()} errors:")
                        for error in errors[:5]:  # Show first 5 errors
                            console.print(f"  - {error}")
                        if len(errors) > 5:
                            console.print(f"  ... and {len(errors) - 5} more")

            format_success("✓ Import completed")

    asyncio.run(do_import())


@app.command("purge")
@command_wrapper
def purge_data(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what would be deleted without actually deleting",
    ),
) -> None:
    """
    Delete ALL your data (tasks, projects, labels, contexts, encryption keys).

    ⚠️  WARNING: This action CANNOT be undone!

    You should export your data first:
        todopro data export --output backup.json

    Examples:
        todopro data purge --dry-run  # Preview only
        todopro data purge             # Actually delete
    """

    # Get user info
    config_manager = get_config_service()
    credentials = config_manager.load_credentials()
    user_email = credentials.get("email", "your email")

    async def do_purge() -> None:
        client = get_client()

        if dry_run:
            format_info("Running in dry-run mode (no data will be deleted)...")
            params = {"dry_run": "true"}
            payload = {"confirm": "DELETE", "username": user_email}

            response = await client.request(
                "POST", "/v1/purge/data", params=params, json=payload
            )

            if isinstance(response, dict):
                items = response.get("items_to_delete", {})

                table = Table(
                    title="Dry Run - Items That Would Be Deleted", show_header=True
                )
                table.add_column("Type", style="cyan")
                table.add_column("Count", justify="right", style="red")

                table.add_row("Tasks", str(items.get("tasks", 0)))
                table.add_row("Projects", str(items.get("projects", 0)))
                table.add_row("Labels", str(items.get("labels", 0)))
                table.add_row("Contexts", str(items.get("contexts", 0)))
                table.add_row(
                    "Total", str(response.get("total_items", 0)), style="bold red"
                )

                console.print(table)
                format_info("This was a dry run. No data was deleted.")

            await client.close()
            return

        # Actual purge - show warning
        format_warning("⚠️  WARNING: You are about to delete ALL your data!")
        format_warning("⚠️  This action CANNOT be undone!")
        console.print()

        # First confirmation: explain what will be deleted
        format_info("The following will be permanently deleted:")
        console.print("  • All tasks")
        console.print("  • All projects")
        console.print("  • All labels")
        console.print("  • All contexts")
        console.print("  • All encryption keys")
        console.print()

        if not Confirm.ask("Do you want to continue?", default=False):
            format_info("Purge cancelled")
            raise typer.Exit(0)

        # Second confirmation: type username
        console.print()
        format_warning("Please type your email address to confirm:")
        typed_email = Prompt.ask("Email")

        if typed_email != user_email:
            format_error("Email does not match. Purge cancelled.")
            raise typer.Exit(0)

        # Third confirmation: final warning
        console.print()
        format_warning("FINAL WARNING: All your data will be permanently deleted!")
        if not Confirm.ask("Are you absolutely sure?", default=False):
            format_info("Purge cancelled")
            raise typer.Exit(0)

        # Perform purge
        format_info("Deleting all data...")

        payload = {"confirm": "DELETE", "username": user_email}

        response = await client.request("POST", "/v1/purge/data", json=payload)

        if isinstance(response, dict):
            deleted = response.get("deleted", {})

            table = Table(title="Deletion Summary", show_header=True)
            table.add_column("Type", style="cyan")
            table.add_column("Deleted", justify="right", style="red")

            table.add_row("Tasks", str(deleted.get("tasks", 0)))
            table.add_row("Projects", str(deleted.get("projects", 0)))
            table.add_row("Labels", str(deleted.get("labels", 0)))
            table.add_row("Contexts", str(deleted.get("contexts", 0)))

            console.print(table)

            if response.get("encryption_cleared"):
                format_info("🔐 Encryption keys cleared")

            format_success("✓ All data has been permanently deleted")

        await client.close()

    asyncio.run(do_purge())
