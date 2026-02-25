"""Task template commands for TodoPro CLI."""

import asyncio

import typer
from rich.table import Table

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.templates import TemplatesAPI
from todopro_cli.utils.recurrence import resolve_rrule
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Manage task templates")
console = get_console()


@app.command("create")
def create_template(
    name: str = typer.Argument(..., help="Template name"),
    content: str = typer.Option(..., "--content", "-c", help="Task content/title"),
    description: str = typer.Option(
        None, "--description", "-d", help="Task description"
    ),
    priority: int = typer.Option(
        4, "--priority", "-p", help="Priority (1-4)", min=1, max=4
    ),
    label: list[str] = typer.Option(
        None, "--label", "-l", help="Label names (repeatable)"
    ),
    recur: str = typer.Option(
        None,
        "--recur",
        help="Recurrence pattern (daily/weekly/monthly/weekdays/bi-weekly)",
    ),
) -> None:
    """Create a new task template."""
    rrule = None
    if recur:
        rrule = resolve_rrule(recur)
        if not rrule:
            console.print(f"[red]Unknown recurrence pattern: {recur}[/red]")
            raise typer.Exit(1)

    async def do_create() -> None:
        client = get_client()
        api = TemplatesAPI(client)
        try:
            template = await api.create_template(
                name=name,
                content=content,
                description=description,
                priority=priority,
                labels=list(label) if label else [],
                recurrence_rule=rrule,
            )
            console.print(
                f"[green]✓[/green] Template [bold]{template['name']}[/bold] created (ID: {template['id']})"
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        finally:
            await client.close()

    asyncio.run(do_create())


@app.command("list")
def list_templates() -> None:
    """List all task templates."""

    async def do_list() -> None:
        client = get_client()
        api = TemplatesAPI(client)
        try:
            templates = await api.list_templates()
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        finally:
            await client.close()

        if not templates:
            console.print("[yellow]No templates found.[/yellow]")
            return

        table = Table(title="Task Templates")
        table.add_column("Name", style="cyan bold")
        table.add_column("Content")
        table.add_column("Priority", justify="center")
        table.add_column("Recurrence")
        table.add_column("ID", style="dim")

        priority_labels = {1: "Urgent", 2: "High", 3: "Medium", 4: "Normal"}
        for t in templates:
            table.add_row(
                t["name"],
                t["content"],
                priority_labels.get(t["priority"], str(t["priority"])),
                t.get("recurrence_rule") or "-",
                t["id"][:8] + "…",
            )
        console.print(table)

    asyncio.run(do_list())


@app.command("apply")
def apply_template(
    name_or_id: str = typer.Argument(..., help="Template name or ID"),
    title: str = typer.Option(None, "--title", "-t", help="Override task title"),
    project: str = typer.Option(None, "--project", "-P", help="Project ID"),
    due: str = typer.Option(
        None, "--due", "-D", help="Due date (YYYY-MM-DD or ISO datetime)"
    ),
    priority: int = typer.Option(
        None, "--priority", "-p", help="Override priority (1-4)", min=1, max=4
    ),
) -> None:
    """Create a task from a template."""

    async def do_apply() -> None:
        client = get_client()
        api = TemplatesAPI(client)
        try:
            template = await api.find_template_by_name(name_or_id)
            if not template:
                console.print(f"[red]Template not found:[/red] {name_or_id}")
                raise typer.Exit(1)

            task = await api.apply_template(
                template["id"],
                content=title,
                project_id=project,
                due_date=due,
                priority=priority,
            )
            console.print(
                f"[green]✓[/green] Task [bold]{task.get('content', '')}[/bold] created from template [cyan]{template['name']}[/cyan] (ID: {task['id']})"
            )
        except typer.Exit:
            raise
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(do_apply())


@app.command("delete")
def delete_template(
    name_or_id: str = typer.Argument(..., help="Template name or ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a task template."""

    async def do_delete() -> None:
        client = get_client()
        api = TemplatesAPI(client)
        try:
            template = await api.find_template_by_name(name_or_id)
            if not template:
                console.print(f"[red]Template not found:[/red] {name_or_id}")
                raise typer.Exit(1)

            if not yes:
                confirm = typer.confirm(f"Delete template '{template['name']}'?")
                if not confirm:
                    console.print("[yellow]Aborted.[/yellow]")
                    return

            await api.delete_template(template["id"])
            console.print(
                f"[green]✓[/green] Template [bold]{template['name']}[/bold] deleted."
            )
        except typer.Exit:
            raise
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        finally:
            await client.close()

    asyncio.run(do_delete())
