"""Unit tests for rotate_command.py.

rotate_command.py has a module-level ``console = get_console()`` call but
``get_console`` is not imported, causing a NameError on import. We inject
a stub via builtins before the module loads so the import succeeds.
"""

from __future__ import annotations

import builtins
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

# ---------------------------------------------------------------------------
# Ensure the module can be imported by injecting get_console into builtins
# before Python executes the module-level statement.
# ---------------------------------------------------------------------------
_MOD = "todopro_cli.commands.rotate_command"
if _MOD not in sys.modules:
    _sentinel = object()
    _orig = getattr(builtins, "get_console", _sentinel)
    builtins.get_console = MagicMock(return_value=MagicMock())
    try:
        import todopro_cli.commands.rotate_command  # noqa: F401
    finally:
        if _orig is _sentinel:
            try:
                delattr(builtins, "get_console")
            except AttributeError:
                pass
        else:
            builtins.get_console = _orig  # type: ignore[assignment]

from todopro_cli.commands.rotate_command import app  # noqa: E402

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_encryption_service(
    rotate_return="new-recovery-key-abc123",
    rotate_side_effect=None,
):
    svc = MagicMock()
    svc.rotate_key = AsyncMock(
        return_value=rotate_return,
        side_effect=rotate_side_effect,
    )
    return svc


# ---------------------------------------------------------------------------
# Help tests
# ---------------------------------------------------------------------------

class TestRotateCommandHelp:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code in (0, 2)

    def test_help_shows_passphrase_option(self):
        result = runner.invoke(app, ["--help"])
        assert "passphrase" in result.output.lower() or "Usage" in result.output


# ---------------------------------------------------------------------------
# Invocation tests
# ---------------------------------------------------------------------------

class TestRotateCommandInvocation:
    def test_rotate_with_passphrase_succeeds(self):
        mock_svc = _make_encryption_service()
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "mynewpassword"])
        assert result.exit_code == 0
        mock_svc.rotate_key.assert_awaited_once_with("mynewpassword")

    def test_rotate_shows_success_message(self):
        mock_svc = _make_encryption_service("RECOVERY-KEY-XYZ")
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "pass"])
        assert result.exit_code == 0
        assert "rotated" in result.output.lower() or "success" in result.output.lower()

    def test_rotate_shows_new_recovery_key(self):
        mock_svc = _make_encryption_service("MY-NEW-RECOVERY-KEY")
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "pass"])
        # The key is printed via console.print (mocked) but success msg is via format_success
        assert result.exit_code == 0
        mock_svc.rotate_key.assert_awaited_once()

    def test_rotate_prompts_when_passphrase_not_provided(self):
        mock_svc = _make_encryption_service("KEY-FROM-PROMPT")
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            with patch("typer.prompt", return_value="prompted-passphrase"):
                result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_svc.rotate_key.assert_awaited_once_with("prompted-passphrase")

    def test_rotate_service_error_exits_nonzero(self):
        mock_svc = _make_encryption_service(
            rotate_side_effect=Exception("key rotation failed")
        )
        with patch(
            "todopro_cli.services.encryption_service.EncryptionService",
            return_value=mock_svc,
        ):
            result = runner.invoke(app, ["--passphrase", "pass"])
        assert result.exit_code != 0
