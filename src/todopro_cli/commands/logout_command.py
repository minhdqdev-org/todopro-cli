"""Command 'logout' of todopro-cli"""

import typer

from todopro_cli.utils.ui.console import get_console

from .auth import logout

app = typer.Typer()
console = get_console()


@app.command("logout")
def logout_command(
    all_profiles: bool = typer.Option(False, "--all", help="Logout from all contexts"),
) -> None:
    """Logout from TodoPro."""
    # Delegate to auth command
    logout(all_profiles=all_profiles)
