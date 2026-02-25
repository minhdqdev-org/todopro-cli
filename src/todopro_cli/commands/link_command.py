"""Task dependency link commands for TodoPro CLI."""

import asyncio

import typer
from rich.table import Table

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Manage task dependencies")
console = get_console()


@app.command("add")
def link_task(
    task_id: str = typer.Argument(..., help="Task ID that has the dependency"),
    blocks: str = typer.Option(
        None, "--blocks", help="ID of a task that this task blocks"
    ),
    blocked_by: str = typer.Option(
        None, "--blocked-by", help="ID of a task that blocks this task"
    ),
) -> None:
    """Link two tasks with a dependency relationship."""
    if not blocks and not blocked_by:
        console.print("[red]Error:[/red] Provide --blocks or --blocked-by")
        raise typer.Exit(1)
    if blocks and blocked_by:
        console.print("[red]Error:[/red] Use either --blocks or --blocked-by, not both")
        raise typer.Exit(1)

    async def do_link() -> None:
        client = get_client()
        api = TasksAPI(client)
        try:
            if blocks:
                # task_id blocks another task → the other task depends_on task_id
                dep = await api.add_dependency(
                    blocks, task_id, dependency_type="blocks"
                )
                console.print(
                    f"[green]✓[/green] Task {task_id[:8]}… now blocks task {blocks[:8]}…"
                )
            else:
                # task_id is blocked_by another task → task_id depends_on blocked_by
                dep = await api.add_dependency(
                    task_id, blocked_by, dependency_type="blocks"
                )
                console.print(
                    f"[green]✓[/green] Task {task_id[:8]}… is now blocked by task {blocked_by[:8]}…"
                )
            console.print(f"  Dependency ID: {dep['id']}")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        finally:
            await client.close()

    asyncio.run(do_link())


@app.command("remove")
def unlink_task(
    task_id: str = typer.Argument(..., help="Task ID"),
    dep_id: str = typer.Option(..., "--dep", "-d", help="Dependency ID to remove"),
) -> None:
    """Remove a dependency from a task."""

    async def do_unlink() -> None:
        client = get_client()
        api = TasksAPI(client)
        try:
            await api.remove_dependency(task_id, dep_id)
            console.print(
                f"[green]✓[/green] Dependency {dep_id[:8]}… removed from task {task_id[:8]}…"
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        finally:
            await client.close()

    asyncio.run(do_unlink())


@app.command("list")
def list_dependencies(
    task_id: str = typer.Argument(..., help="Task ID"),
) -> None:
    """List dependencies of a task."""

    async def do_list() -> None:
        client = get_client()
        api = TasksAPI(client)
        try:
            deps = await api.list_dependencies(task_id)
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        finally:
            await client.close()

        if not deps:
            console.print(
                f"[yellow]No dependencies found for task {task_id[:8]}…[/yellow]"
            )
            return

        table = Table(title=f"Dependencies of {task_id[:8]}…")
        table.add_column("Dep ID", style="dim")
        table.add_column("Depends On", style="cyan")
        table.add_column("Type")

        for dep in deps:
            table.add_row(
                dep["id"][:8] + "…",
                dep.get("depends_on_content", dep.get("depends_on_id", ""))[:50],
                dep.get("dependency_type", "blocks"),
            )
        console.print(table)

    asyncio.run(do_list())
