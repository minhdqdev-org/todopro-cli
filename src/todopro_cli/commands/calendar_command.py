"""Google Calendar integration commands."""

import asyncio

import httpx
import typer
from rich.table import Table

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="Google Calendar integration commands")
console = get_console()

_GOOGLE_PATH = "/api/integrations/google"


def _get_base_url() -> str:
    from todopro_cli.utils.update_checker import get_backend_url

    return get_backend_url().rstrip("/")


def _get_auth_headers() -> dict:
    from todopro_cli.services.config_service import get_config_service

    config_manager = get_config_service()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    current_context = config_manager.get_current_context()
    credentials = (
        config_manager.load_context_credentials(current_context.name)
        if current_context
        else None
    )
    if not credentials:
        credentials = config_manager.load_credentials()
    if credentials and "token" in credentials:
        headers["Authorization"] = f"Bearer {credentials['token']}"
    return headers


async def _api_get(path: str) -> dict:
    base = _get_base_url()
    headers = _get_auth_headers()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{base}{_GOOGLE_PATH}{path}", headers=headers, timeout=30
        )
        return (
            resp.json()
            if resp.status_code < 500
            else {"error": f"Server error {resp.status_code}"}
        )


async def _api_post(path: str, data: dict | None = None) -> dict:
    base = _get_base_url()
    headers = _get_auth_headers()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}{_GOOGLE_PATH}{path}", json=data or {}, headers=headers, timeout=30
        )
        return (
            resp.json()
            if resp.status_code < 500
            else {"error": f"Server error {resp.status_code}"}
        )


async def _api_delete(path: str) -> dict:
    base = _get_base_url()
    headers = _get_auth_headers()
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{base}{_GOOGLE_PATH}{path}", headers=headers, timeout=30
        )
        try:
            return resp.json()
        except Exception:
            return {"status": "ok"}


@app.command("connect")
def calendar_connect() -> None:
    """Connect Google Calendar account (browser OAuth flow)."""

    async def _do():
        data = await _api_post("/auth-url/")
        if data.get("error"):
            console.print(f"[red]Error: {data['error']}[/red]")
            raise typer.Exit(1)
        auth_url = data.get("auth_url", "")
        console.print(
            "[bold]Open this URL in your browser to authorise TodoPro:[/bold]"
        )
        console.print(f"  {auth_url}")
        console.print()
        code = typer.prompt("Enter authorisation code")
        result = await _api_post("/auth-callback/", {"code": code})
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        email = result.get("email", "")
        msg = f"✓ Connected to Google Calendar{' as ' + email if email else ''}"
        console.print(f"[green]{msg}[/green]")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("disconnect")
def calendar_disconnect() -> None:
    """Disconnect Google Calendar account."""

    async def _do():
        await _api_delete("/disconnect/")
        console.print("[green]✓ Google Calendar disconnected[/green]")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("status")
def calendar_status() -> None:
    """Show Google Calendar connection status."""

    async def _do():
        data = await _api_get("/status/")
        if data.get("error"):
            console.print(f"[red]Error: {data['error']}[/red]")
            raise typer.Exit(1)
        if data.get("connected"):
            email = data.get("email", "")
            connected_at = data.get("connected_at", "")
            console.print(
                f"[green]● Connected[/green]{' as ' + email if email else ''}"
            )
            if connected_at:
                console.print(f"  Connected at: {connected_at}")
        else:
            console.print("[yellow]○ Not connected[/yellow]")
            console.print("  Run: [bold]todopro calendar connect[/bold]")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("list")
