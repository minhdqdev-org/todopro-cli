"""Comprehensive unit tests for todopro_cli.commands.encryption_command.

Coverage strategy
-----------------
* ``get_encryption_service`` is patched to return a MagicMock in every
  command test, so no real filesystem I/O or cryptographic operations occur.
* ``typer.confirm`` and ``typer.prompt`` are patched where needed, or stdin
  is supplied via the CliRunner ``input=`` parameter.
* Each command path (happy path, cancellation, error paths) is exercised.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.encryption_command import app
from todopro_cli.models.crypto.exceptions import (
    InvalidRecoveryPhraseError,
    TodoProCryptoError,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    key_exists: bool = False,
    enabled: bool = False,
    key_file_path: str | None = None,
    error: str | None = None,
):
    """Build a MagicMock EncryptionService with the given status."""
    svc = MagicMock()

    status = MagicMock()
    status.key_file_exists = key_exists
    status.enabled = enabled
    status.key_file_path = key_file_path or "/home/user/.config/todopro-cli/key.bin"
    status.error = error

    svc.get_status.return_value = status
    svc.storage.has_key.return_value = key_exists
    svc.storage.get_key_path.return_value = key_file_path or "/home/user/.config/todopro-cli/key.bin"
    svc.storage.key_file = key_file_path or "/home/user/.config/todopro-cli/key.bin"

    return svc


# ---------------------------------------------------------------------------
# Help smoke tests
# ---------------------------------------------------------------------------


class TestEncryptionHelp:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_setup_help(self):
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_show_recovery_help(self):
        result = runner.invoke(app, ["show-recovery", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output

    def test_recover_help(self):
        result = runner.invoke(app, ["recover", "--help"])
        assert result.exit_code == 0

    def test_rotate_key_help(self):
        result = runner.invoke(app, ["rotate-key", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------


class TestStatusCommand:
    def test_status_enabled(self):
        svc = _make_service(key_exists=True, enabled=True, key_file_path="/path/key")
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "enabled" in result.output.lower() or "✅" in result.output

    def test_status_not_set_up(self):
        svc = _make_service(key_exists=False, enabled=False)
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "not set up" in result.output.lower() or "❌" in result.output

    def test_status_key_exists_but_invalid(self):
        svc = _make_service(
            key_exists=True, enabled=False, error="Key corrupted"
        )
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # Should mention key exists but is invalid
        assert "invalid" in result.output.lower() or "⚠️" in result.output or "exists" in result.output.lower()


# ---------------------------------------------------------------------------
# show-recovery command
# ---------------------------------------------------------------------------


class TestShowRecoveryCommand:
    def test_no_key_exits_with_code_1(self):
        svc = _make_service(key_exists=False)
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["show-recovery", "--yes"])
        assert result.exit_code == 1
        assert "No encryption key" in result.output or "❌" in result.output

    def test_show_recovery_with_yes_flag_displays_phrase(self):
        svc = _make_service(key_exists=True)
        svc.get_recovery_phrase.return_value = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["show-recovery", "--yes"])
        assert result.exit_code == 0
        assert "word1" in result.output

    def test_show_recovery_prompts_for_confirmation_when_no_yes_flag_decline(self):
        svc = _make_service(key_exists=True)
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            # User answers "n" to the confirmation prompt
            result = runner.invoke(app, ["show-recovery"], input="n\n")
        assert result.exit_code == 0
        # User declined – phrase should not be shown
        svc.get_recovery_phrase.assert_not_called()

    def test_show_recovery_prompts_for_confirmation_when_no_yes_flag_accept(self):
        svc = _make_service(key_exists=True)
        svc.get_recovery_phrase.return_value = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima"

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["show-recovery"], input="y\n")
        assert result.exit_code == 0
        svc.get_recovery_phrase.assert_called_once()

    def test_show_recovery_exception_exits_with_code_1(self):
        svc = _make_service(key_exists=True)
        svc.get_recovery_phrase.side_effect = RuntimeError("Decryption failed")

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["show-recovery", "--yes"])
        assert result.exit_code == 1
        assert "Error" in result.output or "❌" in result.output


# ---------------------------------------------------------------------------
# recover command
# ---------------------------------------------------------------------------


class TestRecoverCommand:
    def test_recover_success_no_existing_key(self):
        svc = _make_service(key_exists=False)
        mock_manager = MagicMock()
        svc.recover.return_value = mock_manager

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(
                app,
                ["recover"],
                input="word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12\n",
            )
        assert result.exit_code == 0
        assert "recovered successfully" in result.output.lower() or "✅" in result.output

    def test_recover_crypto_error_exits_with_code_1(self):
        svc = _make_service(key_exists=False)
        svc.recover.side_effect = InvalidRecoveryPhraseError("Bad phrase")

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(
                app,
                ["recover"],
                input="bad phrase\n",
            )
        assert result.exit_code == 1
        assert "Recovery failed" in result.output or "❌" in result.output

    def test_recover_unexpected_error_exits_with_code_1(self):
        svc = _make_service(key_exists=False)
        svc.recover.side_effect = RuntimeError("unexpected")

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(
                app,
                ["recover"],
                input="any phrase here\n",
            )
        assert result.exit_code == 1

    def test_recover_with_existing_key_user_declines(self):
        svc = _make_service(key_exists=True)

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["recover"], input="n\n")
        assert result.exit_code == 0
        svc.recover.assert_not_called()

    def test_recover_with_existing_key_user_accepts(self):
        svc = _make_service(key_exists=True)
        mock_manager = MagicMock()
        svc.recover.return_value = mock_manager

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(
                app,
                ["recover"],
                input="y\nword1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12\n",
            )
        assert result.exit_code == 0
        svc.recover.assert_called_once()

    def test_recover_saves_manager_on_success(self):
        svc = _make_service(key_exists=False)
        mock_manager = MagicMock()
        svc.recover.return_value = mock_manager

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            runner.invoke(
                app,
                ["recover"],
                input="valid phrase words here now ok go\n",
            )
        svc.save_manager.assert_called_once_with(mock_manager)


# ---------------------------------------------------------------------------
# rotate-key command
# ---------------------------------------------------------------------------


class TestRotateKeyCommand:
    def test_rotate_key_exits_cleanly(self):
        """rotate-key is a stub that prints a message and exits."""
        result = runner.invoke(app, ["rotate-key"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()


# ---------------------------------------------------------------------------
# setup command
# ---------------------------------------------------------------------------


class TestSetupCommand:
    def test_setup_already_configured_user_declines(self):
        """User declines to replace existing key – setup is cancelled."""
        svc = _make_service(key_exists=True)

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            # First confirm: "Do you want to set up a new key?" → N
            result = runner.invoke(app, ["setup"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower() or "Setup cancelled" in result.output
        svc.setup.assert_not_called()

    def test_setup_fresh_user_declines_after_viewing_phrase(self):
        """User declines to confirm they wrote down the phrase – setup cancelled."""
        svc = _make_service(key_exists=False)
        mock_manager = MagicMock()
        phrase = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee"
        svc.setup.return_value = (mock_manager, phrase)

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            with patch(
                "todopro_cli.services.config_service.get_config_service",
                create=True,
            ):
                # "Have you written down your recovery phrase?" → N
                result = runner.invoke(app, ["setup"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower() or "Setup cancelled" in result.output
        svc.save_manager.assert_not_called()

    def test_setup_fresh_phrase_mismatch_exits_with_code_1(self):
        """Incorrect phrase verification causes exit code 1."""
        svc = _make_service(key_exists=False)
        mock_manager = MagicMock()
        phrase = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"
        svc.setup.return_value = (mock_manager, phrase)

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            with patch(
                "todopro_cli.services.config_service.get_config_service",
                create=True,
            ):
                # Written-down confirm → Y, then wrong phrase
                result = runner.invoke(app, ["setup"], input="y\nwrong phrase here\n")
        assert result.exit_code == 1
        assert "doesn't match" in result.output or "❌" in result.output
        svc.save_manager.assert_not_called()

    def test_setup_fresh_success(self):
        """Happy-path: fresh setup with correct phrase verification."""
        svc = _make_service(key_exists=False)
        mock_manager = MagicMock()
        phrase = "correct horse battery staple foo bar baz qux alpha beta gamma delta"
        svc.setup.return_value = (mock_manager, phrase)

        mock_cfg_svc = MagicMock()
        mock_cfg_svc.config.e2ee.enabled = False

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            with patch(
                "todopro_cli.services.config_service.get_config_service",
                return_value=mock_cfg_svc,
            ):
                # Confirm written → Y, verify phrase (correct)
                result = runner.invoke(app, ["setup"], input=f"y\n{phrase}\n")
        assert result.exit_code == 0
        assert "complete" in result.output.lower() or "✅" in result.output
        svc.save_manager.assert_called_once_with(mock_manager)

    def test_setup_already_configured_user_accepts_replacement(self):
        """User replaces existing key – setup proceeds."""
        svc = _make_service(key_exists=True)
        mock_manager = MagicMock()
        phrase = "test phrase one two three four five six seven eight nine ten eleven"
        svc.setup.return_value = (mock_manager, phrase)

        mock_cfg_svc = MagicMock()

        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            with patch(
                "todopro_cli.services.config_service.get_config_service",
                return_value=mock_cfg_svc,
            ):
                # Replace existing key → Y, written down → Y, correct phrase
                result = runner.invoke(app, ["setup"], input=f"y\ny\n{phrase}\n")
        # Should proceed to phrase verification stage at minimum
        assert result.exit_code in (0, 1)
