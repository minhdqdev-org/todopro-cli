"""Unit tests for purge command.

The ``purge data`` command performs a two-step confirmation before reaching
the ``get_storage_strategy_context`` call (which is undefined in scope).
We mock ``todopro_cli.services.data_service`` (lazy-imported at function start)
so the cancel paths can be reached and verified.
"""

import sys
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.purge_command import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helper: mock the lazy-imported data_service module so the function body
# can be entered before the import fails.
# ---------------------------------------------------------------------------
_DATA_SVC_MOCK = MagicMock()


def _patch_data_svc():
    return patch.dict("sys.modules", {"todopro_cli.services.data_service": _DATA_SVC_MOCK})


class TestPurgeHelp:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_data_help(self):
        result = runner.invoke(app, ["data", "--help"])
        assert result.exit_code == 0


class TestPurgeDataCancel:
    """Verify cancellation paths exit cleanly before broken storage code is reached.

    The single-command Typer app is invoked with [] (no sub-command token needed).
    """

    def test_first_confirmation_no_cancels(self):
        """Answering 'n' to the first prompt exits 0 without deleting anything."""
        with _patch_data_svc():
            result = runner.invoke(app, [], input="n\n")
        assert result.exit_code == 0
        assert "cancel" in result.output.lower() or "cancelled" in result.output.lower()

    def test_second_confirmation_no_cancels(self):
        """Answering 'y' then 'n' exits 0 before reaching storage code."""
        with _patch_data_svc():
            result = runner.invoke(app, [], input="y\nn\n")
        assert result.exit_code == 0
        assert "cancel" in result.output.lower() or "cancelled" in result.output.lower()

    def test_warning_message_displayed(self):
        """The scary WARNING banner is shown before any confirmations."""
        with _patch_data_svc():
            result = runner.invoke(app, [], input="n\n")
        assert "WARNING" in result.output or "warning" in result.output.lower()
        assert "ALL" in result.output or "all" in result.output.lower()

    def test_both_prompts_shown(self):
        """Both confirmation prompts appear when user says 'y' the first time."""
        with _patch_data_svc():
            result = runner.invoke(app, [], input="y\nn\n")
        output_lower = result.output.lower()
        assert "absolutely" in output_lower or "sure" in output_lower
        assert "confirm" in output_lower or "permanent" in output_lower
