"""Decorators for command functions."""

import asyncio
import functools
import time
import traceback
from collections.abc import Callable

import typer

from todopro_cli.services.auth_service import AuthService
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.logger import get_logger
from todopro_cli.utils.ui.formatters import format_error


def _require_auth() -> None:
    """Require user to be authenticated.

    Note: Local contexts don't require authentication.
    """

    # Check current context type
    config_svc = get_config_service()
    try:
        current_context = config_svc.config.get_current_context()
    except (ValueError, KeyError):
        # No context configured, assume local (doesn't need auth)
        return

    # Skip authentication check for local contexts
    if current_context and current_context.type == "local":
        return

    # Require authentication for remote contexts
    if not AuthService.is_authenticated():
        format_error("Not logged in. Use 'todopro login' to authenticate.")
        raise typer.Exit(1)


class AppError(Exception):
    """Custom application error with exit code."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def command_wrapper(_func: Callable | None = None, *, auth_required: bool = True):
    """Decorator to wrap command functions with common functionality."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            cmd = func.__name__
            start = time.monotonic()
            logger.info("command started: %s", cmd)
            try:
                # 1. Handle Auth
                if auth_required:
                    _require_auth()

                # 2. Run Sync or Async
                if asyncio.iscoroutinefunction(func):
                    result = asyncio.run(func(*args, **kwargs))
                else:
                    result = func(*args, **kwargs)

                elapsed = time.monotonic() - start
                logger.info("command completed: %s (%.3fs)", cmd, elapsed)
                return result

            except AppError as e:
                elapsed = time.monotonic() - start
                logger.error(
                    "command failed: %s (%.3fs) - %s",
                    cmd,
                    elapsed,
                    str(e),
                )
                format_error(str(e))
                raise typer.Exit(code=e.exit_code) from e

            except typer.Exit:
                # Re-raise Typer's own exits (like --help or explicit Exit(0))
                raise

            except Exception as e:
                elapsed = time.monotonic() - start
                logger.error(
                    "command failed: %s (%.3fs) - %s\n%s",
                    cmd,
                    elapsed,
                    str(e),
                    traceback.format_exc(),
                )
                # Generic fallback for unexpected crashes
                format_error(f"An unexpected error occurred: {str(e)}")
                raise typer.Exit(code=1) from e

        return wrapper

    if _func is None:
        return decorator
    return decorator(_func)
