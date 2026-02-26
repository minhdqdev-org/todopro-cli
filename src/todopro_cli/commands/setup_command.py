"""Setup command - Setup encryption."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output, format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Setup encryption")
console = get_console()


@app.command("encryption")
@command_wrapper
async def setup_encryption(
    passphrase: str | None = typer.Option(
        None, "--passphrase", help="Encryption passphrase"
    ),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Setup end-to-end encryption."""
    from todopro_cli.services.encryption_service import EncryptionService

    service = EncryptionService()

    if not passphrase:
        passphrase = typer.prompt("Enter encryption passphrase", hide_input=True)

    recovery_key = await service.setup(passphrase)

    format_success("Encryption setup complete")
    console.print("\n[bold yellow]⚠️  IMPORTANT: Save your recovery key![/bold yellow]")
    console.print(f"Recovery Key: [bold]{recovery_key}[/bold]\n")

    format_output({"recovery_key": recovery_key}, output)
