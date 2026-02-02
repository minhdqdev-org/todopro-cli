"""Data management commands (import, export, purge)."""

import asyncio
import gzip
import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from todopro_cli.api.client import get_client
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import (
    format_error,
    format_info,
    format_success,
    format_warning,
)
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Data management commands")
console = Console()


def check_auth(profile: str = "default") -> None:
    """Check if user is authenticated."""
    config_manager = get_config_manager(profile)
    credentials = config_manager.load_credentials()
    if not credentials:
        format_error("Not logged in. Use 'todopro login' to authenticate.")
        raise typer.Exit(3)  # Exit code 3: Authentication failure


@app.command("export")
def export_data(
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: todopro-export-{timestamp}.json)",
    ),
    compress: bool = typer.Option(
        False,
        "--compress",
        "-z",
        help="Compress output with gzip",
    ),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """
    Export all your data (tasks, projects, labels, contexts) to JSON.
    
    Examples:
        todopro data export
        todopro data export --output backup.json
        todopro data export --compress
    """
    check_auth(profile)

    try:
        async def do_export() -> None:
            client = get_client(profile)
            
            format_info("Exporting your data...")
            
            # Call export API
            params = {}
            if compress:
                params['compress'] = 'true'
            
            response = await client.request("GET", "/api/export/data", params=params)
            
            # Determine output filename
            if output is None:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                extension = ".json.gz" if compress else ".json"
                filename = f"todopro-export-{timestamp}{extension}"
            else:
                filename = output
            
            # Write to file
            output_path = Path(filename)
            
            if compress and isinstance(response, bytes):
                # Response is already gzipped
                output_path.write_bytes(response)
            elif isinstance(response, dict):
                # JSON response - write as JSON file
                output_path.write_text(json.dumps(response, indent=2))
            else:
                format_error("Unexpected response format from server")
                raise typer.Exit(1)
            
            # Show stats
            if isinstance(response, dict):
                stats = response.get('stats', {})
                
                table = Table(title="Export Summary", show_header=True)
                table.add_column("Type", style="cyan")
                table.add_column("Count", justify="right", style="green")
                
                table.add_row("Tasks", str(stats.get('tasks_count', 0)))
                table.add_row("Projects", str(stats.get('projects_count', 0)))
                table.add_row("Labels", str(stats.get('labels_count', 0)))
                table.add_row("Contexts", str(stats.get('contexts_count', 0)))
                
                console.print(table)
                
                # Show encryption status
                encryption = response.get('encryption', {})
                if encryption.get('enabled'):
                    format_info("🔐 Data includes encrypted fields")
            
            format_success(f"✓ Data exported to: {output_path.absolute()}")
            
            await client.close()

        asyncio.run(do_export())

    except Exception as e:
        format_error(f"Export failed: {str(e)}")
        raise typer.Exit(4)  # Exit code 4: Network/API error


