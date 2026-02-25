"""Encryption management commands for TodoPro CLI."""

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
    Set up end-to-end encryption for the first time.

    This will:
    1. Generate a new master encryption key
    2. Display your 24-word recovery phrase (SAVE THIS!)
    3. Verify you saved the recovery phrase
    4. Store the key locally and backup to server
    """
    console.print("\n[bold cyan]🔐 TodoPro Encryption Setup[/bold cyan]\n")

    service = get_encryption_service()
    status = service.get_status()

    # Check if already set up
    if status.key_file_exists:
        console.print("[yellow]⚠️  Encryption is already set up![/yellow]")
        console.print(f"   Key file: {status.key_file_path}\n")

        if not typer.confirm(
            "Do you want to set up a new key? (This will replace your current key)"
        ):
            console.print("[dim]Setup cancelled.[/dim]")
            raise typer.Exit()

    # Generate master key and recovery phrase
    console.print("[dim]Generating master encryption key...[/dim]")
    manager, recovery_phrase = service.setup()

    # Count words in recovery phrase
    word_count = len(recovery_phrase.split())

    # Display recovery phrase
    console.print()
    console.print(
        Panel.fit(
            Text(recovery_phrase, style="bold yellow", justify="center"),
            title=f"[bold red]⚠️  YOUR {word_count}-WORD RECOVERY PHRASE[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )
    console.print()
    console.print("[bold red]IMPORTANT:[/bold red]")
    console.print(f"  • Write down these {word_count} words on paper")
    console.print("  • Store them in a safe place")
    console.print(
        "  • This is the [bold]ONLY[/bold] way to recover your data if you lose your device"
    )
    console.print("  • Never share your recovery phrase with anyone")
    console.print()

    # Confirm user saved it
    if not typer.confirm("Have you written down your recovery phrase?"):
        console.print(
            "\n[yellow]Setup cancelled. Run 'todopro encryption setup' again when ready.[/yellow]"
        )
        raise typer.Exit()

    # Verify phrase
    console.print()
    verify_phrase = typer.prompt(
        "Type your recovery phrase to verify", hide_input=False
    )

    if verify_phrase.strip().lower() != recovery_phrase.lower():
        console.print("\n[bold red]❌ Recovery phrase doesn't match![/bold red]")
        console.print("   Setup failed. Please try again.\n")
        raise typer.Exit(code=1)

    # Save key locally
    console.print("\n[dim]Saving encryption key...[/dim]")
    service.save_manager(manager)

    # Enable E2EE in config
    from todopro_cli.services.config_service import get_config_service

    config_service = get_config_service()
    config_service.config.e2ee.enabled = True
    config_service.save_config()

    # TODO: Send encrypted backup to server via API
    # This would call POST /api/auth/setup-encryption with the encrypted backup
    console.print("[dim]Uploading encrypted backup to server...[/dim]")
    console.print(
        "[yellow]Note: Server backup not yet implemented (API integration needed)[/yellow]"
    )

    console.print()
    console.print("[bold green]✅ Encryption setup complete![/bold green]")
    console.print(
        f"   Key stored at: [cyan]{status.key_file_path or service.storage.key_file}[/cyan]"
    )
    console.print("   E2EE enabled in config")
    console.print()


@app.command("status")
def status():
    """Check encryption status."""
    console.print()
    service = get_encryption_service()
    enc_status = service.get_status()

    if enc_status.enabled:
        console.print("[bold green]✅ Encryption is enabled[/bold green]")
        console.print(f"   Key file: [cyan]{enc_status.key_file_path}[/cyan]")
        console.print("   Status: [green]Valid key loaded[/green]")
    elif enc_status.key_file_exists:
        console.print(
            "[bold yellow]⚠️  Encryption key exists but is invalid[/bold yellow]"
        )
        console.print(f"   Key file: [cyan]{enc_status.key_file_path}[/cyan]")
        console.print(f"   Error: [red]{enc_status.error}[/red]")
    else:
        console.print("[bold red]❌ Encryption is not set up[/bold red]")
        console.print("   Run: [cyan]todopro encryption setup[/cyan]")

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
        raise typer.Exit(code=1)


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
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[bold red]❌ Unexpected error: {e}[/bold red]\n")
        raise typer.Exit(code=1)


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
