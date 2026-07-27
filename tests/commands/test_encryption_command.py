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

from typer.testing import CliRunner

from todopro_cli.commands.encryption_command import app

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
    """ADR-0024: status now always reports the feature as discontinued."""

    def test_status_reports_discontinued(self):
        svc = _make_service(key_exists=True, enabled=True, key_file_path="/path/key")
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()

    def test_status_discontinued_even_when_no_key(self):
        svc = _make_service(key_exists=False, enabled=False)
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()

    def test_status_mentions_legacy_key_file_when_present(self):
        svc = _make_service(
            key_exists=True, enabled=False, error="Key corrupted"
        )
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "legacy key file" in result.output.lower()


# ---------------------------------------------------------------------------
# show-recovery command
# ---------------------------------------------------------------------------


class TestDiscontinuedCommands:
    """ADR-0024: show-recovery / recover / rotate-key are inert notices.

    They must not touch EncryptionService, must not prompt, and must exit 0 —
    matching the already-stubbed `setup` / `status` pattern.
    """

    COMMANDS = ["show-recovery", "recover", "rotate-key"]

    def test_all_print_discontinued_notice(self):
        for command in self.COMMANDS:
            result = runner.invoke(app, [command])
            assert result.exit_code == 0, command
            assert "discontinued" in result.output.lower(), command
            assert "adr-0024" in result.output.lower(), command

    def test_none_touch_the_encryption_service(self):
        for command in self.COMMANDS:
            svc = _make_service(key_exists=True)
            with patch(
                "todopro_cli.commands.encryption_command.get_encryption_service",
                return_value=svc,
            ):
                # Empty stdin: a surviving prompt would abort instead of exit 0.
                result = runner.invoke(app, [command], input="")
            assert result.exit_code == 0, command
            svc.get_recovery_phrase.assert_not_called()
            svc.recover.assert_not_called()
            svc.save_manager.assert_not_called()
            svc.storage.has_key.assert_not_called()

    def test_no_dead_end_pointer_back_to_setup(self):
        """The old code told users to run the (also discontinued) `setup`."""
        for command in self.COMMANDS:
            result = runner.invoke(app, [command])
            assert "todopro encryption setup" not in result.output, command

    def test_no_stale_encryption_claims(self):
        """No copy may still imply live encryption or a future capability."""
        banned = [
            "your encrypted data",
            "recovery phrase in plain text",
            "not yet implemented",
            "planned for future release",
            "24-word",
            "12-word",
        ]
        for command in self.COMMANDS:
            output = runner.invoke(app, [command]).output.lower()
            for phrase in banned:
                assert phrase not in output, f"{command}: {phrase}"

    def test_show_recovery_yes_flag_still_accepted(self):
        """Scripts passing --yes must not start failing on an unknown flag."""
        result = runner.invoke(app, ["show-recovery", "--yes"])
        assert result.exit_code == 0


class TestGroupHelp:
    def test_group_help_is_marked_discontinued(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()
        assert "manage end-to-end encryption" not in result.output.lower()

    def test_group_stays_visible_so_users_can_discover_the_notice(self):
        """Deliberately NOT hidden: a command-not-found is worse than a notice."""
        result = runner.invoke(app, ["--help"])
        for command in ["show-recovery", "recover", "rotate-key", "setup", "status"]:
            assert command in result.output




# ---------------------------------------------------------------------------
# setup command
# ---------------------------------------------------------------------------


class TestSetupCommand:
    """ADR-0024: `setup` is discontinued — no key generation, no prompts."""

    def test_setup_prints_discontinued_notice(self):
        result = runner.invoke(app, ["setup"])
        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()

    def test_setup_does_not_generate_a_key_or_prompt(self):
        svc = _make_service(key_exists=False)
        with patch(
            "todopro_cli.commands.encryption_command.get_encryption_service",
            return_value=svc,
        ):
            # No stdin input supplied: if the command still prompted for
            # confirmation, this would raise/hang instead of exiting cleanly.
            result = runner.invoke(app, ["setup"], input="")
        assert result.exit_code == 0
        svc.setup.assert_not_called()
        svc.save_manager.assert_not_called()
