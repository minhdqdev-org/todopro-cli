"""Sync commands for TodoPro CLI.

Provides data synchronization between local and remote storage.
"""

import asyncio
from datetime import UTC, datetime
from typing import Literal

import typer
from rich.table import Table

from todopro_cli.services.config_service import get_config_service, get_storage_strategy_context
from todopro_cli.services.sync_service import SyncPullService, SyncPushService
from todopro_cli.services.sync_state import SyncState
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(help="Sync data between local and remote storage")
console = get_console()


@app.command("pull")
def pull_command(
    context: str = typer.Option(
        None,
        "--context",
        "-c",
        help="Remote context to pull from (defaults to current if remote)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without applying them",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Perform full sync, ignoring last sync timestamp",
    ),
    strategy: Literal["local-wins", "remote-wins"] = typer.Option(
        "remote-wins",
        "--strategy",
        help="Conflict resolution strategy",
    ),
):
    """Pull data from remote to local storage.

    Imports tasks, projects, labels, and contexts from a remote context
    to the current local context.

    Examples:
        todopro sync pull
        todopro sync pull --context=company-cloud --dry-run
        todopro sync pull --full --strategy=remote-wins
    """
    asyncio.run(_pull(context, dry_run, full, strategy))


async def _pull(
    context: str | None,
    dry_run: bool,
    full: bool,
    strategy: Literal["local-wins", "remote-wins"],
):
    """Internal async pull implementation."""
    try:
        ctx_manager = get_config_service()
        current_ctx = ctx_manager.get_current_context()

        if current_ctx is None:
            console.print("[red]Error: No context configured[/red]")
            raise typer.Exit(1)

        # Determine source and target
        if context is None:
            if current_ctx.type == "remote":
                source_context_name = current_ctx.name
                # Need a local context to pull into
                console.print(
                    "[red]Error: Cannot pull from remote to remote. Switch to a local context first.[/red]"
                )
                raise typer.Exit(1)
            console.print(
                "[red]Error: --context is required when current context is local[/red]"
            )
            raise typer.Exit(1)
        source_context_name = context

        target_context_name = current_ctx.name

        # Get source context config
        source_ctx_config = ctx_manager.config.get_context(source_context_name)
        if source_ctx_config is None:
            console.print(
                f"[red]Error: Context '{source_context_name}' not found[/red]"
            )
            raise typer.Exit(1)

        # Create repository strategies for source and target contexts
        # Note: We need to get fresh strategy contexts after each context switch

        # Get source repositories
        original_context = ctx_manager.get_current_context().name
        ctx_manager.use_context(source_context_name)
        source_storage_strategy_context = get_storage_strategy_context()

        source_task_repo = source_storage_strategy_context.task_repository
        source_project_repo = source_storage_strategy_context.project_repository
        source_label_repo = source_storage_strategy_context.label_repository
        source_context_repo = source_storage_strategy_context.context_repository

        # Switch back to target context and get target repositories
        ctx_manager.use_context(target_context_name)
        target_storage_strategy_context = get_storage_strategy_context()

        target_task_repo = target_storage_strategy_context.task_repository
        target_project_repo = target_storage_strategy_context.project_repository
        target_label_repo = target_storage_strategy_context.label_repository
        target_context_repo = target_storage_strategy_context.context_repository

        # Create pull service
        pull_service = SyncPullService(
            source_task_repo=source_task_repo,
            source_project_repo=source_project_repo,
            source_label_repo=source_label_repo,
            source_context_repo=source_context_repo,
            target_task_repo=target_task_repo,
            target_project_repo=target_project_repo,
            target_label_repo=target_label_repo,
            target_context_repo=target_context_repo,
            console=console,
        )

        # Convert strategy format
        strategy_internal = strategy.replace("-", "_")

        # Display sync header
        console.print(
            f"\n[bold]Pulling from context '{source_context_name}'...[/bold]\n"
        )

        # Perform pull
        result = await pull_service.pull(
            source_context=source_context_name,
            target_context=target_context_name,
            dry_run=dry_run,
            full_sync=full,
            strategy=strategy_internal,
        )

        # Restore original context
        if original_context:
            ctx_manager.use_context(original_context)

        # Display results
        _display_sync_result(result, "pull", dry_run)

        if not result.success:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("push")
def push_command(
    context: str = typer.Option(
        None,
        "--context",
        "-c",
        help="Remote context to push to (defaults to current if remote)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without applying them",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Perform full sync, ignoring last sync timestamp",
    ),
    strategy: Literal["local-wins", "remote-wins"] = typer.Option(
        "local-wins",
        "--strategy",
        help="Conflict resolution strategy",
    ),
):
    """Push data from local to remote storage.

    Exports tasks, projects, labels, and contexts from the current local context
    to a remote context.

    Examples:
        todopro sync push --context=company-cloud
        todopro sync push --context=backup --dry-run
        todopro sync push --context=work --full
    """
    asyncio.run(_push(context, dry_run, full, strategy))


