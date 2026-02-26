"""Auth commands — login, logout, signup."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

from .auth import login, logout

app = typer.Typer(cls=SuggestingGroup, help="Authentication — login, logout, signup")
console = get_console()


@app.command("login")
def auth_login(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    save_profile: bool = typer.Option(
        False, "--save-profile", help="Save as default profile"
    ),
) -> None:
    """Login to TodoPro."""
    login(
        email=email,
        password=password,
        endpoint=endpoint,
        save_profile=save_profile,
    )


@app.command("logout")
def auth_logout(
    all_profiles: bool = typer.Option(False, "--all", help="Logout from all contexts"),
) -> None:
    """Logout from TodoPro."""
    logout(all_profiles=all_profiles)


@app.command("signup")
def auth_signup(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
) -> None:
    """Register a new user account."""
    import asyncio

    from todopro_cli.services.auth_service import AuthService
    from todopro_cli.utils.ui.formatters import format_success

    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    auth_service = AuthService()
    asyncio.run(auth_service.signup(email=email, password=password))
    format_success(f"Account created: {email}")
