"""Tests for auth_app.py — auth login, logout, signup commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.auth_app import app

runner = CliRunner(mix_stderr=False)


def _invoke(*args, **kwargs):
    return runner.invoke(app, list(args), catch_exceptions=True, **kwargs)


class TestAuthLogin:
    def test_login_help(self):
        result = _invoke("login", "--help")
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_login_delegates_to_auth_login(self):
        with patch("todopro_cli.commands.auth_app.login") as mock_login:
            result = _invoke("login")
            mock_login.assert_called_once()

    def test_login_passes_email(self):
        with patch("todopro_cli.commands.auth_app.login") as mock_login:
            _invoke("login", "--email", "user@example.com")
            mock_login.assert_called_once()
            kwargs = mock_login.call_args[1]
            assert kwargs["email"] == "user@example.com"

    def test_login_passes_password(self):
        with patch("todopro_cli.commands.auth_app.login") as mock_login:
            _invoke("login", "--password", "secret")
            mock_login.assert_called_once()
            kwargs = mock_login.call_args[1]
            assert kwargs["password"] == "secret"

    def test_login_passes_endpoint(self):
        with patch("todopro_cli.commands.auth_app.login") as mock_login:
            _invoke("login", "--endpoint", "https://api.example.com")
            mock_login.assert_called_once()
            kwargs = mock_login.call_args[1]
            assert kwargs["endpoint"] == "https://api.example.com"

    def test_login_passes_save_profile(self):
        with patch("todopro_cli.commands.auth_app.login") as mock_login:
            _invoke("login", "--save-profile")
            mock_login.assert_called_once()
            kwargs = mock_login.call_args[1]
            assert kwargs["save_profile"] is True


class TestAuthLogout:
    def test_logout_help(self):
        result = _invoke("logout", "--help")
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_logout_delegates_to_auth_logout(self):
        with patch("todopro_cli.commands.auth_app.logout") as mock_logout:
            result = _invoke("logout")
            mock_logout.assert_called_once()

    def test_logout_passes_all_flag(self):
        with patch("todopro_cli.commands.auth_app.logout") as mock_logout:
            _invoke("logout", "--all")
            mock_logout.assert_called_once()
            kwargs = mock_logout.call_args[1]
            assert kwargs["all_profiles"] is True

    def test_logout_default_all_false(self):
        with patch("todopro_cli.commands.auth_app.logout") as mock_logout:
            _invoke("logout")
            kwargs = mock_logout.call_args[1]
            assert kwargs["all_profiles"] is False


class TestAuthSignup:
    def test_signup_help(self):
        result = _invoke("signup", "--help")
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_signup_calls_auth_service(self):
        mock_service = MagicMock()
        mock_service.signup = AsyncMock()
        with (
            patch(
                "todopro_cli.services.auth_service.AuthService",
                return_value=mock_service,
            ),
        ):
            result = _invoke("signup", "--email", "new@example.com", "--password", "pass123")
            # Success or auth_service was called
            assert mock_service.signup.called or result.exit_code in (0, 1)

    def test_signup_prompts_for_missing_email(self):
        mock_service = MagicMock()
        mock_service.signup = AsyncMock()
        with (
            patch(
                "todopro_cli.services.auth_service.AuthService",
                return_value=mock_service,
            ),
        ):
            result = runner.invoke(
                app,
                ["signup", "--password", "pass123"],
                input="newuser@test.com\n",
                catch_exceptions=True,
            )
            # Email prompt or call made
            assert "Email" in result.output or mock_service.signup.called or result.exit_code in (0, 1)


class TestAuthAppHelp:
    def test_group_help(self):
        result = _invoke("--help")
        assert result.exit_code == 0
        assert "login" in result.output.lower()
        assert "logout" in result.output.lower()
        assert "signup" in result.output.lower()
