"""Comprehensive unit tests for todopro_cli.commands.auth.

Covers: login, signup, logout, timezone commands.
Goal: maximise line/branch coverage across all paths.
"""

from __future__ import annotations

import asyncio
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.auth import app
from todopro_cli.models.config_models import AppConfig, Context

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_ansi(text: str) -> str:
    ansi = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi.sub("", text)


def _make_context(name="mycloud", ctx_type="remote", source="https://api.example.com"):
    return Context(name=name, type=ctx_type, source=source)


def _make_local_context(name="local", source="/tmp/test.db"):
    return Context(name=name, type="local", source=source)


def _mock_config_service(context=None, credentials=None):
    """Return a MagicMock config service."""
    mock = MagicMock()
    mock.get_current_context.return_value = context
    mock.load_credentials.return_value = credentials
    mock.save_credentials = MagicMock()
    mock.clear_credentials = MagicMock()
    mock.set = MagicMock()
    mock.list_contexts.return_value = []
    return mock


def _patch_config_service(mock_svc):
    return patch("todopro_cli.commands.auth.get_config_service", return_value=mock_svc)


def _make_auth_api_mock(
    login_result=None,
    signup_result=None,
    get_profile_result=None,
    logout_result=None,
    update_profile_result=None,
    login_side_effect=None,
    signup_side_effect=None,
):
    mock = MagicMock()
    mock.login = AsyncMock(
        return_value=login_result or {"access_token": "tok123", "refresh_token": "ref456"},
        side_effect=login_side_effect,
    )
    mock.signup = AsyncMock(
        return_value=signup_result or {"user_id": "uid-001", "email": "user@example.com"},
        side_effect=signup_side_effect,
    )
    mock.get_profile = AsyncMock(
        return_value=get_profile_result or {"email": "user@example.com", "timezone": "UTC"},
    )
    mock.logout = AsyncMock(return_value=None)
    mock.update_profile = AsyncMock(return_value=update_profile_result or {})
    return mock


def _patch_auth_api(mock_auth_api):
    """Patch AuthAPI constructor to return mock_auth_api."""
    return patch("todopro_cli.commands.auth.AuthAPI", return_value=mock_auth_api)


def _patch_get_client():
    """Patch get_client to return a mock that has .close()."""
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    return patch("todopro_cli.commands.auth.get_client", return_value=mock_client), mock_client


# ===========================================================================
# Tests: login
# ===========================================================================

