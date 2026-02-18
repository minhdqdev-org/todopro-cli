"""Command 'update' of todopro-cli"""

import subprocess

import typer

from todopro_cli import __version__
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.update_checker import is_update_available

app = typer.Typer()
console = get_console()


@app.command()
def update(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Update TodoPro CLI to the latest version."""

    console.print("[bold]Checking for updates...[/bold]")

    try:
        is_available, latest_version = is_update_available()

        if not is_available:
            if latest_version:
                console.print(
                    f"[green]✓[/green] You're already on the latest version ([cyan]{__version__}[/cyan])"
                )
            else:
                console.print(
                    "[yellow]⚠[/yellow] Unable to check for updates. Please try again later."
                )
            return

        console.print(
            f"\n[green]✨ New version available:[/green] [bold cyan]{latest_version}[/bold cyan]"
        )
        console.print(f"[dim]Current version: {__version__}[/dim]\n")

        # Prompt user if not in non-interactive mode
        if not yes:
            confirm = typer.confirm("Do you want to update now?", default=True)
            if not confirm:
                console.print("[yellow]Update cancelled.[/yellow]")
                return

        console.print("\n[bold]Updating TodoPro CLI...[/bold]")

        # Run uv tool upgrade
        result = subprocess.run(
            ["uv", "tool", "upgrade", "todopro-cli"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            console.print(
                f"\n[green]✓ Successfully updated to version {latest_version}![/green]"
            )
            console.print("[dim]Run 'todopro version' to verify the update.[/dim]")
        else:
            console.print("\n[red]✗ Update failed.[/red]")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            console.print("\n[yellow]You can try updating manually with:[/yellow]")
            console.print("  [cyan]uv tool upgrade todopro-cli[/cyan]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]✗ 'uv' command not found. Please install uv first:[/red]")
        console.print("  [cyan]curl -LsSf https://astral.sh/uv/install.sh | sh[/cyan]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        raise typer.Exit(1) from e
