"""Authentication commands."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from todopro_cli.api.auth import AuthAPI
from todopro_cli.api.client import get_client
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success

app = typer.Typer(help="Authentication commands")
console = Console()


@app.command()
def login(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email address"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", help="API endpoint URL"),
    save_profile: bool = typer.Option(
        False, "--save-profile", help="Save as default profile"
    ),
) -> None:
    """Login to TodoPro."""
    try:
        # Get config manager
        config_manager = get_config_manager(profile)

        # Update endpoint if provided
        if endpoint:
            config_manager.set("api.endpoint", endpoint)

        # Prompt for credentials if not provided
        if not email:
            email = Prompt.ask("Email")
        if not password:
            password = Prompt.ask("Password", password=True)

        if not email or not password:
            format_error("Email and password are required")
            raise typer.Exit(1)

        # Perform login
        async def do_login() -> None:
            client = get_client(profile)
            auth_api = AuthAPI(client)

            try:
                result = await auth_api.login(email, password)  # type: ignore

                # Save credentials
                token = result.get("access_token") or result.get("token")
                refresh_token = result.get("refresh_token")

                if not token:
                    format_error("Invalid response from server: no token received")
                    raise typer.Exit(1)

                config_manager.save_credentials(token, refresh_token)

                # Get user profile
                user = await auth_api.get_profile()

                format_success(f"Logged in as {user.get('email', 'unknown')}")

                if save_profile:
                    format_success(f"Profile '{profile}' saved as default")

            finally:
                await client.close()

        asyncio.run(do_login())

    except Exception as e:
        format_error(f"Login failed: {str(e)}")
        raise typer.Exit(1)


@app.command()
def logout(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    all_profiles: bool = typer.Option(False, "--all", help="Logout from all profiles"),
) -> None:
    """Logout from TodoPro."""
    try:
        if all_profiles:
            config_manager = get_config_manager(profile)
            profiles = config_manager.list_profiles()
            for prof in profiles:
                prof_manager = get_config_manager(prof)
                prof_manager.clear_credentials()
            format_success("Logged out from all profiles")
        else:
            config_manager = get_config_manager(profile)

            # Try to logout from server
            async def do_logout() -> None:
                client = get_client(profile)
                auth_api = AuthAPI(client)
                try:
                    await auth_api.logout()
                except Exception:
                    # Ignore errors during logout
                    pass
                finally:
                    await client.close()

            asyncio.run(do_logout())

            # Clear local credentials
            config_manager.clear_credentials()
            format_success(f"Logged out from profile '{profile}'")

    except Exception as e:
        format_error(f"Logout failed: {str(e)}")
        raise typer.Exit(1)


@app.command()
def whoami(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show current user information."""
    try:
        config_manager = get_config_manager(profile)

        # Check if logged in
        credentials = config_manager.load_credentials()
        if not credentials:
            format_error("Not logged in. Use 'todopro login' to authenticate.")
            raise typer.Exit(1)

        async def get_user() -> None:
            client = get_client(profile)
            auth_api = AuthAPI(client)

            try:
                user = await auth_api.get_profile()
                format_output(user, output)
            finally:
                await client.close()

        asyncio.run(get_user())

    except Exception as e:
        format_error(f"Failed to get user information: {str(e)}")
        raise typer.Exit(1)