class TestLogin:
    """Tests for the `auth login` command."""

    def test_help(self):
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "Login" in result.stdout

    def test_login_non_remote_context(self):
        """login on a local context should exit 1 with helpful message."""
        ctx = _make_local_context()
        svc = _mock_config_service(context=ctx)

        with _patch_config_service(svc):
            result = runner.invoke(app, ["login", "--email", "a@b.com", "--password", "pass"])

        assert result.exit_code == 1
        assert "remote" in strip_ansi(result.stdout).lower()

    def test_login_no_current_context(self):
        """No current context — login still proceeds (context_name becomes 'unknown')."""
        svc = _mock_config_service(context=None)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["login", "--email", "a@b.com", "--password", "pass"])

        # No context type check when context is None — goes to login
        assert result.exit_code == 0

    def test_login_success_with_flags(self):
        """Successful login with --email and --password flags."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["login", "--email", "a@b.com", "--password", "pass"])

        assert result.exit_code == 0
        assert "Logged in as" in strip_ansi(result.stdout)
        svc.save_credentials.assert_called_once()

    def test_login_with_save_profile(self):
        """--save-profile flag triggers profile saved message."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["login", "--email", "a@b.com", "--password", "pass", "--save-profile"],
            )

        assert result.exit_code == 0
        assert "saved as default" in strip_ansi(result.stdout)

    def test_login_with_endpoint_flag(self):
        """--endpoint flag calls config_service.set."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["login", "--email", "a@b.com", "--password", "pass",
                 "--endpoint", "https://new.api.com"],
            )

        assert result.exit_code == 0
        svc.set.assert_called_once_with("api.endpoint", "https://new.api.com")

    def test_login_prompts_for_credentials(self):
        """When email/password not given, prompts are triggered."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        prompt_answers = iter(["a@b.com", "password123"])
        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            with patch("todopro_cli.commands.auth.Prompt.ask", side_effect=prompt_answers):
                result = runner.invoke(app, ["login"])

        assert result.exit_code == 0

    def test_login_empty_credentials_after_prompt(self):
        """Empty email/password after prompt exits 1."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)

        with _patch_config_service(svc):
            with patch("todopro_cli.commands.auth.Prompt.ask", return_value=""):
                result = runner.invoke(app, ["login"])

        assert result.exit_code == 1
        assert "required" in strip_ansi(result.stdout).lower()

    def test_login_no_token_in_response(self):
        """Server returns no token — exits 1."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock(login_result={"data": "no token here"})
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["login", "--email", "a@b.com", "--password", "pass"])

        assert result.exit_code == 1
        assert "no token" in strip_ansi(result.stdout).lower()

    def test_login_token_via_token_key(self):
        """Server returns 'token' key instead of 'access_token'."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock(login_result={"token": "tok-alt", "refresh_token": None})
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["login", "--email", "a@b.com", "--password", "pass"])

        assert result.exit_code == 0
        svc.save_credentials.assert_called_once()

    def test_login_api_exception(self):
        """API raises unexpected exception — exits 1 with error message."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock(login_side_effect=Exception("network error"))
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["login", "--email", "a@b.com", "--password", "pass"])

        assert result.exit_code == 1
        assert "Login failed" in strip_ansi(result.stdout)


# ===========================================================================
# Tests: signup
# ===========================================================================

