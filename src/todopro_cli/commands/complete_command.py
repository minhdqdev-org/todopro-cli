"""Command 'complete' of todopro-cli"""

from typing import Annotated

import typer

from todopro_cli.services.cache_service import get_background_cache
from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.background import run_in_background
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import (
    format_output,
    format_success,
)

from .decorators import command_wrapper

app = typer.Typer()
console = get_console()


@app.command("complete")
@command_wrapper
async def complete_command(
    task_ids: Annotated[
        list[str], typer.Argument(help="Task ID(s) - can specify multiple")
    ],
    output: Annotated[
        str, typer.Option("--output", "-o", help="Output format")
    ] = "table",
    json_opt: Annotated[
        bool, typer.Option("--json", help="Output as JSON (alias for --output json)")
    ] = False,
    sync_opt: Annotated[
        bool, typer.Option("--sync", help="Wait for completion")
    ] = False,
) -> None:
    """Mark one or more tasks as completed."""
    if json_opt:
        output = "json"

    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    # For local context, background mode uses the remote API which doesn't apply.
    # Always use sync mode so the local SQLite DB is updated directly.
    from todopro_cli.services.config_service import get_config_service

    _config_svc = get_config_service()
    if _config_svc.get_current_context().type == "local":
        sync_opt = True

    # Single task - use original logic
    if len(task_ids) == 1:
        task_id = task_ids[0]

        if sync_opt:
            # Synchronous mode - wait for completion
            resolved_id = await resolve_task_id(task_service, task_id)
            task = await task_service.complete_task(resolved_id)

            # Show concise success message
            content = task.content or "[No title]"
            # Truncate long content
            if len(content) > 60:
                content = content[:57] + "..."

            format_success(f"✓ Completed: {content}")
            console.print(f"[dim]To undo: tp reopen {task_id}[/dim]")

            # Only show full output if explicitly requested
            if output not in ["table", "pretty"]:
                format_output(task.model_dump(), output)
        else:
            # Background mode - don't wait, start immediately

            # Add to cache for optimistic UI update
            cache = get_background_cache()
            cache.add_completing_task(task_id)

            # Start background task immediately
            run_in_background(
                task_type="complete",
                command="complete",
                context={
                    "task_id": task_id,
                },
                max_retries=3,
            )

            # Show immediate feedback without waiting
            format_success(f"✓ Marking task as complete: {task_id}")
            console.print(f"[dim]Check status: tp tasks get {task_id}[/dim]")

    # Multiple tasks - use batch API
    else:
        if sync_opt:
            # Synchronous batch mode
            # Resolve all IDs first
            resolved_ids = []
            for task_id in task_ids:
                resolved_id = await resolve_task_id(task_service, task_id)
                resolved_ids.append(resolved_id)

            # Batch complete
            completed_tasks = await task_service.bulk_complete_tasks(resolved_ids)

            # Show results
            format_success(f"✓ Completed {len(completed_tasks)} task(s)")
            for task in completed_tasks:
                content = task.content[:50] if task.content else "[No title]"
                console.print(f"  • {content}")

        else:
            # Background batch mode

            # Add all tasks to cache for optimistic UI update
            cache = get_background_cache()
            cache.add_completing_tasks(task_ids)

            run_in_background(
                task_type="batch_complete",
                command="complete",
                context={
                    "task_ids": task_ids,
                },
                max_retries=3,
            )

            # Show immediate feedback
            format_success(
                f"✓ Marking {len(task_ids)} task(s) as complete in background"
            )
            console.print(f"[dim]Tasks: {', '.join(task_ids)}[/dim]")
