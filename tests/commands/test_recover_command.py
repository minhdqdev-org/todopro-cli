"""Unit tests for recover_command (recover encryption).

Note: this app compiles to a single TyperCommand named 'encryption', so we
invoke it WITHOUT the subcommand name prefix (e.g. ``["my-key"]``).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.recover_command import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke_recover(recovery_key, service=None):
    """Invoke the recover-encryption command with ``recovery_key`` as argument."""
    mock_svc = service or MagicMock()
    if not isinstance(getattr(mock_svc, "recover", None), AsyncMock):
        mock_svc.recover = AsyncMock(return_value=None)

    with patch(
        "todopro_cli.commands.recover_command.get_encryption_service",
        return_value=mock_svc,
    ):
        return runner.invoke(app, [recovery_key])


# ---------------------------------------------------------------------------
# recover encryption tests
# ---------------------------------------------------------------------------


class TestRecoverEncryption:
    """Tests for the recover encryption command."""

    def test_recover_encryption_success(self):
        result = _invoke_recover("my-recovery-key")
        assert result.exit_code == 0

    def test_recover_encryption_shows_success_message(self):
        result = _invoke_recover("my-recovery-key")
        assert "recovered" in result.output.lower() or "success" in result.output.lower()

    def test_recover_encryption_calls_recover_with_key(self):
        mock_svc = MagicMock()
        mock_svc.recover = AsyncMock(return_value=None)

        with patch(
            "todopro_cli.commands.recover_command.get_encryption_service",
            return_value=mock_svc,
        ):
            runner.invoke(app, ["super-secret-key"])
        mock_svc.recover.assert_awaited_once_with("super-secret-key")

    def test_recover_encryption_service_error_exits_nonzero(self):
        mock_svc = MagicMock()
        mock_svc.recover = AsyncMock(side_effect=Exception("Invalid recovery key"))

        with patch(
            "todopro_cli.commands.recover_command.get_encryption_service",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["bad-key"])
        assert result.exit_code != 0

    def test_recover_encryption_missing_key_exits_nonzero(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0

    def test_recover_encryption_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "RECOVERY_KEY" in result.output or "key" in result.output.lower()

    def test_recover_encryption_different_keys(self):
        """Verify the key argument is forwarded verbatim for various key formats."""
        for key in ["abc123", "key-with-dashes", "UPPERCASE_KEY"]:
            mock_svc = MagicMock()
            mock_svc.recover = AsyncMock(return_value=None)
            with patch(
                "todopro_cli.commands.recover_command.get_encryption_service",
                return_value=mock_svc,
            ):
                runner.invoke(app, [key])
            mock_svc.recover.assert_awaited_once_with(key)


# ---------------------------------------------------------------------------
# CLI structure
# ---------------------------------------------------------------------------


class TestRecoverCommandStructure:
    """Tests for overall recover command structure."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_app_accepts_recovery_key(self):
        """Verify RECOVERY_KEY argument is listed in help."""
        result = runner.invoke(app, ["--help"])
        assert "RECOVERY_KEY" in result.output or "key" in result.output.lower()
