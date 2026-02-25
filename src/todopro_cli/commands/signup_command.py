"""Signup command - Register new user."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_success

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Register new user")
console = get_console()


@app.command()
@command_wrapper
async def signup(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
) -> None:
    """Register a new user account."""
    from todopro_cli.services.auth_service import AuthService

    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    auth_service = AuthService()
    await auth_service.signup(email=email, password=password)
    format_success(f"Account created: {email}")