async def _push(
    context: str | None,
    dry_run: bool,
    full: bool,
    strategy: Literal["local-wins", "remote-wins"],
):
    """Internal async push implementation."""
    try:
        ctx_manager = get_config_service()
        current_ctx = ctx_manager.get_current_context()

        if current_ctx is None:
            console.print("[red]Error: No context configured[/red]")
            raise typer.Exit(1)

        # Source is current context (should be local)
        source_context_name = current_ctx.name

        if current_ctx.type != "local":
            console.print(
                "[red]Error: Can only push from local contexts. Switch to a local context first.[/red]"
            )
            raise typer.Exit(1)

        # Determine target
        if context is None:
            console.print(
                "[red]Error: --context is required to specify push target[/red]"
            )
            raise typer.Exit(1)

        target_context_name = context

        # Get target context config
        target_ctx_config = ctx_manager.config.get_context(target_context_name)
        if target_ctx_config is None:
            console.print(
                f"[red]Error: Context '{target_context_name}' not found[/red]"
            )
            raise typer.Exit(1)

        # Create repository strategies for source and target contexts
        # Get source repositories (current context)
        source_storage_strategy_context = get_storage_strategy_context()

        source_task_repo = source_storage_strategy_context.task_repository
        source_project_repo = source_storage_strategy_context.project_repository
        source_label_repo = source_storage_strategy_context.label_repository
        source_context_repo = source_storage_strategy_context.context_repository

        # Switch to target context for target repos
        original_context = ctx_manager.get_current_context().name
        ctx_manager.use_context(target_context_name)

        target_storage_strategy_context = get_storage_strategy_context()
        target_task_repo = target_storage_strategy_context.task_repository
        target_project_repo = target_storage_strategy_context.project_repository
        target_label_repo = target_storage_strategy_context.label_repository
        target_context_repo = target_storage_strategy_context.context_repository

        # Restore source context
        ctx_manager.use_context(source_context_name)

        # Create push service
        push_service = SyncPushService(
            source_task_repo=source_task_repo,
            source_project_repo=source_project_repo,
            source_label_repo=source_label_repo,
            source_context_repo=source_context_repo,
            target_task_repo=target_task_repo,
            target_project_repo=target_project_repo,
            target_label_repo=target_label_repo,
            target_context_repo=target_context_repo,
            console=console,
        )

        # Convert strategy format
        strategy_internal = strategy.replace("-", "_")

        # Display sync header
        console.print(f"\n[bold]Pushing to context '{target_context_name}'...[/bold]\n")

        # Perform push
        result = await push_service.push(
            source_context=source_context_name,
            target_context=target_context_name,
            dry_run=dry_run,
            full_sync=full,
            strategy=strategy_internal,
        )

        # Restore original context
        if original_context:
            ctx_manager.use_context(original_context)

        # Display results
        _display_sync_result(result, "push", dry_run)

        if not result.success:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("status")
def status_command():
    """Show sync status for current context.

    Displays last sync times and pending changes.
    """
    try:
        ctx_manager = get_config_service()
        current_ctx = ctx_manager.get_current_context()

        if current_ctx is None:
            console.print("[red]Error: No context configured[/red]")
            raise typer.Exit(1)

        sync_state = SyncState()
        all_syncs = sync_state.get_all_sync_times()

        if not all_syncs:
            console.print("[yellow]No sync history found[/yellow]")
            return

        # Display sync status
        console.print(f"\n[bold]Sync Status for context: {current_ctx.name}[/bold]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Sync Path", style="dim")
        table.add_column("Last Sync", justify="right")
        table.add_column("Time Ago", justify="right")

        now = datetime.now(UTC)

        for context_key, last_sync in all_syncs.items():
            if current_ctx.name in context_key:
                if last_sync is None:
                    table.add_row(context_key, "Never", "-")
                else:
                    delta = now - last_sync
                    if delta.days > 0:
                        time_ago = f"{delta.days}d ago"
                    elif delta.seconds > 3600:
                        time_ago = f"{delta.seconds // 3600}h ago"
                    elif delta.seconds > 60:
                        time_ago = f"{delta.seconds // 60}m ago"
                    else:
                        time_ago = f"{delta.seconds}s ago"

                    table.add_row(
                        context_key,
                        last_sync.strftime("%Y-%m-%d %H:%M:%S"),
                        time_ago,
                    )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


def _display_sync_result(result, direction: str, dry_run: bool):
    """Display sync result summary."""
    if dry_run:
        console.print("\n[bold yellow]Dry Run Results:[/bold yellow]")
    else:
        console.print()

    # Projects
    console.print(
        f"  [cyan]Projects:[/cyan] {result.projects_fetched} fetched, "
        f"{result.projects_new} new, {result.projects_updated} updated"
    )

    # Labels
    console.print(
        f"  [cyan]Labels:[/cyan] {result.labels_fetched} fetched, "
        f"{result.labels_new} new, {result.labels_updated} updated"
    )

    # Tasks
    console.print(
        f"  [cyan]Tasks:[/cyan] {result.tasks_fetched} fetched, "
        f"{result.tasks_new} new, {result.tasks_updated} updated, "
        f"{result.tasks_unchanged} unchanged"
    )

    if result.tasks_conflicts > 0:
        console.print(
            f"\n  [yellow]⚠ {result.tasks_conflicts} task conflicts detected[/yellow]"
        )
        console.print("  [dim]See ~/.todopro/sync-conflicts.json for details[/dim]")

        if direction == "push":
            console.print("  [dim]Consider running 'todopro sync pull' first[/dim]")

    if result.success:
        if dry_run:
            console.print(
                f"\n[green]✓ Dry run completed in {result.duration:.2f}s[/green]"
            )
        else:
            console.print(f"\n[green]✓ Sync complete in {result.duration:.2f}s[/green]")
    else:
        console.print(f"\n[red]✗ Sync failed: {result.error}[/red]")


if __name__ == "__main__":
    app()
