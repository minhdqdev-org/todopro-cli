"""Context management commands for TodoPro CLI.

Provides kubectl-style context switching between local and remote storage.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import typer
from platformdirs import user_data_dir
from rich.table import Table

from todopro_cli.adapters.sqlite.connection import get_connection
from todopro_cli.adapters.sqlite.schema import initialize_schema
from todopro_cli.models.config_models import Context
from todopro_cli.services.api.auth import AuthAPI
from todopro_cli.services.api.client import get_client
from todopro_cli.utils.ui.console import get_console

from .decorators import command_wrapper

app = typer.Typer(
    help="Manage storage contexts (local/remote)",
    no_args_is_help=False,  # Allow bare command
)
console = get_console()


def show_current_context_info(output: str = "text"):
    """Show current context information including user info."""
    manager = get_config_service()
    ctx = manager.get_current_context()

    if ctx is None:
        console.print("[red]No current context set[/red]")
        console.print("\nUse [cyan]todopro context create[/cyan] to create a context")
        raise typer.Exit(1)

    if output == "json":
        data: dict[str, object | None] = {
            "name": ctx.name,
            "type": ctx.type,
            "source": ctx.source,
            "description": ctx.description,
        }
        if ctx.user:
            data["user"] = ctx.user
        if ctx.workspace_id:
            data["workspace"] = ctx.workspace_id

        # Add user info for remote contexts
        if ctx.type == "remote":
            data["user_info"] = _get_user_info_sync()

        console.print_json(json.dumps(data, indent=2))
    else:
        console.print(f"\n[bold]Context:[/bold] {ctx.name} ([cyan]{ctx.type}[/cyan])")
        console.print(f"[bold]Source:[/bold] {ctx.source}")

        if ctx.description:
            console.print(f"[bold]Description:[/bold] {ctx.description}")

        if ctx.user:
            console.print(f"[bold]User:[/bold] {ctx.user}")

        if ctx.workspace_id:
            console.print(f"[bold]Workspace:[/bold] {ctx.workspace_id}")

        # Local context specific info
        if ctx.type == "local":
            source_path = Path(os.path.expanduser(ctx.source))

            if source_path.exists():
                # File stats
                stat = source_path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                console.print(f"[bold]File Size:[/bold] {size_mb:.2f} MB")

                modified = datetime.fromtimestamp(stat.st_mtime)
                console.print(
                    f"[bold]Last Modified:[/bold] {modified.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # Database stats
                conn = get_connection(source_path)

                # Count records
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE deleted_at IS NULL"
                )
                task_count = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE is_completed = 1 AND deleted_at IS NULL"
                )
                completed_count = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM projects WHERE deleted_at IS NULL"
                )
                project_count = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM labels")
                label_count = cursor.fetchone()[0]

                console.print("\n[bold]Records:[/bold]")
                console.print(f"  • Tasks: {task_count} ({completed_count} completed)")
                console.print(f"  • Projects: {project_count}")
                console.print(f"  • Labels: {label_count}")

            else:
                console.print("[yellow]Database file not yet created[/yellow]")

            # Encryption status
            if ctx.encryption and ctx.encryption.enabled:
                console.print("\n[bold]Encryption:[/bold] ✓ Enabled (AES-256-GCM)")
            else:
                console.print("\n[bold]Encryption:[/bold] Disabled")

        # Remote context - show user info
        elif ctx.type == "remote":
            console.print()

            user_info = _get_user_info_sync()
            assert user_info is not None
            console.print("[bold]User Information:[/bold]")
            console.print(f"  • Email: {user_info.get('email', 'N/A')}")
            console.print(f"  • Name: {user_info.get('name', 'N/A')}")
            console.print(f"  • ID: {user_info.get('id', 'N/A')}")

        console.print()


def _get_user_info_sync():
    """Get user info synchronously for remote contexts."""

    manager = get_config_service()
    credentials = manager.load_credentials()

    if not credentials:
        return None

    async def get_user():
        client = get_client()
        auth_api = AuthAPI(client)
        try:
            user = await auth_api.get_profile()
            return user
        finally:
            await client.close()

    return asyncio.run(get_user())


@app.callback(invoke_without_command=True)
def context_callback(
    ctx: typer.Context,
    output: str = typer.Option(
        "text", "--output", "-o", help="Output format: text or json"
    ),
):
    """Show current context information.

    Run 'todopro context' to see the active context.
    Use subcommands to manage contexts (create, use, delete, etc.)
    """
    # If a subcommand is being called, skip the default behavior
    if ctx.invoked_subcommand is not None:
        return

    # Show current context info (default behavior)
    show_current_context_info(output)


@app.command("list", help="List all available contexts")
@command_wrapper(auth_required=False)
def list_contexts(
    output: str = typer.Option(
        "table", "--output", "-o", help="Output format: table or json"
    ),
):
    """List all available contexts."""
    manager = get_config_service()
    contexts = manager.list_contexts()
    current_name = manager.config.current_context

    if output == "json":
        # JSON output
        context_list = []
        for ctx in contexts:
            context_list.append(
                {
                    "name": ctx.name,
                    "type": ctx.type,
                    "source": ctx.source,
                    "current": ctx.name == current_name,
                    "description": ctx.description,
                }
            )
        console.print_json(json.dumps(context_list, indent=2))
    else:
        # Table output
        table = Table(title="TodoPro Contexts")
        table.add_column("ACTIVE", style="green")
        table.add_column("NAME", style="cyan")
        table.add_column("TYPE", style="yellow")
        table.add_column("SOURCE")

        for ctx in contexts:
            active = "*" if ctx.name == current_name else ""
            table.add_row(active, ctx.name, ctx.type, ctx.source)

        console.print(table)

        if not contexts:
            console.print("[yellow]No contexts configured[/yellow]")


@app.command("use", help="Switch to a different context")
@command_wrapper(auth_required=False)
def use_context(name: str = typer.Argument(..., help="Context name to switch to")):
    """Switch to a different context."""
    manager = get_config_service()

    try:
        # Check if already using this context
        current = manager.get_current_context()

        if current and current.name == name:
            console.print(
                f"[yellow]ℹ[/yellow] Already using context '{name}' ([cyan]{current.type}[/cyan])"
            )
            console.print(f"  Source: {current.source}")
            return

        ctx = manager.use_context(name)
        console.print(
            f"[green]✓[/green] Switched to context '{ctx.name}' ([cyan]{ctx.type}[/cyan])"
        )
        console.print(f"  Using: {ctx.source}")

        # Warn if local vault doesn't exist
        if ctx.type == "local":
            source_path = Path(os.path.expanduser(ctx.source))
            if not source_path.exists():
                console.print(
                    "\n[yellow]⚠ Warning:[/yellow] Local vault doesn't exist yet."
                )
                console.print("  It will be created on first use.")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("create", help="Create a new context")
@command_wrapper(auth_required=False)
def create_context(
    name: str = typer.Argument(..., help="Context name"),
    ctx_type: str = typer.Option(..., "--type", help="Context type: local or remote"),
    source: str = typer.Option(
        None, "--source", help="Database path or API URL (optional for local)"
    ),
    user: str = typer.Option(None, "--user", help="User email (for remote contexts)"),
    description: str = typer.Option("", "--description", help="Context description"),
):
    """Create a new context."""
    manager = get_config_service()

    # Validate type
    if ctx_type not in ["local", "remote"]:
        console.print("[red]Error:[/red] type must be 'local' or 'remote'")
        raise typer.Exit(1)

    # Check if context already exists
    if manager.get_context(name) is not None:
        console.print(f"[red]Error:[/red] Context '{name}' already exists")
        raise typer.Exit(1)

    # Set default source for local contexts if not provided
    if ctx_type == "local" and not source:
        data_dir = Path(user_data_dir("todopro-cli"))
        data_dir.mkdir(parents=True, exist_ok=True)
        source = str(data_dir / f"{name}.db")
        console.print(f"[dim]Using default database path: {source}[/dim]")
    elif ctx_type == "remote" and not source:
        console.print("[red]Error:[/red] --source is required for remote contexts")
        raise typer.Exit(1)

    # Validate remote context has user
    if ctx_type == "remote" and not user:
        console.print("[red]Error:[/red] --user is required for remote contexts")
        raise typer.Exit(1)

    # Create context config
    ctx = Context(
        name=name,
        type=ctx_type,  # type: ignore
        source=source,
        user=user,
        description=description,
    )

    # For local contexts, check if we should create the database
    if ctx_type == "local":
        source_path = Path(os.path.expanduser(source))
        if not source_path.exists():
            create_db = typer.confirm(
                "Database doesn't exist. Create it now?", default=True
            )
            if create_db:
                # Initialize local database
                try:
                    conn = get_connection(source_path)
                    initialize_schema(conn)
                    conn.close()
                    console.print(
                        f"[green]✓[/green] Created local database at {source}"
                    )
                except Exception as e:
                    console.print(f"[red]Error:[/red] Failed to create database: {e}")
                    raise typer.Exit(1) from e

    # Add context
    manager.add_context(ctx)
    console.print(f"[green]✓[/green] Created context '{name}'")
    console.print(f"  Type: {ctx_type}")
    console.print(f"  Source: {source}")


@app.command("delete", help="Delete a context")
@app.command("rm", help="Delete a context (alias)")
@command_wrapper(auth_required=False)
def delete_context(
    name: str = typer.Argument(..., help="Context name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    delete_db: bool = typer.Option(
        False, "--delete-db", help="Also delete local database file"
    ),
):
    """Delete a context."""
    manager = get_config_service()

    ctx = manager.get_context(name)
    if ctx is None:
        console.print(f"[red]Error:[/red] Context '{name}' not found")
        raise typer.Exit(1)

    # Confirm deletion
    if not force:
        confirmed = typer.confirm(f"Remove context '{name}'?")
        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(0)

    manager.remove_context(name)
    console.print(f"[green]✓[/green] Removed context '{name}'")

    # Handle database deletion for local contexts
    if ctx.type == "local" and delete_db:
        source_path = Path(os.path.expanduser(ctx.source))
        if source_path.exists():
            source_path.unlink()
            console.print("[green]✓[/green] Deleted database file")


@app.command("rename", help="Rename a context")
@command_wrapper(auth_required=False)
def rename_context(
    old_name: str = typer.Argument(..., help="Current context name"),
    new_name: str = typer.Argument(..., help="New context name"),
):
    """Rename a context."""
    manager = get_config_service()

    renamed = manager.rename_context(old_name, new_name)
    if renamed:
        console.print(f"[green]✓[/green] Renamed context '{old_name}' to '{new_name}'")
    else:
        console.print(f"[red]Error:[/red] Context '{old_name}' not found")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
