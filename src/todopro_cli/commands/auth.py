"""Authentication commands."""

import asyncio
import json

import typer
from rich.prompt import Prompt

from todopro_cli.services.api.auth import AuthAPI
from todopro_cli.services.api.client import get_client
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_success

app = typer.Typer(cls=SuggestingGroup, help="Authentication commands")
console = get_console()


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
        # Get config service
        config_service = get_config_service()

        # Require remote context
        current_context = config_service.get_current_context()
        if current_context and current_context.type != "remote":
            format_error(
                f"Login is only available for remote contexts. "
                f"Current context '{current_context.name}' is '{current_context.type}'. "
                f"Use 'tp context use cloud' to switch to a remote context."
            )
            raise typer.Exit(1)

        context_name = current_context.name if current_context else "unknown"

        # Update endpoint if provided
        if endpoint:
            config_service.set_endpoint(endpoint)

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

                # Save credentials. Knox returns a single opaque token (no
                # refresh token); it auto-refreshes server-side on use.
                token = result.get("token") or result.get("access_token")

                if not token:
                    format_error("Invalid response from server: no token received")
                    raise typer.Exit(1)

                # Save credentials for current context
                config_service.save_credentials(token, context_name=context_name)

                # Get user profile
                user = await auth_api.get_profile()

                msg = (
                    f"Logged in as {user.get('email', 'unknown')} "
                    f"(context: {context_name})"
                )
                if save_profile:
                    msg += " — saved as default"
                format_success(msg)

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
        # Get config service
        config_service = get_config_service()

        # Require remote context
        current_context = config_service.get_current_context()
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
            config_service.set_endpoint(endpoint)

        # Prompt for credentials if not provided
        if not email:
            email = Prompt.ask("Email")

        # Client-side password policy — kept in lockstep with the backend and
        # the other TodoPro clients: at least 8 characters, and at least one
        # uppercase letter, one lowercase letter, and one special
        # (non-alphanumeric) character.
        def password_problems(pw: str) -> list[str]:
            problems: list[str] = []
            if len(pw) < 8:
                problems.append("be at least 8 characters long")
            if not any(c.isupper() for c in pw):
                problems.append("contain an uppercase letter")
            if not any(c.islower() for c in pw):
                problems.append("contain a lowercase letter")
            if not any(not c.isalnum() for c in pw):
                problems.append("contain a special character")
            return problems

        if password:
            # Supplied non-interactively (--password): validate, but there is
            # no way to re-prompt, so a weak password is a hard error.
            problems = password_problems(password)
            if problems:
                format_error("Password must " + "; ".join(problems) + ".")
                raise typer.Exit(1)
        else:
            # Interactive: keep asking until the policy is satisfied, showing a
            # 4-segment strength meter (one filled block per satisfied rule).
            while True:
                password = Prompt.ask("Password", password=True)
                problems = password_problems(password)
                met = 4 - len(problems)

                bar_color = "red" if met <= 1 else "yellow" if met <= 3 else "green"
                bar = "".join(
                    f"[{bar_color}]█[/{bar_color}]" if i < met else "[dim]█[/dim]"
                    for i in range(4)
                )
                label = ("very weak", "weak", "fair", "good", "strong")[met]
                console.print(f"[dim]Strength:[/dim] {bar} [dim]({label})[/dim]")

                if problems:
                    format_error("Password must " + "; ".join(problems) + ".")
                    continue

                confirm_password = Prompt.ask("Confirm password", password=True)
                if password != confirm_password:
                    format_error("Passwords do not match")
                    raise typer.Exit(1)
                break

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
                        except Exception:
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

                    # Save credentials (Knox: single opaque token, no refresh)
                    token = login_result.get("token") or login_result.get(
                        "access_token"
                    )

                    if token:
                        config_service.save_credentials(
                            token, context_name=context_name
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
        config_service = get_config_service()

        # Require remote context
        current_context = config_service.get_current_context()
        if current_context and current_context.type != "remote":
            format_error(
                f"Logout is only available for remote contexts. "
                f"Current context '{current_context.name}' is '{current_context.type}'. "
                f"Use 'tp use cloud' to switch to a remote context."
            )
            raise typer.Exit(1)

        if all_profiles:
            contexts = config_service.list_contexts()
            for ctx in contexts:
                config_service.clear_credentials(ctx.name)
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
            config_service.clear_credentials()
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
        config_service = get_config_service()

        # Check if logged in
        credentials = config_service.load_credentials()
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


@app.command("resend-verification")
def resend_verification(
    email: str | None = typer.Option(
        None,
        "--email",
        help="Address to resend to (defaults to the signed-in account)",
    ),
) -> None:
    """S-80: send yourself a fresh email-confirmation link.

    The wall the API puts in front of an unconfirmed account points here, so
    this has to work while that wall is up — which it does: the endpoint is
    exempt from the gate, and `--email` skips auth entirely for a machine that
    was never signed in.
    """
    try:
        config_service = get_config_service()

        current_context = config_service.get_current_context()
        if current_context and current_context.type != "remote":
            format_error(
                f"Email verification only applies to remote contexts. "
                f"Current context '{current_context.name}' is "
                f"'{current_context.type}'."
            )
            raise typer.Exit(1)

        async def do_resend() -> None:
            client = get_client()
            auth_api = AuthAPI(client)
            try:
                result = await auth_api.resend_verification(email)
                # The backend answers the same way whether the address is
                # unknown, already confirmed, or genuinely pending — echo its
                # wording rather than inventing a more specific claim.
                format_success(
                    result.get("message")
                    or "If that address needs confirming, a new link is on its way."
                )
            finally:
                await client.close()

        asyncio.run(do_resend())

    except typer.Exit:
        raise
    except Exception as e:
        format_error(f"Could not request a new link: {str(e)}")
        raise typer.Exit(1) from e