class TestSignup:
    """Tests for the `auth signup` command."""

    def test_help(self):
        result = runner.invoke(app, ["signup", "--help"])
        assert result.exit_code == 0

    def test_signup_non_remote_context(self):
        """signup on local context exits 1."""
        ctx = _make_local_context()
        svc = _mock_config_service(context=ctx)

        with _patch_config_service(svc):
            result = runner.invoke(app, ["signup", "--email", "a@b.com", "--password", "pass"])

        assert result.exit_code == 1
        assert "remote" in strip_ansi(result.stdout).lower()

    def test_signup_success_with_auto_login(self):
        """Successful signup with auto-login enabled."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 0
        assert "Account created" in strip_ansi(result.stdout)
        assert "Logged in as" in strip_ansi(result.stdout)
        svc.save_credentials.assert_called_once()

    def test_signup_success_no_auto_login(self):
        """Successful signup with --no-auto-login."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass", "--no-auto-login"],
            )

        assert result.exit_code == 0
        assert "Account created" in strip_ansi(result.stdout)
        assert "login with" in strip_ansi(result.stdout)
        svc.save_credentials.assert_not_called()

    def test_signup_with_endpoint(self):
        """--endpoint flag updates config."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass",
                 "--endpoint", "https://custom.api.com"],
            )

        assert result.exit_code == 0
        svc.set.assert_called_once_with("api.endpoint", "https://custom.api.com")

    def test_signup_prompts_for_credentials(self):
        """Without flags, prompts for email, password, and confirm password."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        prompt_answers = iter(["a@b.com", "pass123", "pass123"])
        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            with patch("todopro_cli.commands.auth.Prompt.ask", side_effect=prompt_answers):
                result = runner.invoke(app, ["signup"])

        assert result.exit_code == 0

    def test_signup_password_mismatch(self):
        """Password confirmation mismatch exits 1."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)

        prompt_answers = iter(["a@b.com", "pass1", "pass2"])
        with _patch_config_service(svc):
            with patch("todopro_cli.commands.auth.Prompt.ask", side_effect=prompt_answers):
                result = runner.invoke(app, ["signup"])

        assert result.exit_code == 1
        assert "do not match" in strip_ansi(result.stdout).lower()

    def test_signup_empty_credentials_after_prompt(self):
        """Empty email/password after prompt exits 1 (lines 144-145)."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)

        # Need 3 answers: email="", password="", confirm=""
        prompt_answers = iter(["", "", ""])
        with _patch_config_service(svc):
            with patch("todopro_cli.commands.auth.Prompt.ask", side_effect=prompt_answers):
                result = runner.invoke(app, ["signup"])

        assert result.exit_code == 1
        assert "required" in strip_ansi(result.stdout).lower()

    def test_signup_api_error_plain_exception(self):
        """signup raises a plain exception — exits 1."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock(signup_side_effect=Exception("duplicate email"))
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 1
        assert "Signup failed" in strip_ansi(result.stdout)

    def test_signup_api_error_with_response_email_field(self):
        """signup raises exception with .response.text containing email error."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)

        import json as _json

        exc = Exception("HTTP 400")
        exc.response = MagicMock()
        exc.response.text = _json.dumps({"email": ["This email is already taken."]})

        auth_api_mock = _make_auth_api_mock(signup_side_effect=exc)
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 1

    def test_signup_api_error_with_response_password_field(self):
        """signup raises exception with .response.text containing password error."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)

        import json as _json

        exc = Exception("HTTP 400")
        exc.response = MagicMock()
        exc.response.text = _json.dumps({"password": "Too short."})

        auth_api_mock = _make_auth_api_mock(signup_side_effect=exc)
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 1

    def test_signup_api_error_with_response_error_field(self):
        """signup raises with .response.text containing 'error' key."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)

        import json as _json

        exc = Exception("HTTP 400")
        exc.response = MagicMock()
        exc.response.text = _json.dumps({"error": "Something went wrong."})

        auth_api_mock = _make_auth_api_mock(signup_side_effect=exc)
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 1

    def test_signup_api_error_invalid_json_response(self):
        """signup raises with .response.text containing invalid JSON — falls back gracefully."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)

        exc = Exception("HTTP 500")
        exc.response = MagicMock()
        exc.response.text = "Not JSON at all"

        auth_api_mock = _make_auth_api_mock(signup_side_effect=exc)
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 1

    def test_signup_auto_login_no_token(self):
        """Auto-login returns no token — shows manual login prompt."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock(
            signup_result={"user_id": "uid-001", "email": "a@b.com"},
            login_result={"data": "no token"},  # login returns no token
        )
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 0
        assert "Auto-login failed" in strip_ansi(result.stdout)
        svc.save_credentials.assert_not_called()

    def test_signup_no_current_context(self):
        """No current context — context_name becomes 'unknown'."""
        svc = _mock_config_service(context=None)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(
                app,
                ["signup", "--email", "a@b.com", "--password", "pass"],
            )

        assert result.exit_code == 0


# ===========================================================================
# Tests: logout
# ===========================================================================

