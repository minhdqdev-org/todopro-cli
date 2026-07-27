"""Auth commands — login, logout, signup."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

from .auth import login, logout, resend_verification, signup

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


@app.command("resend-verification")
def auth_resend_verification(
    email: str | None = typer.Option(
        None,
        "--email",
        help="Address to resend to (defaults to the signed-in account)",
    ),
) -> None:
    """Send yourself a fresh email-confirmation link."""
    resend_verification(email=email)


@app.command("signup")
def auth_signup(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    auto_login: bool = typer.Option(
        True, "--auto-login/--no-auto-login", help="Automatically login after signup"
    ),
) -> None:
    """Register a new user account."""
    signup(
        email=email,
        password=password,
        endpoint=endpoint,
        auto_login=auto_login,
    )
