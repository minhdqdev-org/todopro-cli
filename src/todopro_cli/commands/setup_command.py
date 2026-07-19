"""Setup command - Setup encryption.

Deprecated: end-to-end encryption was dropped per ADR-0024. This command is
kept registered (so scripts/`--help` don't break) but no longer sets up a
key or enables encryption — see `docs/adr/ADR-0024-drop-e2ee.md`.
"""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Setup encryption (discontinued)")
console = get_console()


@app.command("encryption")
@command_wrapper
async def setup_encryption(
    passphrase: str | None = typer.Option(
        None, "--passphrase", help="Encryption passphrase (unused, discontinued)"
    ),
    output: str = typer.Option(
        "table", "--output", "-o", help="Output format (unused, discontinued)"
    ),
) -> None:
    """[Discontinued] End-to-end encryption setup (ADR-0024)."""
    del passphrase, output  # kept for CLI/signature compatibility only

    console.print(
        "\n[yellow]End-to-end encryption has been discontinued (ADR-0024).[/yellow]"
    )
    console.print(
        "Your tasks now sync as plaintext, like every other TodoPro surface "
        "(web, mobile) — no encryption key is needed.\n"
    )
