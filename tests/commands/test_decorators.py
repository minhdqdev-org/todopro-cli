"""Unit tests for command decorators."""

from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from todopro_cli.commands.decorators import AppError, _require_auth, command_wrapper

runner = CliRunner()


class TestRequireAuth:
    """Tests for _require_auth() function."""

    def test_local_context_skips_auth(self):
        """Local context type → no auth check needed → returns silently."""
        config_svc = MagicMock()
        ctx = MagicMock()
        ctx.type = "local"
        config_svc.config.get_current_context.return_value = ctx

        with patch("todopro_cli.commands.decorators.get_config_service", return_value=config_svc):
            _require_auth()  # Should not raise

    def test_no_context_configured_skips_auth(self):
        """ValueError when getting context → assumes local → returns silently."""
        config_svc = MagicMock()
        config_svc.config.get_current_context.side_effect = ValueError("no context")

        with patch("todopro_cli.commands.decorators.get_config_service", return_value=config_svc):
            _require_auth()  # Should not raise

    def test_key_error_skips_auth(self):
        """KeyError when getting context → assumes local → returns silently."""
        config_svc = MagicMock()
        config_svc.config.get_current_context.side_effect = KeyError("ctx")

        with patch("todopro_cli.commands.decorators.get_config_service", return_value=config_svc):
            _require_auth()  # Should not raise

    def test_remote_context_authenticated_passes(self):
        """Remote context with valid auth → no exception raised."""
        config_svc = MagicMock()
        ctx = MagicMock()
        ctx.type = "remote"
        config_svc.config.get_current_context.return_value = ctx

        with patch("todopro_cli.commands.decorators.get_config_service", return_value=config_svc):
            with patch("todopro_cli.commands.decorators.AuthService.is_authenticated", return_value=True):
                _require_auth()  # Should not raise

    def test_remote_context_not_authenticated_raises_exit(self):
        """Remote context with no auth → format_error + Exit(1)."""
        config_svc = MagicMock()
        ctx = MagicMock()
        ctx.type = "remote"
        config_svc.config.get_current_context.return_value = ctx

        with patch("todopro_cli.commands.decorators.get_config_service", return_value=config_svc):
            with patch("todopro_cli.commands.decorators.AuthService.is_authenticated", return_value=False):
                with patch("todopro_cli.commands.decorators.format_error"):
                    with pytest.raises(typer.Exit):
                        _require_auth()

    def test_none_current_context_falls_through_to_auth_check(self):
        """None current_context → condition is falsy → falls to auth check."""
        config_svc = MagicMock()
        config_svc.config.get_current_context.return_value = None

        with patch("todopro_cli.commands.decorators.get_config_service", return_value=config_svc):
            with patch("todopro_cli.commands.decorators.AuthService.is_authenticated", return_value=False):
                with patch("todopro_cli.commands.decorators.format_error"):
                    with pytest.raises(typer.Exit):
                        _require_auth()


class TestAppError:
    """Lines 42-43: AppError class."""

    def test_app_error_default_exit_code(self):
        """AppError defaults to exit_code=1."""
        err = AppError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.exit_code == 1

    def test_app_error_custom_exit_code(self):
        """AppError can have custom exit_code."""
        err = AppError("fatal error", exit_code=2)
        assert err.exit_code == 2
        assert str(err) == "fatal error"

    def test_app_error_is_exception(self):
        """AppError is an Exception subclass."""
        assert issubclass(AppError, Exception)

    def test_app_error_can_be_raised_and_caught(self):
        """AppError can be raised and caught as Exception."""
        with pytest.raises(AppError) as exc_info:
            raise AppError("test", exit_code=3)
        assert exc_info.value.exit_code == 3


class TestCommandWrapper:
    """Tests for command_wrapper decorator."""

    def test_wraps_sync_function(self):
        """Sync function is called directly."""
        called = []

        @command_wrapper(auth_required=False)
        def my_cmd():
            called.append(True)

        my_cmd()
        assert called == [True]

    def test_wraps_async_function(self):
        """Async function is run via asyncio.run."""
        called = []

        @command_wrapper(auth_required=False)
        async def my_async_cmd():
            called.append(True)

        my_async_cmd()
        assert called == [True]

    def test_app_error_caught_and_reraises_exit(self):
        """Lines 63-64: AppError is caught, format_error called, Exit raised."""
        @command_wrapper(auth_required=False)
        def failing_cmd():
            raise AppError("test error", exit_code=2)

        app_test = typer.Typer()
        app_test.command()(failing_cmd)

        with patch("todopro_cli.commands.decorators.format_error") as mock_fmt:
            result = runner.invoke(app_test, [])

        assert result.exit_code == 2
        mock_fmt.assert_called_once_with("test error")

    def test_typer_exit_reraises(self):
        """typer.Exit is re-raised without modification."""
        @command_wrapper(auth_required=False)
        def exit_cmd():
            raise typer.Exit(code=0)

        app_test = typer.Typer()
        app_test.command()(exit_cmd)

        result = runner.invoke(app_test, [])
        assert result.exit_code == 0

    def test_unexpected_exception_caught(self):
        """Unexpected exception → format_error + Exit(1)."""
        @command_wrapper(auth_required=False)
        def crashing_cmd():
            raise RuntimeError("unexpected crash")

        app_test = typer.Typer()
        app_test.command()(crashing_cmd)

        with patch("todopro_cli.commands.decorators.format_error") as mock_fmt:
            result = runner.invoke(app_test, [])

        assert result.exit_code == 1
        mock_fmt.assert_called_once()

    def test_auth_required_true_calls_require_auth(self):
        """auth_required=True calls _require_auth."""
        @command_wrapper  # default auth_required=True
        def auth_cmd():
            pass

        app_test = typer.Typer()
        app_test.command()(auth_cmd)

        with patch("todopro_cli.commands.decorators._require_auth") as mock_auth:
            result = runner.invoke(app_test, [])

        mock_auth.assert_called_once()
        assert result.exit_code == 0

    def test_auth_required_false_skips_require_auth(self):
        """auth_required=False does NOT call _require_auth."""
        @command_wrapper(auth_required=False)
        def no_auth_cmd():
            pass

        app_test = typer.Typer()
        app_test.command()(no_auth_cmd)

        with patch("todopro_cli.commands.decorators._require_auth") as mock_auth:
            result = runner.invoke(app_test, [])

        mock_auth.assert_not_called()
        assert result.exit_code == 0

    def test_wrapper_preserves_function_name(self):
        """command_wrapper preserves the original function name via functools.wraps."""
        @command_wrapper(auth_required=False)
        def my_named_function():
            pass

        assert my_named_function.__name__ == "my_named_function"
