"""Task comment commands for TodoPro CLI."""

from __future__ import annotations

import asyncio

import typer
from rich.table import Table

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.collaboration import CollaborationAPI
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(help="Manage task comments")
console = get_console()


@app.command("add")
def add_comment(
    task_id: str = typer.Argument(..., help="Task ID"),
    content: str = typer.Argument(..., help="Comment content"),
) -> None:
    """Add a comment to a task."""

    async def do_add() -> None:
        client = get_client()
        api = CollaborationAPI(client)
        try:
            comment = await api.add_comment(task_id, content)
            console.print(f"[green]✓[/green] Comment added (ID: {comment['id']})")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(do_add())


@app.command("list")
def list_comments(
    task_id: str = typer.Argument(..., help="Task ID"),
) -> None:
    """List all comments for a task."""

    async def do_list() -> None:
        client = get_client()
        api = CollaborationAPI(client)
        try:
            comments = await api.get_comments(task_id)
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

        if not comments:
            console.print("[yellow]No comments found.[/yellow]")
            return

        table = Table(title=f"Comments for task {task_id}")
        table.add_column("ID", style="dim")
        table.add_column("Content")
        table.add_column("Author", style="cyan")
        table.add_column("Created", style="dim")

        for comment in comments:
            author = comment.get("author", comment.get("user", {}) or {})
            author_name = (
                author.get("email", author.get("name", ""))
                if isinstance(author, dict)
                else str(author)
            )
            table.add_row(
                comment.get("id", ""),
                comment.get("content", ""),
                author_name,
                comment.get("created_at", ""),
            )
        console.print(table)

    asyncio.run(do_list())


@app.command("delete")
def delete_comment(
    task_id: str = typer.Argument(..., help="Task ID"),
    comment_id: str = typer.Argument(..., help="Comment ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a comment from a task."""
    if not yes:
        confirm = typer.confirm(f"Delete comment '{comment_id}'?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            return

    async def do_delete() -> None:
        client = get_client()
        api = CollaborationAPI(client)
        try:
            await api.delete_comment(task_id, comment_id)
            console.print(f"[green]✓[/green] Comment {comment_id} deleted.")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(do_delete())
