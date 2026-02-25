"""Recover command - Recover encryption."""

import typer

from todopro_cli.services.encryption_service import get_encryption_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Recover encryption")
console = get_console()


@app.command("encryption")
@command_wrapper
async def recover_encryption(
    recovery_key: str = typer.Argument(..., help="Recovery key"),
) -> None:
    """Recover encryption using recovery key."""

    await get_encryption_service().recover(recovery_key)

    format_success("Encryption recovered successfully")
