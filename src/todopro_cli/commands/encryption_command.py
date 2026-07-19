"""Encryption management commands for TodoPro CLI.

Deprecated: end-to-end encryption was dropped per ADR-0024
(`docs/adr/ADR-0024-drop-e2ee.md`). `setup` no longer generates a key or
enables encryption, and `status` reports the feature as discontinued. The
commands stay registered (so scripts/`--help` don't break), and the
recovery/rotate commands are left as dormant, unreachable code paths since
nothing can enable encryption anymore.
"""

import typer
from rich.panel import Panel
from rich.text import Text

from todopro_cli.models.crypto.exceptions import TodoProCryptoError
from todopro_cli.services.encryption_service import EncryptionService
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(help="Manage end-to-end encryption")
console = get_console()


def get_encryption_service() -> EncryptionService:
    """Get encryption service instance."""
    return EncryptionService()


@app.command("setup")
def setup():
    """
    [Discontinued] End-to-end encryption setup (ADR-0024).

    E2EE has been dropped as a shipped feature. This command no longer
    generates a key, displays a recovery phrase, or enables encryption —
    it only prints a notice. See `docs/adr/ADR-0024-drop-e2ee.md`.
    """
    console.print(
        "\n[yellow]End-to-end encryption has been discontinued (ADR-0024).[/yellow]"
    )
    console.print(
        "Your tasks now sync as plaintext; no encryption key is needed.\n"
    )
    console.print(
        "[dim]If you have existing content stored under an old encrypted "
        "setup, `todopro data export`/`import` can be used to re-save it as "
        "plaintext — this is a manual, out-of-scope follow-up.[/dim]\n"
    )


@app.command("status")
def status():
    """[Discontinued] Report encryption status (ADR-0024)."""
    console.print()
    console.print(
        "[bold yellow]End-to-end encryption has been discontinued (ADR-0024).[/bold yellow]"
    )
    console.print("Status: [yellow]discontinued[/yellow] — tasks sync as plaintext.")

    # Informational only: a legacy key file may still exist on disk from
    # before the feature was dropped, but it is no longer used for writes.
    service = get_encryption_service()
    enc_status = service.get_status()
    if enc_status.key_file_exists:
        console.print(
            f"   [dim]Legacy key file still present at: {enc_status.key_file_path} "
            "(unused, dormant)[/dim]"
        )

    console.print()


@app.command("show-recovery")
def show_recovery(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Display your recovery phrase.

    ⚠️  WARNING: Anyone with your recovery phrase can access your encrypted data!
    Only use this command in a secure, private environment.
    """
    service = get_encryption_service()

    if not service.storage.has_key():
        console.print("\n[red]❌ No encryption key found[/red]")
        console.print("   Run: [cyan]todopro encryption setup[/cyan]\n")
        raise typer.Exit(code=1)

    # Security warning
    if not confirm:
        console.print(
            "\n[bold yellow]⚠️  WARNING: This will display your recovery phrase in plain text![/bold yellow]\n"
        )
        if not typer.confirm("Are you in a secure, private location?"):
            console.print("[dim]Cancelled.[/dim]\n")
            raise typer.Exit()

    # Load key and get recovery phrase
    try:
        recovery_phrase = service.get_recovery_phrase()

        console.print()
        console.print(
            Panel.fit(
                Text(recovery_phrase, style="bold yellow", justify="center"),
                title="[bold]Your Recovery Phrase[/bold]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()
        console.print("[dim]Keep this phrase secret and safe![/dim]\n")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(code=1) from e


@app.command("recover")
def recover():
    """
    Recover your encryption key from recovery phrase.

    Use this if you lost your encryption key but have your 24-word recovery phrase.
    """
    console.print("\n[bold cyan]🔑 Recover Encryption Key[/bold cyan]\n")

    service = get_encryption_service()

    # Warn if key already exists
    if service.storage.has_key():
        console.print("[yellow]⚠️  An encryption key already exists![/yellow]")
        console.print(f"   Location: {service.storage.get_key_path()}\n")

        if not typer.confirm("Do you want to replace it with a recovered key?"):
            console.print("[dim]Recovery cancelled.[/dim]\n")
            raise typer.Exit()

    # Prompt for recovery phrase
    console.print("[dim]Enter your 24-word recovery phrase:[/dim]")
    phrase = typer.prompt("Recovery phrase", hide_input=True)

    # Attempt recovery
    try:
        console.print("\n[dim]Recovering encryption key...[/dim]")
        manager = service.recover(phrase)

        # Save recovered key
        service.save_manager(manager)

        console.print()
        console.print(
            "[bold green]✅ Encryption key recovered successfully![/bold green]"
        )
        console.print(
            f"   Key stored at: [cyan]{service.storage.get_key_path()}[/cyan]"
        )
        console.print()

    except TodoProCryptoError as e:
        console.print(f"\n[bold red]❌ Recovery failed: {e}[/bold red]")
        console.print("   Make sure you entered the correct 12-word phrase.\n")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"\n[bold red]❌ Unexpected error: {e}[/bold red]\n")
        raise typer.Exit(code=1) from e


@app.command("rotate-key")
def rotate_key():
    """
    Rotate encryption key (advanced feature).

    This will:
    1. Generate a new master key
    2. Download all encrypted data
    3. Re-encrypt with new key
    4. Upload re-encrypted data
    5. Display new recovery phrase
    """
    console.print("\n[bold yellow]⚠️  Key rotation not yet implemented[/bold yellow]")
    console.print("   This is an advanced feature planned for future release.\n")
    raise typer.Exit()


if __name__ == "__main__":
    app()
