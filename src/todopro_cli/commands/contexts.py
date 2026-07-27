"""Context management commands for TodoPro CLI."""

from typing import Any

import typer
from rich.table import Table

from todopro_cli.services.api.client import APIClient
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.ui.console import get_console

from .utils import handle_api_error

console = get_console()
app = typer.Typer(help="Manage task contexts (@home, @office, @errands)")

# The third party `geocoder.ip("me")` talks to. Named explicitly so the consent
# prompt can say *who* receives the user's IP rather than hand-waving.
GEOIP_PROVIDER = "ipinfo.io (via the `geocoder` package)"

_CONSENT_DISCLOSURE = (
    "\n[bold yellow]Location lookup requires sending your IP address to a "
    "third party.[/bold yellow]\n"
    f"TodoPro would ask [cyan]{GEOIP_PROVIDER}[/cyan] to estimate your "
    "location from your public IP address.\n"
    "Your IP address is personal data and this service is operated by "
    "someone other than TodoPro.\n"
    "You can skip this entirely by passing coordinates yourself with "
    "[cyan]--lat[/cyan] and [cyan]--lon[/cyan].\n"
)


def _geoip_consent_granted() -> bool:
    """Return whether the user has consented to third-party geo-IP lookups.

    Asks once, on first use, and persists the answer in
    ``~/.config/todopro_cli/config.json`` under ``privacy.geoip_consent``.
    A non-interactive session (no TTY, piped input) counts as "no": we must
    never make the call on a silent default.
    """
    config_svc = get_config_service()
    privacy = config_svc.config.privacy
    if privacy.geoip_consent is not None:
        return privacy.geoip_consent

    console.print(_CONSENT_DISCLOSURE)
    try:
        granted = typer.confirm(
            f"Allow TodoPro to send your IP address to {GEOIP_PROVIDER}?",
            default=False,
        )
    except (typer.Abort, EOFError):
        # Non-interactive: decline, and don't persist — the user never saw the
        # question, so a later interactive run should still get to answer it.
        console.print(
            "[yellow]No answer available (non-interactive session); "
            "skipping location lookup.[/yellow]"
        )
        return False

    privacy.geoip_consent = granted
    config_svc.save_config()
    if granted:
        console.print(
            "[dim]Saved. Revoke any time with: "
            "[cyan]todopro config set privacy.geoip_consent false[/cyan][/dim]"
        )
    else:
        console.print(
            "[dim]Saved. No location lookup will be performed. Pass --lat/--lon "
            "to use contexts' geo features.[/dim]"
        )
    return granted


def _resolve_location(
    lat: float | None, lon: float | None
) -> tuple[float | None, float | None]:
    """Resolve coordinates for a geo-aware command.

    Explicit ``--lat``/``--lon`` always win and never trigger a network call.
    Otherwise a third-party geo-IP lookup is attempted, but only after the
    user has been told what it does and has consented.
    """
    if lat is not None and lon is not None:
        return lat, lon
    if lat is not None or lon is not None:
        console.print("[red]Pass both --lat and --lon, or neither.[/red]")
        return None, None

    if not _geoip_consent_granted():
        return None, None

    try:
        import geocoder
    except ImportError:
        console.print(
            "[yellow]Install the 'geocoder' package for location detection, "
            "or pass --lat/--lon.[/yellow]"
        )
        return None, None

    g = geocoder.ip("me")
    if not g.ok:
        console.print("[red]Could not detect location[/red]")
        return None, None
    resolved_lat, resolved_lon = g.latlng
    console.print(f"[blue]📍 Your location: {resolved_lat:.4f}, {resolved_lon:.4f}[/blue]")
    return resolved_lat, resolved_lon