class TestLogout:
    """Tests for the `auth logout` command."""

    def test_help(self):
        result = runner.invoke(app, ["logout", "--help"])
        assert result.exit_code == 0

    def test_logout_non_remote_context(self):
        """logout on local context exits 1."""
        ctx = _make_local_context()
        svc = _mock_config_service(context=ctx)

        with _patch_config_service(svc):
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 1
        assert "remote" in strip_ansi(result.stdout).lower()

    def test_logout_success(self):
        """Standard logout from remote context."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0
        assert "Logged out" in strip_ansi(result.stdout)
        svc.clear_credentials.assert_called_once()

    def test_logout_server_error_ignored(self):
        """Server logout raises — error is silently swallowed, local creds cleared."""
        ctx = _make_context()
        svc = _mock_config_service(context=ctx)
        auth_api_mock = _make_auth_api_mock()
        auth_api_mock.logout = AsyncMock(side_effect=Exception("server gone"))
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0
        svc.clear_credentials.assert_called_once()

    def test_logout_all_profiles(self):
        """--all flag clears credentials for all contexts."""
        ctx = _make_context()
        ctx2 = _make_context(name="staging")
        svc = _mock_config_service(context=ctx)
        svc.list_contexts.return_value = [ctx, ctx2]

        with _patch_config_service(svc):
            result = runner.invoke(app, ["logout", "--all"])

        assert result.exit_code == 0
        assert "all contexts" in strip_ansi(result.stdout).lower()
        assert svc.clear_credentials.call_count == 2

    def test_logout_no_current_context(self):
        """No current context during logout — context_name defaults to 'default'."""
        svc = _mock_config_service(context=None)
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0

    def test_logout_outer_exception(self):
        """Unexpected top-level exception exits 1."""
        svc = _mock_config_service(context=_make_context())
        svc.clear_credentials.side_effect = Exception("unexpected")
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 1
        assert "Logout failed" in strip_ansi(result.stdout)


# ===========================================================================
# Tests: timezone
# ===========================================================================

class TestTimezone:
    """Tests for the `auth timezone` command."""

    def test_help(self):
        result = runner.invoke(app, ["timezone", "--help"])
        assert result.exit_code == 0

    def test_not_logged_in(self):
        """No credentials — exits 1."""
        svc = _mock_config_service(credentials=None)

        with _patch_config_service(svc):
            result = runner.invoke(app, ["timezone"])

        assert result.exit_code == 1
        assert "Not logged in" in strip_ansi(result.stdout)

    def test_get_timezone(self):
        """No argument — prints current timezone from profile."""
        svc = _mock_config_service(credentials={"token": "tok123"})
        auth_api_mock = _make_auth_api_mock(
            get_profile_result={"email": "a@b.com", "timezone": "Asia/Ho_Chi_Minh"}
        )
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["timezone"])

        assert result.exit_code == 0
        assert "Asia/Ho_Chi_Minh" in strip_ansi(result.stdout)

    def test_get_timezone_default_utc(self):
        """Profile has no timezone key — shows UTC."""
        svc = _mock_config_service(credentials={"token": "tok123"})
        auth_api_mock = _make_auth_api_mock(get_profile_result={"email": "a@b.com"})
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["timezone"])

        assert result.exit_code == 0
        assert "UTC" in strip_ansi(result.stdout)

    def test_set_timezone(self):
        """Argument provided — updates timezone on server."""
        svc = _mock_config_service(credentials={"token": "tok123"})
        auth_api_mock = _make_auth_api_mock()
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["timezone", "America/New_York"])

        assert result.exit_code == 0
        assert "America/New_York" in strip_ansi(result.stdout)
        auth_api_mock.update_profile.assert_awaited_once_with(timezone="America/New_York")

    def test_timezone_api_error(self):
        """API raises during timezone get — exits 1."""
        svc = _mock_config_service(credentials={"token": "tok123"})
        auth_api_mock = _make_auth_api_mock()
        auth_api_mock.get_profile = AsyncMock(side_effect=Exception("timeout"))
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["timezone"])

        assert result.exit_code == 1
        assert "Failed to handle timezone" in strip_ansi(result.stdout)

    def test_timezone_set_api_error(self):
        """API raises during timezone set — exits 1."""
        svc = _mock_config_service(credentials={"token": "tok123"})
        auth_api_mock = _make_auth_api_mock()
        auth_api_mock.update_profile = AsyncMock(side_effect=Exception("unauthorized"))
        p_client, _ = _patch_get_client()

        with _patch_config_service(svc), p_client, _patch_auth_api(auth_api_mock):
            result = runner.invoke(app, ["timezone", "Asia/Tokyo"])

        assert result.exit_code == 1
        assert "Failed to handle timezone" in strip_ansi(result.stdout)
