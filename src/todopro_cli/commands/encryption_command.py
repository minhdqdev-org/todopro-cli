"""Encryption management commands for TodoPro CLI.

Deprecated: end-to-end encryption was dropped per ADR-0024
(`docs/adr/ADR-0024-drop-e2ee.md`). No command in this group can enable,
recover or rotate an encryption key any more — every one of them only prints
a discontinuation notice.

The group stays registered (so scripts and `--help` get a clear
"discontinued" message instead of a confusing command-not-found), and stays
*visible* in `--help` for the same reason: a user following an old runbook
needs to be able to discover why the feature stopped working.
"""

import typer

from todopro_cli.services.encryption_service import EncryptionService
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(help="[Discontinued] End-to-end encryption (ADR-0024)")
console = get_console()


def _print_discontinued() -> None:
    """Print the shared ADR-0024 discontinuation notice."""
    console.print(
        "\n[yellow]End-to-end encryption has been discontinued (ADR-0024).[/yellow]"
    )
    console.print("Your tasks now sync as plaintext; no encryption key is needed.\n")


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
    confirm: bool = typer.Option(  # noqa: ARG001 — kept so existing scripts passing --yes don't break
        False, "--yes", "-y", help="Ignored (kept for backwards compatibility)"
    ),
):
    """
    [Discontinued] Display an E2EE recovery phrase (ADR-0024).

    E2EE has been dropped as a shipped feature. There is no recovery phrase to
    display — nothing can enable encryption any more, so no key is in use.
    See `docs/adr/ADR-0024-drop-e2ee.md`.
    """
    _print_discontinued()
    console.print(
        "[dim]There is no recovery phrase to display: recovery phrases only "
        "protected E2EE keys, and no key is used for your data any more.[/dim]\n"
    )


@app.command("recover")
def recover():
    """
    [Discontinued] Recover an E2EE key from a recovery phrase (ADR-0024).

    E2EE has been dropped as a shipped feature. There is nothing to recover —
    your data is not encrypted with a client-side key.
    See `docs/adr/ADR-0024-drop-e2ee.md`.
    """
    _print_discontinued()
    console.print(
        "[dim]Nothing to recover: your data is not protected by a client-side "
        "encryption key, so a recovery phrase would not unlock anything.[/dim]\n"
    )


@app.command("rotate-key")
def rotate_key():
    """
    [Discontinued] Rotate an E2EE key (ADR-0024).

    E2EE has been dropped as a shipped feature. Key rotation was never
    implemented and will not be — there is no key to rotate.
    See `docs/adr/ADR-0024-drop-e2ee.md`.
    """
    _print_discontinued()
    console.print(
        "[dim]Nothing to rotate: no client-side encryption key is in use.[/dim]\n"
    )


if __name__ == "__main__":
    app()