@app.command("list")
def list_contexts(
    location: bool = typer.Option(
        False, "--location", "-l", help="Request location for availability check"
    ),
    lat: float | None = typer.Option(
        None, "--lat", help="Latitude to use instead of a geo-IP lookup"
    ),
    lon: float | None = typer.Option(
        None, "--lon", help="Longitude to use instead of a geo-IP lookup"
    ),
):
    """List all contexts."""
    client = APIClient()

    try:
        # Availability needs coordinates. They must NOT travel as query
        # params — query strings land in nginx/LB access logs and Sentry
        # breadcrumbs in cleartext, which would put the user's real-time
        # position in plaintext logs. The dedicated endpoint takes them in
        # the POST body instead.
        if location or lat is not None or lon is not None:
            user_lat, user_lon = _resolve_location(lat, lon)
        else:
            user_lat, user_lon = None, None

        response = client.get("/v1/contexts")
        contexts_data = response if isinstance(response, list) else []

        if user_lat is not None and user_lon is not None:
            availability: Any = (
                client.post(
                    "/v1/contexts/check-available",
                    {"latitude": user_lat, "longitude": user_lon},
                )
                or {}
            )
            available_ids = {ctx["id"] for ctx in availability.get("available", [])}
            unavailable_ids = {ctx["id"] for ctx in availability.get("unavailable", [])}
            for ctx in contexts_data:
                if ctx.get("id") in available_ids:
                    ctx["is_available"] = True
                elif ctx.get("id") in unavailable_ids:
                    ctx["is_available"] = False

        if not contexts_data:
            console.print(
                "[yellow]No contexts found. Create one with 'todopro contexts create'[/yellow]"
            )
            return

        # Display table
        table = Table(title="Contexts", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Tasks", justify="right")
        table.add_column("Icon")
        table.add_column("Geo-Fence")
        table.add_column("Available", justify="center")

        for ctx in contexts_data:
            has_geo = bool(
                ctx.get("latitude") and ctx.get("longitude") and ctx.get("radius")
            )
            geo_info = f"{ctx['radius']}m" if has_geo else "—"

            available = "—"
            if ctx.get("is_available") is True:
                available = "✓ HERE"
            elif ctx.get("is_available") is False:
                available = "✗"

            table.add_row(
                ctx["name"],
                str(ctx.get("task_count", 0)),
                ctx.get("icon", "📍"),
                geo_info,
                available,
            )

        console.print(table)

    except Exception as e:
        handle_api_error(e, "listing contexts")


@app.command("create")
def create_context(
    name: str = typer.Argument(..., help="Context name"),
    icon: str = typer.Option("📍", help="Context icon (emoji)"),
    color: str = typer.Option("#3498DB", help="Context color (hex)"),
    geo: bool = typer.Option(
        False, "--geo", help="Enable geo-fencing at current location"
    ),
    radius: int = typer.Option(200, help="Geo-fence radius in meters"),
    lat: float | None = typer.Option(
        None, "--lat", help="Latitude to use instead of a geo-IP lookup"
    ),
    lon: float | None = typer.Option(
        None, "--lon", help="Longitude to use instead of a geo-IP lookup"
    ),
):
    """Create a new context."""
    client = APIClient()

    data: dict[str, Any] = {"name": name, "icon": icon, "color": color}

    if geo or lat is not None or lon is not None:
        fence_lat, fence_lon = _resolve_location(lat, lon)
        if fence_lat is None or fence_lon is None:
            return
        data["latitude"] = fence_lat
        data["longitude"] = fence_lon
        data["radius"] = radius
        console.print(
            f"[blue]📍 Geo-fence: {fence_lat:.4f}, {fence_lon:.4f} "
            f"(radius: {radius}m)[/blue]"
        )

    try:
        result = client.post("/v1/contexts", data)
        console.print(f"[green]✓ Created context: {result['name']}[/green]")
    except Exception as e:
        handle_api_error(e, "creating context")


@app.command("delete")
def delete_context(
    name: str = typer.Argument(..., help="Context name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a context."""
    if not yes:
        confirmed = typer.confirm("Are you sure you want to delete this context?")
        if not confirmed:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    client = APIClient()

    try:
        # Find context by name
        contexts_data = client.get("/v1/contexts")
        context = next(
            (c for c in contexts_data if c["name"] == name or c["name"] == f"@{name}"),
            None,
        )

        if not context:
            console.print(f"[red]Context '{name}' not found[/red]")
            return

        client.delete(f"/v1/contexts/{context['id']}")
        console.print(f"[green]✓ Deleted context: {context['name']}[/green]")

    except Exception as e:
        handle_api_error(e, "deleting context")


@app.command("tasks")
def context_tasks(
    name: str = typer.Argument(..., help="Context name"),
):
    """List tasks for a specific context."""
    client = APIClient()

    try:
        # Find context
        contexts_data = client.get("/v1/contexts")
        context = next(
            (c for c in contexts_data if c["name"] == name or c["name"] == f"@{name}"),
            None,
        )

        if not context:
            console.print(f"[red]Context '{name}' not found[/red]")
            return

        # Get tasks
        result = client.get(f"/v1/contexts/{context['id']}/tasks")
        tasks = result.get("tasks", [])

        if not tasks:
            console.print(f"[yellow]No tasks in context '{context['name']}'[/yellow]")
            return

        console.print(
            f"\n[bold]{context['icon']} {context['name']}[/bold] — {len(tasks)} tasks\n"
        )

        for task in tasks:
            status = "✓" if task.get("is_completed") else "○"
            priority = f"P{task.get('priority', 1)}"
            console.print(f"{status} {task['content']} [{priority}]")

    except Exception as e:
        handle_api_error(e, "listing context tasks")


@app.command("check")
def check_available(
    lat: float | None = typer.Option(
        None, "--lat", help="Latitude to use instead of a geo-IP lookup"
    ),
    lon: float | None = typer.Option(
        None, "--lon", help="Longitude to use instead of a geo-IP lookup"
    ),
):
    """Check which contexts are available at current location."""
    client = APIClient()

    try:
        user_lat, user_lon = _resolve_location(lat, lon)
        if user_lat is None or user_lon is None:
            return

        console.print(
            f"[blue]📍 Checking location: {user_lat:.4f}, {user_lon:.4f}[/blue]\n"
        )

        result = client.post(
            "/v1/contexts/check-available",
            {"latitude": user_lat, "longitude": user_lon},
        )

        available = result.get("available", [])
        unavailable = result.get("unavailable", [])

        if available:
            console.print("[bold green]✓ Available Contexts:[/bold green]")
            for ctx in available:
                console.print(f"  {ctx['icon']} {ctx['name']}")
            console.print()

        if unavailable:
            console.print("[bold dim]✗ Not Available:[/bold dim]")
            for ctx in unavailable:
                console.print(f"  {ctx['icon']} {ctx['name']}")

        if not available and not unavailable:
            console.print("[yellow]No geo-fenced contexts configured[/yellow]")

    except Exception as e:
        handle_api_error(e, "checking available contexts")
