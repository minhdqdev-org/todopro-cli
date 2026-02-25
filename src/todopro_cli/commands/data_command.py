"""Data management commands (import, export, purge)."""

import asyncio
import gzip
import json
from datetime import datetime
from pathlib import Path

import typer
from rich.prompt import Confirm, Prompt
from rich.table import Table

from todopro_cli.models import ProjectFilters, TaskFilters
from todopro_cli.services.api.client import get_client
from todopro_cli.services.config_service import (
    get_config_service,
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
) -> None:
    """
    Export all your data (tasks, projects, labels, contexts) to JSON.

    Examples:
        todopro data export
        todopro data export --output backup.json
        todopro data export --compress
    """

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
            response = await client.request("GET", "/api/export/data", params=params)
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

            # Import projects first (tasks may reference them)
            projects_created = 0
            projects_skipped = 0
            for project_data in import_data_payload.get("projects", []):
                try:
                    # Check if project already exists by name
                    existing = (
                        await storage_strategy_context.project_repository.list_all(
                            ProjectFilters(name=project_data.get("name"))
                        )
                    )
                    if existing:
                        projects_skipped += 1
                        continue

                    # Create project (excluding id to let DB generate new one)
                    from todopro_cli.models import ProjectCreate

                    project_create = ProjectCreate(
                        name=project_data["name"],
                        description=project_data.get("description"),
                        color=project_data.get("color"),
                        archived=project_data.get("archived", False),
                    )
                    await storage_strategy_context.project_repository.create(
                        project_create
                    )
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
                    if any(l.name == label_data.get("name") for l in existing):
                        labels_skipped += 1
                        continue

                    # Create label
                    from todopro_cli.models import LabelCreate

                    label_create = LabelCreate(
                        name=label_data["name"],
                        color=label_data.get("color"),
                    )
                    await storage_strategy_context.label_repository.create(label_create)
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

                    # Create task (map project name to ID if present)
                    from todopro_cli.models import TaskCreate

                    project_id = None
                    if task_data.get("project_name"):
                        projects = (
                            await storage_strategy_context.project_repository.list_all(
                                ProjectFilters(name=task_data["project_name"])
                            )
                        )
                        if projects:
                            project_id = projects[0].id

                    task_create = TaskCreate(
                        content=task_data["content"],
                        description=task_data.get("description"),
                        priority=task_data.get("priority", 4),
                        project_id=project_id,
                        label_ids=task_data.get("label_ids", []),
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
            response = await client.request("POST", "/api/import/data", json=data)
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
                "POST", "/api/purge/data", params=params, json=payload
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

        response = await client.request("POST", "/api/purge/data", json=payload)

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
