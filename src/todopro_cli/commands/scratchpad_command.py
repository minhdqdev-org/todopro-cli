"""Scratchpad management commands.

Scratchpads are project-scoped free-form notes. They are a **remote-only**
feature — run these against a remote context (``todopro context use cloud``).
The per-project count is capped by subscription tier (free: 2, pro/trial: 20),
enforced server-side.
"""

from pathlib import Path

import typer

from todopro_cli.services.config_service import get_storage_strategy_context
from todopro_cli.services.scratchpad_service import get_scratchpad_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.uuid_utils import resolve_project_uuid

from .decorators import command_wrapper

app = typer.Typer(
    cls=SuggestingGroup, help="Scratchpad management commands (remote-only)"
)
console = get_console()


def _resolve_content(content: str | None, content_file: str | None) -> str | None:
    """Resolve note body from an inline string or a file (``--content-file``)."""
    if content_file is not None:
        path = Path(content_file).expanduser()
        if not path.is_file():
            format_error(f"Content file not found: {content_file}")
            raise typer.Exit(1)
        return path.read_text(encoding="utf-8")
    return content


@app.command("list")
@command_wrapper
async def list_scratchpads(
    project_id: str = typer.Argument(
        ..., help="Project ID, name, or suffix (from 'tp project list')"
    ),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """List scratchpads in a project."""
    if json_opt:
        output = "json"
    storage_strategy_context = get_storage_strategy_context()
    # Instantiate the service first so the remote-only guard fires with a clear
    # message before we try to resolve the project against the local repo.
    scratchpad_service = get_scratchpad_service()
    resolved_project_id = await resolve_project_uuid(
        project_id, storage_strategy_context.project_repository
    )
    scratchpads = await scratchpad_service.list_scratchpads(resolved_project_id)
    result = {"scratchpads": [s.model_dump() for s in scratchpads]}
    format_output(result, output)


@app.command("get")
@command_wrapper
async def get_scratchpad(
    scratchpad_id: str = typer.Argument(
        ..., help="Scratchpad ID (from 'tp scratchpad list <project>')"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Get a scratchpad by ID."""
    scratchpad_service = get_scratchpad_service()
    scratchpad = await scratchpad_service.get_scratchpad(scratchpad_id)
    format_output(scratchpad.model_dump(), output)


@app.command("create")
@command_wrapper
async def create_scratchpad(
    project_id: str = typer.Argument(..., help="Project ID, name, or suffix"),
    title: str = typer.Option("", "--title", "-t", help="Scratchpad title"),
    content: str | None = typer.Option(
        None, "--content", "-c", help="Note body (HTML/plaintext)"
    ),
    content_file: str | None = typer.Option(
        None, "--content-file", "-f", help="Read note body from a file"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Create a new scratchpad within a project."""
    body = _resolve_content(content, content_file) or ""
    storage_strategy_context = get_storage_strategy_context()
    # Instantiate the service first so the remote-only guard fires with a clear
    # message before we try to resolve the project against the local repo.
    scratchpad_service = get_scratchpad_service()
    resolved_project_id = await resolve_project_uuid(
        project_id, storage_strategy_context.project_repository
    )
    scratchpad = await scratchpad_service.create_scratchpad(
        resolved_project_id, title=title, content=body
    )
    format_success(f"Scratchpad created: {scratchpad.id}")
    format_output(scratchpad.model_dump(), output)


@app.command("update")
@command_wrapper
async def update_scratchpad(
    scratchpad_id: str = typer.Argument(..., help="Scratchpad ID"),
    title: str | None = typer.Option(None, "--title", "-t", help="New title"),
    content: str | None = typer.Option(
        None, "--content", "-c", help="New note body (HTML/plaintext)"
    ),
    content_file: str | None = typer.Option(
        None, "--content-file", "-f", help="Read new note body from a file"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Update a scratchpad's title and/or content."""
    body = _resolve_content(content, content_file)
    if title is None and body is None:
        format_error(
            "No updates specified (pass --title and/or --content/--content-file)"
        )
        raise typer.Exit(1)

    scratchpad_service = get_scratchpad_service()
    scratchpad = await scratchpad_service.update_scratchpad(
        scratchpad_id, title=title, content=body
    )
    format_success(f"Scratchpad updated: {scratchpad_id}")
    format_output(scratchpad.model_dump(), output)


@app.command("delete")
@command_wrapper
async def delete_scratchpad(
    scratchpad_id: str = typer.Argument(..., help="Scratchpad ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a scratchpad."""
    if not yes and not typer.confirm(
        f"Are you sure you want to delete scratchpad {scratchpad_id}?"
    ):
        format_error("Cancelled")
        raise typer.Exit(0)

    scratchpad_service = get_scratchpad_service()
    await scratchpad_service.delete_scratchpad(scratchpad_id)
    format_success(f"Scratchpad deleted: {scratchpad_id}")
