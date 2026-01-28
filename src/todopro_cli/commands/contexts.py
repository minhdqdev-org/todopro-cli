"""Context management commands for TodoPro CLI."""

import click
from rich.console import Console
from rich.table import Table
from todopro_cli.api.client import APIClient
from todopro_cli.commands.utils import handle_api_error

console = Console()


@click.group()
def contexts():
    """Manage task contexts (@home, @office, @errands)."""
    pass


@contexts.command("list")
@click.option("--location", "-l", is_flag=True, help="Request location for availability check")
def list_contexts(location):
    """List all contexts."""
    client = APIClient()
    
    try:
        # Get location if requested
        lat, lon = None, None
        if location:
            try:
                import geocoder
                g = geocoder.ip('me')
                if g.ok:
                    lat, lon = g.latlng
                    console.print(f"[blue]📍 Your location: {lat:.4f}, {lon:.4f}[/blue]")
            except ImportError:
                console.print("[yellow]Install 'geocoder' package for location detection[/yellow]")
        
        # Build query params
        params = {}
        if lat and lon:
            params['lat'] = lat
            params['lon'] = lon
        
        response = client.get("/v1/contexts", params=params)
        contexts_data = response if isinstance(response, list) else []
        
        if not contexts_data:
            console.print("[yellow]No contexts found. Create one with 'todopro contexts create'[/yellow]")
            return
        
        # Display table
        table = Table(title="Contexts", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Tasks", justify="right")
        table.add_column("Icon")
        table.add_column("Geo-Fence")
        table.add_column("Available", justify="center")
        
        for ctx in contexts_data:
            has_geo = bool(ctx.get('latitude') and ctx.get('longitude') and ctx.get('radius'))
            geo_info = f"{ctx['radius']}m" if has_geo else "—"
            
            available = "—"
            if ctx.get('is_available') is True:
                available = "✓ HERE"
            elif ctx.get('is_available') is False:
                available = "✗"
            
            table.add_row(
                ctx['name'],
                str(ctx.get('task_count', 0)),
                ctx.get('icon', '📍'),
                geo_info,
                available
            )
        
        console.print(table)
        
    except Exception as e:
        handle_api_error(e, "listing contexts")


@contexts.command("create")
@click.argument("name")
@click.option("--icon", default="📍", help="Context icon (emoji)")
@click.option("--color", default="#3498DB", help="Context color (hex)")
@click.option("--geo", is_flag=True, help="Enable geo-fencing at current location")
@click.option("--radius", default=200, type=int, help="Geo-fence radius in meters")
def create_context(name, icon, color, geo, radius):
    """Create a new context."""
    client = APIClient()
    
    data = {
        "name": name,
        "icon": icon,
        "color": color
    }
    
    if geo:
        try:
            import geocoder
            g = geocoder.ip('me')
            if g.ok:
                lat, lon = g.latlng
                data['latitude'] = lat
                data['longitude'] = lon
                data['radius'] = radius
                console.print(f"[blue]📍 Geo-fence: {lat:.4f}, {lon:.4f} (radius: {radius}m)[/blue]")
            else:
                console.print("[red]Could not detect location[/red]")
                return
        except ImportError:
            console.print("[red]Install 'geocoder' package: pip install geocoder[/red]")
            return
    
    try:
        result = client.post("/v1/contexts", data)
        console.print(f"[green]✓ Created context: {result['name']}[/green]")
    except Exception as e:
        handle_api_error(e, "creating context")


@contexts.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to delete this context?")
def delete_context(name):
    """Delete a context."""
    client = APIClient()
    
    try:
        # Find context by name
        contexts_data = client.get("/v1/contexts")
        context = next((c for c in contexts_data if c['name'] == name or c['name'] == f"@{name}"), None)
        
        if not context:
            console.print(f"[red]Context '{name}' not found[/red]")
            return
        
        client.delete(f"/v1/contexts/{context['id']}")
        console.print(f"[green]✓ Deleted context: {context['name']}[/green]")
        
    except Exception as e:
        handle_api_error(e, "deleting context")


@contexts.command("tasks")
@click.argument("name")
def context_tasks(name):
    """List tasks for a specific context."""
    client = APIClient()
    
    try:
        # Find context
        contexts_data = client.get("/v1/contexts")
        context = next((c for c in contexts_data if c['name'] == name or c['name'] == f"@{name}"), None)
        
        if not context:
            console.print(f"[red]Context '{name}' not found[/red]")
            return
        
        # Get tasks
        result = client.get(f"/v1/contexts/{context['id']}/tasks")
        tasks = result.get('tasks', [])
        
        if not tasks:
            console.print(f"[yellow]No tasks in context '{context['name']}'[/yellow]")
            return
        
        console.print(f"\n[bold]{context['icon']} {context['name']}[/bold] — {len(tasks)} tasks\n")
        
        for task in tasks:
            status = "✓" if task.get('is_completed') else "○"
            priority = f"P{task.get('priority', 1)}"
            console.print(f"{status} {task['content']} [{priority}]")
        
    except Exception as e:
        handle_api_error(e, "listing context tasks")


@contexts.command("check")
def check_available():
    """Check which contexts are available at current location."""
    client = APIClient()
    
    try:
        import geocoder
        g = geocoder.ip('me')
        if not g.ok:
            console.print("[red]Could not detect location[/red]")
            return
        
        lat, lon = g.latlng
        console.print(f"[blue]📍 Checking location: {lat:.4f}, {lon:.4f}[/blue]\n")
        
        result = client.post("/v1/contexts/check-available", {
            "latitude": lat,
            "longitude": lon
        })
        
        available = result.get('available', [])
        unavailable = result.get('unavailable', [])
        
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
        
    except ImportError:
        console.print("[red]Install 'geocoder' package: pip install geocoder[/red]")
    except Exception as e:
        handle_api_error(e, "checking available contexts")
