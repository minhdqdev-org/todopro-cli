"""Recover command - Recover encryption."""

import typer
from rich.console import Console

from todopro_cli.utils.ui.formatters import format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Recover encryption")
console = Console()


@app.command("encryption")
@command_wrapper
async def recover_encryption(
    recovery_key: str = typer.Argument(..., help="Recovery key"),
) -> None:
    """Recover encryption using recovery key."""
    from todopro_cli.services.encryption_service import EncryptionService

    service = EncryptionService()
    await service.recover(recovery_key)
    format_success("Encryption recovered successfully")
