"""Authentication commands."""

import asyncio

import typer
from rich.console import Console
from rich.prompt import Prompt

from todopro_cli.api.auth import AuthAPI
from todopro_cli.api.client import get_client
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Authentication commands")
console = Console()


@app.command()
def login(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    save_profile: bool = typer.Option(
        False, "--save-profile", help="Save as default profile"
    ),
) -> None:
    """Login to TodoPro."""
    try:
        # Get config manager
        config_manager = get_config_manager(profile)

        # Initialize contexts if they don't exist
        if not config_manager.config.contexts:
            config_manager.init_default_contexts()

        # Update endpoint if provided
        if endpoint:
            config_manager.set("api.endpoint", endpoint)

        # Get current context
        current_context = config_manager.get_current_context()
        context_name = current_context.name if current_context else "unknown"

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

                # Save credentials for current context
                config_manager.save_context_credentials(
                    context_name, token, refresh_token
                )
                # Also save to default location for backward compatibility
                config_manager.save_credentials(token, refresh_token)

                # Get user profile
                user = await auth_api.get_profile()

                format_success(
                    f"Logged in as {user.get('email', 'unknown')} "
                    f"(context: {context_name})"
                )

                if save_profile:
                    format_success(f"Profile '{profile}' saved as default")

            finally:
                await client.close()

        asyncio.run(do_login())

    except Exception as e:
        format_error(f"Login failed: {str(e)}")
        raise typer.Exit(1) from e


@app.command()
def signup(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    auto_login: bool = typer.Option(
        True, "--auto-login/--no-auto-login", help="Automatically login after signup"
    ),
) -> None:
    """Create a new TodoPro account."""
    try:
        # Get config manager
        config_manager = get_config_manager(profile)

        # Initialize contexts if they don't exist
        if not config_manager.config.contexts:
            config_manager.init_default_contexts()

        # Update endpoint if provided
        if endpoint:
            config_manager.set("api.endpoint", endpoint)

        # Get current context
        current_context = config_manager.get_current_context()
        context_name = current_context.name if current_context else "unknown"

        # Prompt for credentials if not provided
        if not email:
            email = Prompt.ask("Email")
        if not password:
            password = Prompt.ask("Password", password=True)
            confirm_password = Prompt.ask("Confirm password", password=True)

            if password != confirm_password:
                format_error("Passwords do not match")
                raise typer.Exit(1)

        if not email or not password:
            format_error("Email and password are required")
            raise typer.Exit(1)

        # Perform signup
        async def do_signup() -> None:
            client = get_client(profile)
            auth_api = AuthAPI(client)

            try:
                # Create account
                try:
                    result = await auth_api.signup(email, password)  # type: ignore
                except Exception as e:
                    # Try to extract error message from response
                    error_msg = str(e)
                    if hasattr(e, "response") and hasattr(e.response, "text"):
                        try:
                            import json

                            error_data = json.loads(e.response.text)
                            if isinstance(error_data, dict):
                                if "email" in error_data:
                                    error_msg = f"Email: {error_data['email'][0] if isinstance(error_data['email'], list) else error_data['email']}"
                                elif "password" in error_data:
                                    error_msg = f"Password: {error_data['password'][0] if isinstance(error_data['password'], list) else error_data['password']}"
                                elif "error" in error_data:
                                    error_msg = error_data["error"]
                        except:
                            pass
                    raise Exception(error_msg)

                user_id = result.get("user_id")
                user_email = result.get("email")

                format_success(f"Account created successfully for {user_email}")
                console.print(f"[dim]User ID: {user_id}[/dim]")

                # Auto-login if enabled
                if auto_login:
                    console.print("\n[dim]Logging in...[/dim]")
                    login_result = await auth_api.login(email, password)  # type: ignore

                    # Save credentials
                    token = login_result.get("access_token") or login_result.get(
                        "token"
                    )
                    refresh_token = login_result.get("refresh_token")

                    if token:
                        config_manager.save_context_credentials(
                            context_name, token, refresh_token
                        )
                        config_manager.save_credentials(token, refresh_token)
                        format_success(f"Logged in as {user_email}")
                    else:
                        console.print(
                            "[yellow]Auto-login failed. Please login manually with:[/yellow]"
                        )
                        console.print(
                            f"[yellow]  todopro login --email {user_email}[/yellow]"
                        )
                else:
                    console.print("\n[dim]You can now login with:[/dim]")
                    console.print(f"[dim]  todopro login --email {user_email}[/dim]")

            finally:
                await client.close()

        asyncio.run(do_signup())

    except Exception as e:
        format_error(f"Signup failed: {str(e)}")
        raise typer.Exit(1) from e


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
    output: str = typer.Option("table", "--output", help="Output format"),
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
                # Remove avatar and created_at fields
                user.pop("avatar", None)
                user.pop("created_at", None)
                format_output(user, output)
            finally:
                await client.close()

        asyncio.run(get_user())

    except Exception as e:
        format_error(f"Failed to get user information: {str(e)}")
        raise typer.Exit(1) from e


@app.command()
def timezone(
    new_timezone: str | None = typer.Argument(
        None, help="New timezone (IANA format, e.g., 'Asia/Ho_Chi_Minh')"
    ),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Get or set user timezone."""
    try:
        config_manager = get_config_manager(profile)

        # Check if logged in
        credentials = config_manager.load_credentials()
        if not credentials:
            format_error("Not logged in. Use 'todopro login' to authenticate.")
            raise typer.Exit(1)

        async def handle_timezone() -> None:
            client = get_client(profile)
            auth_api = AuthAPI(client)

            try:
                if new_timezone:
                    # Set new timezone
                    await auth_api.update_profile(timezone=new_timezone)
                    format_success(f"Timezone updated to: {new_timezone}")
                else:
                    # Get current timezone
                    user = await auth_api.get_profile()
                    current_tz = user.get("timezone", "UTC")
                    console.print(
                        f"[bold]Current timezone:[/bold] [cyan]{current_tz}[/cyan]"
                    )
                    console.print()
                    console.print("[dim]To set a new timezone, use:[/dim]")
                    console.print("[dim]  todopro auth timezone <IANA_TIMEZONE>[/dim]")
                    console.print(
                        "[dim]  Example: todopro auth timezone Asia/Ho_Chi_Minh[/dim]"
                    )
            finally:
                await client.close()

        asyncio.run(handle_timezone())

    except Exception as e:
        format_error(f"Failed to handle timezone: {str(e)}")
        raise typer.Exit(1) from e
