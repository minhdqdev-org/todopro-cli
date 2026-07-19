"""Productivity hub - unified view of external items (GitHub Projects, …)."""

import asyncio

import httpx
import typer
from rich.table import Table

from todopro_cli.services.api.client import get_client
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Productivity hub — unified external items")
console = get_console()


def _require_remote_context() -> None:
    """Ensure the active context is remote (cloud).

    Hub commands talk to the TodoPro backend, so they cannot run against a
    local SQLite context.
    """
    config_svc = get_config_service()
    try:
        current_context = config_svc.get_current_context()
    except (ValueError, KeyError):
        current_context = None

    if current_context is None or current_context.type != "remote":
        ctx_name = current_context.name if current_context else "local"
        console.print(
            "[red]Error: This command requires a remote (cloud) context.[/red]"
        )
        console.print(
            f"[dim]Active context is '[bold]{ctx_name}[/bold]' (local). "
            "Switch with:[/dim] [cyan]todopro context use cloud[/cyan]"
        )
        raise typer.Exit(1)


def _extract_error_message(response: httpx.Response) -> str:
    """Best-effort extraction of an error message from an API response."""
    try:
        data = response.json()
    except Exception:
        return response.text or f"HTTP {response.status_code}"
    err = data.get("error")
    if isinstance(err, dict):
        return err.get("message") or str(err)
    if isinstance(err, str):
        return err
    return str(data)


def _handle_pro_required(response: httpx.Response) -> None:
    """Print a Pro-required (402) message extracted from the API response."""
    try:
        err = response.json().get("error", {})
    except Exception:
        err = {}
    message = (
        err.get("message") if isinstance(err, dict) else None
    ) or "A Pro subscription is required for the productivity hub."
    upgrade_url = (
        err.get("details", {}).get("upgrade_url") if isinstance(err, dict) else None
    )
    console.print(f"[yellow]⚠ Pro subscription required:[/yellow] {message}")
    if upgrade_url:
        console.print(f"[dim]Upgrade:[/dim] [cyan]{upgrade_url}[/cyan]")


@app.command("list")
def list_items(
    provider: str | None = typer.Option(
        None, "--provider", help="Filter by provider (e.g. github)"
    ),
    state: str | None = typer.Option(
        None, "--state", help="Filter by item state (e.g. open, closed)"
    ),
    link: str | None = typer.Option(None, "--link", help="Filter by project link id"),
    limit: int = typer.Option(50, "--limit", help="Max items to display"),
) -> None:
    """List aggregated external items across linked providers (Pro)."""
    _require_remote_context()

    params: dict[str, object] = {"limit": limit}
    if provider:
        params["provider"] = provider
    if state:
        params["state"] = state
    if link:
        params["link"] = link

    async def _do() -> dict:
        client = get_client()
        try:
            response = await client.get("/integrations/hub/items/", params=params)
            return response.json()
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 402:
            _handle_pro_required(exc.response)
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: Not authenticated. Run [cyan]todopro login[/cyan] first.[/red]"
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    items = data.get("items", [])
    count = data.get("count", len(items))
    if not items:
        console.print("No hub items found.")
        return

    table = Table(title=f"Hub items ({count})")
    table.add_column("Provider/Project", style="magenta")
    table.add_column("#", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Title")
    table.add_column("State", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("URL", style="blue")

    for item in items:
        provider_name = item.get("provider", "")
        project_name = item.get("project_name", "")
        proj_cell = f"{provider_name}/{project_name}" if project_name else provider_name
        number = item.get("external_number")
        title = item.get("title", "")
        if item.get("task_id"):
            title = f"{title} [dim](task)[/dim]"
        table.add_row(
            proj_cell,
            f"#{number}" if number is not None else "",
            item.get("item_type", ""),
            title,
            item.get("state", ""),
            item.get("status_value") or "",
            item.get("url", ""),
        )

    console.print(table)