def calendar_list(
    resource: str = typer.Argument("calendars", help="Resource to list (calendars)"),
) -> None:
    """List Google Calendar resources."""
    if resource != "calendars":
        console.print(f"[red]Unknown resource: {resource}. Use: calendars[/red]")
        raise typer.Exit(1)

    async def _do():
        data = await _api_get("/calendars/")
        if data.get("error"):
            console.print(f"[red]Error: {data['error']}[/red]")
            raise typer.Exit(1)
        calendars = data.get("calendars", [])
        if not calendars:
            console.print("No calendars found.")
            return
        table = Table(title="Google Calendars")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Timezone", style="yellow")
        for cal in calendars:
            table.add_row(
                cal.get("id", ""), cal.get("summary", ""), cal.get("timeZone", "")
            )
        console.print(table)

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("set")
def calendar_set(
    resource: str = typer.Argument(..., help="Resource to set (default)"),
    calendar_id: str = typer.Argument(..., help="Calendar ID"),
) -> None:
    """Set Google Calendar configuration (e.g., default calendar)."""
    if resource != "default":
        console.print(f"[red]Unknown resource: {resource}[/red]")
        raise typer.Exit(1)

    async def _do():
        result = await _api_post("/config/", {"default_calendar_id": calendar_id})
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✓ Default calendar set to: {calendar_id}[/green]")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("push")
def calendar_push(
    project: str | None = typer.Option(None, "--project", help="Project ID to push"),
    label: str | None = typer.Option(None, "--label", help="Label to filter tasks"),
) -> None:
    """Push tasks with due dates to Google Calendar."""

    async def _do():
        payload: dict = {}
        if project:
            payload["project_id"] = project
        if label:
            payload["label"] = label
        result = await _api_post("/push/", payload)
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        console.print(
            f"[green]✓ Created {created} events, updated {updated}, skipped {skipped}[/green]"
        )

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("pull")
def calendar_pull(
    calendar_id: str | None = typer.Option(
        None, "--calendar-id", help="Calendar ID to pull from"
    ),
    date_from: str | None = typer.Option(
        None, "--from", help="Start date (YYYY-MM-DD)"
    ),
    date_to: str | None = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
) -> None:
    """Pull Google Calendar events as tasks."""

    async def _do():
        payload: dict = {}
        if calendar_id:
            payload["calendar_id"] = calendar_id
        if date_from:
            payload["from"] = date_from
        if date_to:
            payload["to"] = date_to
        result = await _api_post("/pull/", payload)
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        created = result.get("created", 0)
        skipped = result.get("skipped", 0)
        console.print(f"[green]✓ Created {created} tasks, skipped {skipped}[/green]")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("sync")
def calendar_sync(
    show_status: bool = typer.Option(
        False, "--status", help="Show sync status instead of syncing"
    ),
) -> None:
    """Two-way incremental sync with Google Calendar."""

    async def _do():
        if show_status:
            data = await _api_get("/sync/status/")
            if data.get("error"):
                console.print(f"[red]Error: {data['error']}[/red]")
                raise typer.Exit(1)
            last = data.get("last_synced_at")
            stats = data.get("stats", {})
            console.print(f"Last synced: {last or 'Never'}")
            if stats:
                console.print(f"Last stats: {stats}")
            return
        result = await _api_post("/sync/")
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        console.print(
            f"[green]✓ Sync complete: created {created}, updated {updated}, skipped {skipped}[/green]"
        )

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("configure")
def calendar_configure(
    push_on_create: bool | None = typer.Option(
        None,
        "--push-on-create/--no-push-on-create",
        help="Push to calendar when task created",
    ),
    push_on_complete: bool | None = typer.Option(
        None,
        "--push-on-complete/--no-push-on-complete",
        help="Update calendar when task completed",
    ),
) -> None:
    """Configure Google Calendar auto-sync rules."""

    async def _do():
        config: dict = {}
        if push_on_create is not None:
            config["push_on_create"] = push_on_create
        if push_on_complete is not None:
            config["push_on_complete"] = push_on_complete
        result = await _api_post("/config/", {"config": config})
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        console.print("[green]✓ Configuration saved[/green]")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("describe")
def calendar_describe(
    resource: str = typer.Argument("config", help="Resource to describe (config)"),
) -> None:
    """Describe Google Calendar configuration."""
    if resource != "config":
        console.print(f"[red]Unknown resource: {resource}[/red]")
        raise typer.Exit(1)

    async def _do():
        data = await _api_get("/config/")
        if data.get("error"):
            console.print(f"[red]Error: {data['error']}[/red]")
            raise typer.Exit(1)
        config = data.get("config", {})
        if not config:
            console.print("No configuration set.")
        else:
            for key, value in config.items():
                console.print(f"  {key}: {value}")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