@app.command("import")
def import_data(
    file: str = typer.Argument(..., help="JSON file to import"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """
    Import data from JSON file (exported via 'export' command).
    
    This will merge imported data with your existing data.
    Existing items with the same name will be skipped.
    
    Examples:
        todopro data import backup.json
        todopro data import backup.json --yes
    """
    check_auth(profile)
    
    file_path = Path(file)
    
    # Validate file exists
    if not file_path.exists():
        format_error(f"File not found: {file}")
        raise typer.Exit(5)  # Exit code 5: Resource not found
    
    # Read and parse file
    try:
        if file_path.suffix == '.gz':
            with gzip.open(file_path, 'rt') as f:
                data = json.load(f)
        else:
            with file_path.open() as f:
                data = json.load(f)
    except json.JSONDecodeError as e:
        format_error(f"Invalid JSON file: {str(e)}")
        raise typer.Exit(2)  # Exit code 2: Invalid arguments
    except Exception as e:
        format_error(f"Failed to read file: {str(e)}")
        raise typer.Exit(1)
    
    # Show preview
    stats = data.get('stats', {})
    
    table = Table(title="Import Preview", show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right", style="yellow")
    
    table.add_row("Tasks", str(stats.get('tasks_count', len(data.get('data', {}).get('tasks', [])))))
    table.add_row("Projects", str(stats.get('projects_count', len(data.get('data', {}).get('projects', [])))))
    table.add_row("Labels", str(stats.get('labels_count', len(data.get('data', {}).get('labels', [])))))
    table.add_row("Contexts", str(stats.get('contexts_count', len(data.get('data', {}).get('contexts', [])))))
    
    console.print(table)
    
    format_info("Note: Existing items with the same name will be skipped")
    
    # Confirm import
    if not yes:
        if not Confirm.ask("Do you want to import this data?"):
            format_info("Import cancelled")
            raise typer.Exit(0)
    
    try:
        async def do_import() -> None:
            client = get_client(profile)
            
            format_info("Importing data...")
            
            # Call import API
            response = await client.request("POST", "/api/import/data", json=data)
            
            # Show results
            if isinstance(response, dict):
                summary = response.get('summary', {})
                
                table = Table(title="Import Results", show_header=True)
                table.add_column("Type", style="cyan")
                table.add_column("Result", style="green")
                
                table.add_row("Projects", summary.get('projects', 'N/A'))
                table.add_row("Labels", summary.get('labels', 'N/A'))
                table.add_row("Contexts", summary.get('contexts', 'N/A'))
                table.add_row("Tasks", summary.get('tasks', 'N/A'))
                
                console.print(table)
                
                # Show errors if any
                details = response.get('details', {})
                total_errors = sum(len(d.get('errors', [])) for d in details.values())
                
                if total_errors > 0:
                    format_warning(f"⚠ {total_errors} error(s) occurred during import")
                    for resource_type, resource_details in details.items():
                        errors = resource_details.get('errors', [])
                        if errors:
                            format_error(f"\n{resource_type.capitalize()} errors:")
                            for error in errors[:5]:  # Show first 5 errors
                                console.print(f"  - {error}")
                            if len(errors) > 5:
                                console.print(f"  ... and {len(errors) - 5} more")
                
                format_success("✓ Import completed")
            
            await client.close()

        asyncio.run(do_import())

    except Exception as e:
        format_error(f"Import failed: {str(e)}")
        raise typer.Exit(4)  # Exit code 4: Network/API error


@app.command("purge")
def purge_data(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what would be deleted without actually deleting",
    ),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """
    Delete ALL your data (tasks, projects, labels, contexts, encryption keys).
    
    ⚠️  WARNING: This action CANNOT be undone!
    
    You should export your data first:
        todopro data export --output backup.json
    
    Examples:
        todopro data purge --dry-run  # Preview only
        todopro data purge             # Actually delete
    """
    check_auth(profile)
    
    # Get user info
    config_manager = get_config_manager(profile)
    credentials = config_manager.load_credentials()
    user_email = credentials.get('email', 'your email')
    
    try:
        async def do_purge() -> None:
            client = get_client(profile)
            
            if dry_run:
                format_info("Running in dry-run mode (no data will be deleted)...")
                params = {'dry_run': 'true'}
                payload = {
                    'confirm': 'DELETE',
                    'username': user_email
                }
                
                response = await client.request("POST", "/api/purge/data", params=params, json=payload)
                
                if isinstance(response, dict):
                    items = response.get('items_to_delete', {})
                    
                    table = Table(title="Dry Run - Items That Would Be Deleted", show_header=True)
                    table.add_column("Type", style="cyan")
                    table.add_column("Count", justify="right", style="red")
                    
                    table.add_row("Tasks", str(items.get('tasks', 0)))
                    table.add_row("Projects", str(items.get('projects', 0)))
                    table.add_row("Labels", str(items.get('labels', 0)))
                    table.add_row("Contexts", str(items.get('contexts', 0)))
                    table.add_row("Total", str(response.get('total_items', 0)), style="bold red")
                    
                    console.print(table)
                    format_info("This was a dry run. No data was deleted.")
                
                await client.close()
                return
            
            # Actual purge - show warning
            format_warning("⚠️  WARNING: You are about to delete ALL your data!")
            format_warning("⚠️  This action CANNOT be undone!")
            console.print()
            
            # First confirmation: explain what will be deleted
            format_info("The following will be permanently deleted:")
            console.print("  • All tasks")
            console.print("  • All projects")
            console.print("  • All labels")
            console.print("  • All contexts")
            console.print("  • All encryption keys")
            console.print()
            
            if not Confirm.ask("Do you want to continue?", default=False):
                format_info("Purge cancelled")
                raise typer.Exit(0)
            
            # Second confirmation: type username
            console.print()
            format_warning("Please type your email address to confirm:")
            typed_email = Prompt.ask("Email")
            
            if typed_email != user_email:
                format_error("Email does not match. Purge cancelled.")
                raise typer.Exit(0)
            
            # Third confirmation: final warning
            console.print()
            format_warning("FINAL WARNING: All your data will be permanently deleted!")
            if not Confirm.ask("Are you absolutely sure?", default=False):
                format_info("Purge cancelled")
                raise typer.Exit(0)
            
            # Perform purge
            format_info("Deleting all data...")
            
            payload = {
                'confirm': 'DELETE',
                'username': user_email
            }
            
            response = await client.request("POST", "/api/purge/data", json=payload)
            
            if isinstance(response, dict):
                deleted = response.get('deleted', {})
                
                table = Table(title="Deletion Summary", show_header=True)
                table.add_column("Type", style="cyan")
                table.add_column("Deleted", justify="right", style="red")
                
                table.add_row("Tasks", str(deleted.get('tasks', 0)))
                table.add_row("Projects", str(deleted.get('projects', 0)))
                table.add_row("Labels", str(deleted.get('labels', 0)))
                table.add_row("Contexts", str(deleted.get('contexts', 0)))
                
                console.print(table)
                
                if response.get('encryption_cleared'):
                    format_info("🔐 Encryption keys cleared")
                
                format_success("✓ All data has been permanently deleted")
            
            await client.close()

        asyncio.run(do_purge())

    except Exception as e:
        format_error(f"Purge failed: {str(e)}")
        raise typer.Exit(4)  # Exit code 4: Network/API error
