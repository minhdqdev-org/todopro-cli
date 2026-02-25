"""Project collaboration commands for TodoPro CLI."""

from __future__ import annotations

import asyncio

import typer
from rich.table import Table

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.collaboration import CollaborationAPI
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(help="Manage project collaboration")
console = get_console()


@app.command("share")
def share_project(
    project_id: str = typer.Argument(..., help="Project ID to share"),
    email: str = typer.Option(..., "--email", "-e", help="Email of user to share with"),
    permission: str = typer.Option(
        "editor", "--permission", "-p", help="Permission level: editor, viewer, admin"
    ),
) -> None:
    """Share a project with another user."""

    async def do_share() -> None:
        client = get_client()
        api = CollaborationAPI(client)
        try:
            result = await api.share_project(project_id, email, permission)
            console.print(
                f"[green]✓[/green] Project shared with {email} as {permission}"
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(do_share())


@app.command("collaborators")
def list_collaborators(
    project_id: str = typer.Argument(..., help="Project ID"),
) -> None:
    """List all collaborators for a project."""

    async def do_list() -> None:
        client = get_client()
        api = CollaborationAPI(client)
        try:
            collaborators = await api.get_collaborators(project_id)
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

        if not collaborators:
            console.print("[yellow]No collaborators found.[/yellow]")
            return

        table = Table(title=f"Collaborators for project {project_id}")
        table.add_column("User ID", style="cyan")
        table.add_column("Permission", style="bold")
        table.add_column("Shared At", style="dim")

        for collab in collaborators:
            table.add_row(
                collab.get("user_id", collab.get("id", "")),
                collab.get("permission", ""),
                collab.get(
                    "shared_at", collab.get("joined_at", collab.get("created_at", ""))
                ),
            )
        console.print(table)

    asyncio.run(do_list())


@app.command("unshare")
def unshare_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    user_id: str | None = typer.Option(None, "--user-id", help="User ID to remove"),
    email: str | None = typer.Option(
        None, "--email", "-e", help="Email of user to remove (user-id required)"
    ),
) -> None:
    """Remove a collaborator from a project."""
    if not user_id:
        console.print(
            "[red]Error:[/red] --user-id is required to remove a collaborator."
        )
        raise typer.Exit(1)

    async def do_unshare() -> None:
        client = get_client()
        api = CollaborationAPI(client)
        try:
            await api.remove_collaborator(project_id, user_id)
            console.print(f"[green]✓[/green] {user_id} removed from project")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(do_unshare())


@app.command("leave")
def leave_project(
    project_id: str = typer.Argument(..., help="Project ID to leave"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Leave a shared project."""
    if not yes:
        confirm = typer.confirm(
            f"Are you sure you want to leave project '{project_id}'?"
        )
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            return

    async def do_leave() -> None:
        client = get_client()
        api = CollaborationAPI(client)
        try:
            await api.leave_project(project_id)
            console.print(f"[green]✓[/green] Left project {project_id}")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(do_leave())
