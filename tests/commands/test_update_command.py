"""Unit tests for the 'update' command.

Covers:
- Already on latest version
- Unable to check for updates
- New version available (confirmed upgrade)
- New version available (user declines)
- Successful uv upgrade
- Failed uv upgrade
- uv not found (FileNotFoundError)
- Generic exception handling
- --yes flag skips confirmation
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.update_command import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _successful_subprocess():
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


def _failed_subprocess(stderr="Error detail"):
    result = MagicMock()
    result.returncode = 1
    result.stdout = ""
    result.stderr = stderr
    return result


def _run(args=None, *, is_available=False, latest_version=None, subprocess_result=None):
    """Invoke the update command with mocked helpers."""
    if subprocess_result is None:
        subprocess_result = _successful_subprocess()

    with (
        patch(
            "todopro_cli.commands.update_command.is_update_available",
            return_value=(is_available, latest_version),
        ),
        patch(
            "todopro_cli.commands.update_command.subprocess.run",
            return_value=subprocess_result,
        ),
    ):
        # update is the only command in the app – do not repeat its name
        return runner.invoke(app, args or [], catch_exceptions=False)


# ---------------------------------------------------------------------------
# Already on latest version
# ---------------------------------------------------------------------------


class TestAlreadyLatest:
    def test_exits_zero(self):
        result = _run(is_available=False, latest_version="1.2.3")
        assert result.exit_code == 0, result.output

    def test_shows_already_latest_message(self):
        result = _run(is_available=False, latest_version="1.2.3")
        assert "latest" in result.output.lower()

    def test_no_subprocess_called(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                return_value=(False, "1.0.0"),
            ),
            patch(
                "todopro_cli.commands.update_command.subprocess.run"
            ) as mock_sub,
        ):
            runner.invoke(app, [], catch_exceptions=False)
        mock_sub.assert_not_called()


# ---------------------------------------------------------------------------
# Unable to check
# ---------------------------------------------------------------------------


class TestUnableToCheck:
    def test_exits_zero(self):
        result = _run(is_available=False, latest_version=None)
        assert result.exit_code == 0, result.output

    def test_shows_warning_message(self):
        result = _run(is_available=False, latest_version=None)
        assert "unable" in result.output.lower() or "⚠" in result.output


# ---------------------------------------------------------------------------
# Update available - user confirms
# ---------------------------------------------------------------------------


class TestUpdateAvailableConfirm:
    def test_exits_zero_when_user_confirms(self):
        # --yes skips the interactive prompt
        result = _run(
            args=["--yes"],
            is_available=True,
            latest_version="9.9.9",
            subprocess_result=_successful_subprocess(),
        )
        assert result.exit_code == 0, result.output

    def test_shows_new_version(self):
        result = _run(
            args=["--yes"],
            is_available=True,
            latest_version="9.9.9",
        )
        assert "9.9.9" in result.output

    def test_shows_success_message_after_update(self):
        result = _run(
            args=["--yes"],
            is_available=True,
            latest_version="9.9.9",
            subprocess_result=_successful_subprocess(),
        )
        assert "success" in result.output.lower() or "updated" in result.output.lower()

    def test_subprocess_run_called_with_uv(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                return_value=(True, "9.9.9"),
            ),
            patch(
                "todopro_cli.commands.update_command.subprocess.run",
                return_value=_successful_subprocess(),
            ) as mock_sub,
        ):
            runner.invoke(app, ["--yes"], catch_exceptions=False)
        mock_sub.assert_called_once()
        call_args = mock_sub.call_args[0][0]
        assert "uv" in call_args
        assert "upgrade" in call_args


# ---------------------------------------------------------------------------
# Update available - user declines
# ---------------------------------------------------------------------------


class TestUpdateAvailableDecline:
    def test_exits_zero_when_user_declines(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                return_value=(True, "9.9.9"),
            ),
            patch(
                "todopro_cli.commands.update_command.subprocess.run"
            ) as mock_sub,
            patch("typer.confirm", return_value=False),
        ):
            result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 0
        mock_sub.assert_not_called()

    def test_shows_cancelled_message(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                return_value=(True, "9.9.9"),
            ),
            patch("todopro_cli.commands.update_command.subprocess.run"),
            patch("typer.confirm", return_value=False),
        ):
            result = runner.invoke(app, [], catch_exceptions=False)
        assert "cancel" in result.output.lower()


# ---------------------------------------------------------------------------
# Upgrade fails
# ---------------------------------------------------------------------------


class TestUpgradeFails:
    def test_exits_nonzero_when_subprocess_fails(self):
        result = _run(
            args=["--yes"],
            is_available=True,
            latest_version="9.9.9",
            subprocess_result=_failed_subprocess(stderr="uv error"),
        )
        assert result.exit_code != 0

    def test_shows_failure_message(self):
        result = _run(
            args=["--yes"],
            is_available=True,
            latest_version="9.9.9",
            subprocess_result=_failed_subprocess(stderr="permission denied"),
        )
        assert "fail" in result.output.lower() or "✗" in result.output

    def test_shows_stderr_content(self):
        result = _run(
            args=["--yes"],
            is_available=True,
            latest_version="9.9.9",
            subprocess_result=_failed_subprocess(stderr="permission denied"),
        )
        assert "permission denied" in result.output

    def test_shows_manual_upgrade_hint(self):
        result = _run(
            args=["--yes"],
            is_available=True,
            latest_version="9.9.9",
            subprocess_result=_failed_subprocess(),
        )
        assert "uv tool upgrade" in result.output


# ---------------------------------------------------------------------------
# uv not found
# ---------------------------------------------------------------------------


class TestUvNotFound:
    def test_exits_nonzero(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                return_value=(True, "9.9.9"),
            ),
            patch(
                "todopro_cli.commands.update_command.subprocess.run",
                side_effect=FileNotFoundError,
            ),
        ):
            result = runner.invoke(app, ["--yes"], catch_exceptions=False)
        assert result.exit_code != 0

    def test_shows_uv_not_found_message(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                return_value=(True, "9.9.9"),
            ),
            patch(
                "todopro_cli.commands.update_command.subprocess.run",
                side_effect=FileNotFoundError,
            ),
        ):
            result = runner.invoke(app, ["--yes"], catch_exceptions=False)
        assert "uv" in result.output.lower()


# ---------------------------------------------------------------------------
# Generic exception
# ---------------------------------------------------------------------------


class TestGenericException:
    def test_exits_nonzero_on_unexpected_error(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                side_effect=RuntimeError("network unreachable"),
            ),
        ):
            result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code != 0

    def test_shows_error_message(self):
        with (
            patch(
                "todopro_cli.commands.update_command.is_update_available",
                side_effect=RuntimeError("network unreachable"),
            ),
        ):
            result = runner.invoke(app, [], catch_exceptions=False)
        assert "network unreachable" in result.output or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------


class TestHelpText:
    def test_help_exits_zero(self):
        result = runner.invoke(app, ["update", "--help"])
        assert result.exit_code == 0

    def test_help_mentions_yes_flag(self):
        result = runner.invoke(app, ["update", "--help"])
        assert "--yes" in result.output or "-y" in result.output
