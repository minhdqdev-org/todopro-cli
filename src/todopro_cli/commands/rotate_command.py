"""Rotate command - Rotate encryption key."""

import typer
from rich.console import Console

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Rotate encryption key")
console = Console()


@app.command("encryption-key")
@command_wrapper
async def rotate_encryption_key(
    new_passphrase: str | None = typer.Option(
        None, "--passphrase", help="New passphrase"
    ),
) -> None:
    """Rotate encryption key."""
    from todopro_cli.services.encryption_service import EncryptionService

    if not new_passphrase:
        new_passphrase = typer.prompt(
            "Enter new encryption passphrase", hide_input=True
        )

    service = EncryptionService()
    new_recovery_key = await service.rotate_key(new_passphrase)

    format_success("Encryption key rotated successfully")
    console.print("\n[bold yellow]⚠️  New Recovery Key:[/bold yellow]")
    console.print(f"[bold]{new_recovery_key}[/bold]\n")
