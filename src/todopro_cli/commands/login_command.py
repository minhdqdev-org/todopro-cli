"""Command 'login' of todopro-cli"""

import typer

from todopro_cli.utils.ui.console import get_console

from .auth import login

app = typer.Typer()
console = get_console()


@app.command("login")
def login_command(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    save_profile: bool = typer.Option(
        False, "--save-profile", help="Save as default profile"
    ),
) -> None:
    """Login to TodoPro."""
    # Delegate to auth command
    login(
        email=email,
        password=password,
        endpoint=endpoint,
        save_profile=save_profile,
    )
