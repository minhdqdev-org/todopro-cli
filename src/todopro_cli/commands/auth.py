"""Authentication commands."""

import asyncio
import json

import typer
from rich.console import Console
from rich.prompt import Prompt

from todopro_cli.services.api.auth import AuthAPI
from todopro_cli.services.api.client import get_client
from todopro_cli.services.context_manager import get_context_manager
from todopro_cli.utils.ui.formatters import format_error, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Authentication commands")
console = Console()


@app.command()
def login(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    save_profile: bool = typer.Option(
        False, "--save-profile", help="Save as default profile"
    ),
) -> None:
    """Login to TodoPro."""
    try:
        # Get config manager
        config_manager = get_context_manager()

        # Require remote context
        current_context = config_manager.get_current_context()
        if current_context and current_context.type != "remote":
            format_error(
                f"Login is only available for remote contexts. "
                f"Current context '{current_context.name}' is '{current_context.type}'. "
                f"Use 'tp use cloud' to switch to a remote context."
            )
            raise typer.Exit(1)

        context_name = current_context.name if current_context else "unknown"

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
            client = get_client()
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
                config_manager.save_credentials(
                    token, refresh_token, context_name
                )

                # Get user profile
                user = await auth_api.get_profile()

                format_success(
                    f"Logged in as {user.get('email', 'unknown')} "
                    f"(context: {context_name})"
                )

                if save_profile:
                    format_success("Profile 'default' saved as default")

            finally:
                await client.close()

        asyncio.run(do_login())

    except typer.Exit:
        raise
    except Exception as e:
        format_error(f"Login failed: {str(e)}")
        raise typer.Exit(1) from e


@app.command()
def signup(
    email: str | None = typer.Option(None, "--email", help="Email address"),
    password: str | None = typer.Option(None, "--password", help="Password"),
    endpoint: str | None = typer.Option(None, "--endpoint", help="API endpoint URL"),
    auto_login: bool = typer.Option(
        True, "--auto-login/--no-auto-login", help="Automatically login after signup"
    ),
) -> None:
    """Create a new TodoPro account."""
    try:
        # Get config manager
        config_manager = get_context_manager()

        # Require remote context
        current_context = config_manager.get_current_context()
        if current_context and current_context.type != "remote":
            format_error(
                f"Signup is only available for remote contexts. "
                f"Current context '{current_context.name}' is '{current_context.type}'. "
                f"Use 'tp use cloud' to switch to a remote context."
            )
            raise typer.Exit(1)

        context_name = current_context.name if current_context else "unknown"

        # Update endpoint if provided
        if endpoint:
            config_manager.set("api.endpoint", endpoint)

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
            client = get_client()
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
                    raise Exception(error_msg) from e

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
                        config_manager.save_credentials(
                            token, refresh_token, context_name
                        )
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

    except typer.Exit:
        raise
    except Exception as e:
        format_error(f"Signup failed: {str(e)}")
        raise typer.Exit(1) from e


@app.command()
def logout(
    all_profiles: bool = typer.Option(False, "--all", help="Logout from all contexts"),
) -> None:
    """Logout from TodoPro."""
    try:
        config_manager = get_context_manager()

        # Require remote context
        current_context = config_manager.get_current_context()
        if current_context and current_context.type != "remote":
            format_error(
                f"Logout is only available for remote contexts. "
                f"Current context '{current_context.name}' is '{current_context.type}'. "
                f"Use 'tp use cloud' to switch to a remote context."
            )
            raise typer.Exit(1)

        if all_profiles:
            contexts = config_manager.list_contexts()
            for ctx in contexts:
                config_manager.clear_credentials(ctx.name)
            format_success("Logged out from all contexts")
        else:
            # Try to logout from server
            async def do_logout() -> None:
                client = get_client()
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
            context_name = current_context.name if current_context else "default"
            config_manager.clear_credentials()
            format_success(f"Logged out from context '{context_name}'")

    except typer.Exit:
        raise
    except Exception as e:
        format_error(f"Logout failed: {str(e)}")
        raise typer.Exit(1) from e


@app.command()
def timezone(
    new_timezone: str | None = typer.Argument(
        None, help="New timezone (IANA format, e.g., 'Asia/Ho_Chi_Minh')"
    ),
) -> None:
    """Get or set user timezone."""
    try:
        config_manager = get_context_manager()

        # Check if logged in
        credentials = config_manager.load_credentials()
        if not credentials:
            format_error("Not logged in. Use 'todopro login' to authenticate.")
            raise typer.Exit(1)

        async def handle_timezone() -> None:
            client = get_client()
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
