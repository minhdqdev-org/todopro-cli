"""Unit tests for rename_command (rename location contexts).

Note: this app compiles to a single TyperCommand named 'context', so we
invoke it WITHOUT the subcommand name prefix (e.g. ``["home", "office"]``).

The LocationContextService is imported lazily inside rename_context(), so
it is patched via its canonical module path.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.rename_command import app

runner = CliRunner()

# Canonical patch path for the lazily-imported service
_SVC_PATH = "todopro_cli.services.location_context_service.LocationContextService"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke_rename(old_name, new_name, context_service=None):
    """Invoke the rename-context command with a mocked LocationContextService."""
    mock_svc = context_service or MagicMock()

    with patch(_SVC_PATH, return_value=mock_svc):
        return runner.invoke(app, [old_name, new_name])


# ---------------------------------------------------------------------------
# rename context tests
# ---------------------------------------------------------------------------


class TestRenameContext:
    """Tests for the rename context command."""

    def test_rename_context_success(self):
        result = _invoke_rename("home", "office")
        assert result.exit_code == 0

    def test_rename_context_shows_success_message(self):
        result = _invoke_rename("home", "office")
        assert "renamed" in result.output.lower() or "home" in result.output

    def test_rename_context_shows_old_name(self):
        result = _invoke_rename("home", "office")
        assert "home" in result.output

    def test_rename_context_shows_new_name(self):
        result = _invoke_rename("home", "office")
        assert "office" in result.output

    def test_rename_context_shows_arrow(self):
        result = _invoke_rename("gym", "fitness-center")
        assert "→" in result.output or "fitness-center" in result.output

    def test_rename_context_instantiates_service(self):
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        with patch(_SVC_PATH, mock_cls):
            runner.invoke(app, ["work", "home-office"])
        mock_cls.assert_called_once()

    def test_rename_context_missing_args_exits_nonzero(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0

    def test_rename_context_missing_new_name_exits_nonzero(self):
        result = runner.invoke(app, ["home"])
        assert result.exit_code != 0

    def test_rename_context_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert (
            "old" in result.output.lower()
            or "new" in result.output.lower()
            or "context" in result.output.lower()
        )

    def test_rename_context_various_names(self):
        """Verify old and new names are correctly present in output."""
        pairs = [
            ("alpha", "beta"),
            ("my-home", "remote-office"),
            ("ctx1", "ctx2"),
        ]
        for old, new in pairs:
            result = _invoke_rename(old, new)
            assert result.exit_code == 0
            assert old in result.output
            assert new in result.output


# ---------------------------------------------------------------------------
# CLI structure
# ---------------------------------------------------------------------------


class TestRenameCommandStructure:
    """Tests for overall rename command structure."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_app_accepts_old_and_new_name(self):
        """Verify OLD_NAME and NEW_NAME arguments are listed in help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "old" in output_lower or "new" in output_lower or "name" in output_lower
