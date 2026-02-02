"""Encryption management commands for TodoPro CLI."""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional

from todopro_cli.crypto.manager import EncryptionManager
from todopro_cli.crypto.storage import KeyStorage
from todopro_cli.crypto.exceptions import TodoProCryptoError

app = typer.Typer(help="Manage end-to-end encryption")
console = Console()


def get_config_dir() -> Path:
    """Get the CLI config directory."""
    from platformdirs import user_config_dir
    return Path(user_config_dir("todopro-cli"))


def get_key_storage() -> KeyStorage:
    """Get key storage instance."""
    config_dir = get_config_dir()
    return KeyStorage(config_dir)


@app.command("setup")
def setup():
    """
    Set up end-to-end encryption for the first time.
    
    This will:
    1. Generate a new master encryption key
    2. Display your 12-word recovery phrase (SAVE THIS!)
    3. Verify you saved the recovery phrase
    4. Store the key locally and backup to server
    """
    console.print("\n[bold cyan]🔐 TodoPro Encryption Setup[/bold cyan]\n")
    
    storage = get_key_storage()
    
    # Check if already set up
    if storage.has_key():
        console.print("[yellow]⚠️  Encryption is already set up![/yellow]")
        console.print(f"   Key file: {storage.get_key_path()}\n")
        
        if not typer.confirm("Do you want to set up a new key? (This will replace your current key)"):
            console.print("[dim]Setup cancelled.[/dim]")
            raise typer.Exit()
    
    # Generate master key and recovery phrase
    console.print("[dim]Generating master encryption key...[/dim]")
    manager = EncryptionManager.generate()
    recovery_phrase = manager.get_recovery_phrase()
    
    # Display recovery phrase
    console.print()
    console.print(Panel.fit(
        Text(recovery_phrase, style="bold yellow", justify="center"),
        title="[bold red]⚠️  YOUR 12-WORD RECOVERY PHRASE[/bold red]",
        border_style="red",
        padding=(1, 2)
    ))
    console.print()
    console.print("[bold red]IMPORTANT:[/bold red]")
    console.print("  • Write down these 12 words on paper")
    console.print("  • Store them in a safe place")
    console.print("  • This is the [bold]ONLY[/bold] way to recover your data if you lose your device")
    console.print("  • Never share your recovery phrase with anyone")
    console.print()
    
    # Confirm user saved it
    if not typer.confirm("Have you written down your recovery phrase?"):
        console.print("\n[yellow]Setup cancelled. Run 'todopro encryption setup' again when ready.[/yellow]")
        raise typer.Exit()
    
    # Verify phrase
    console.print()
    verify_phrase = typer.prompt("Type your recovery phrase to verify", hide_input=False)
    
    if not manager.verify_recovery_phrase(verify_phrase):
        console.print("\n[bold red]❌ Recovery phrase doesn't match![/bold red]")
        console.print("   Setup failed. Please try again.\n")
        raise typer.Exit(code=1)
    
    # Save key locally
    console.print("\n[dim]Saving encryption key...[/dim]")
    storage.save_key(manager.export_key())
    
    # TODO: Send encrypted backup to server via API
    # This would call POST /api/auth/setup-encryption with the encrypted backup
    console.print("[dim]Uploading encrypted backup to server...[/dim]")
    console.print("[yellow]Note: Server backup not yet implemented (API integration needed)[/yellow]")
    
    console.print()
    console.print("[bold green]✅ Encryption setup complete![/bold green]")
    console.print(f"   Key stored at: [cyan]{storage.get_key_path()}[/cyan]")
    console.print()


@app.command("status")
def status():
    """Check encryption status."""
    console.print()
    storage = get_key_storage()
    
    if storage.has_key():
        console.print("[bold green]✅ Encryption is enabled[/bold green]")
        console.print(f"   Key file: [cyan]{storage.get_key_path()}[/cyan]")
        
        # Try to load and verify key
        try:
            key_b64 = storage.load_key()
            manager = EncryptionManager.from_base64_key(key_b64)
            console.print("   Status: [green]Valid key loaded[/green]")
        except Exception as e:
            console.print(f"   Status: [red]Error loading key: {e}[/red]")
    else:
        console.print("[bold red]❌ Encryption is not set up[/bold red]")
        console.print("   Run: [cyan]todopro encryption setup[/cyan]")
    
    console.print()


@app.command("show-recovery")
def show_recovery(
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt"
    )
):
    """
    Display your recovery phrase.
    
    ⚠️  WARNING: Anyone with your recovery phrase can access your encrypted data!
    Only use this command in a secure, private environment.
    """
    storage = get_key_storage()
    
    if not storage.has_key():
        console.print("\n[red]❌ No encryption key found[/red]")
        console.print("   Run: [cyan]todopro encryption setup[/cyan]\n")
        raise typer.Exit(code=1)
    
    # Security warning
    if not confirm:
        console.print("\n[bold yellow]⚠️  WARNING: This will display your recovery phrase in plain text![/bold yellow]\n")
        if not typer.confirm("Are you in a secure, private location?"):
            console.print("[dim]Cancelled.[/dim]\n")
            raise typer.Exit()
    
    # Load key and get recovery phrase
    try:
        key_b64 = storage.load_key()
        manager = EncryptionManager.from_base64_key(key_b64)
        recovery_phrase = manager.get_recovery_phrase()
        
        console.print()
        console.print(Panel.fit(
            Text(recovery_phrase, style="bold yellow", justify="center"),
            title="[bold]Your Recovery Phrase[/bold]",
            border_style="yellow",
            padding=(1, 2)
        ))
        console.print()
        console.print("[dim]Keep this phrase secret and safe![/dim]\n")
        
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(code=1)


@app.command("recover")
def recover():
    """
    Recover your encryption key from recovery phrase.
    
    Use this if you lost your encryption key but have your 12-word recovery phrase.
    """
    console.print("\n[bold cyan]🔑 Recover Encryption Key[/bold cyan]\n")
    
    storage = get_key_storage()
    
    # Warn if key already exists
    if storage.has_key():
        console.print("[yellow]⚠️  An encryption key already exists![/yellow]")
        console.print(f"   Location: {storage.get_key_path()}\n")
        
        if not typer.confirm("Do you want to replace it with a recovered key?"):
            console.print("[dim]Recovery cancelled.[/dim]\n")
            raise typer.Exit()
    
    # Prompt for recovery phrase
    console.print("[dim]Enter your 12-word recovery phrase:[/dim]")
    phrase = typer.prompt("Recovery phrase", hide_input=True)
    
    # Attempt recovery
    try:
        console.print("\n[dim]Recovering encryption key...[/dim]")
        manager = EncryptionManager.from_recovery_phrase(phrase)
        
        # Save recovered key
        storage.save_key(manager.export_key())
        
        console.print()
        console.print("[bold green]✅ Encryption key recovered successfully![/bold green]")
        console.print(f"   Key stored at: [cyan]{storage.get_key_path()}[/cyan]")
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
