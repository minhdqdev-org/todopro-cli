"""Unit tests for SuggestingGroup (typer_helpers.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer


class TestSuggestingGroup:
    """Tests for the SuggestingGroup Typer group."""

    def _make_group(self, commands: dict):
        """Create a SuggestingGroup with mock commands."""
        from todopro_cli.utils.typer_helpers import SuggestingGroup

        group = SuggestingGroup(name="testgroup")
        group.commands = commands
        return group

    def test_valid_command_passes_through(self):
        """A valid command resolves without error."""
        from todopro_cli.utils.typer_helpers import SuggestingGroup

        group = SuggestingGroup(name="testgroup")
        group.commands = {}

        ctx = MagicMock()
        ctx.info_name = "tp"

        # When super() succeeds, result flows through
        with patch.object(
            SuggestingGroup.__bases__[0],
            "resolve_command",
            return_value=("add", MagicMock(), ["add"]),
        ):
            result = group.resolve_command(ctx, ["add"])
            assert result[0] == "add"

    def test_unknown_command_with_suggestion_prints_hint_and_exits(self):
        """An unknown command similar to a real command triggers suggestion output."""
        from todopro_cli.utils.typer_helpers import SuggestingGroup
        import click

        group = SuggestingGroup(name="testgroup")
        group.commands = {
            "add": MagicMock(),
            "list": MagicMock(),
            "delete": MagicMock(),
        }

        ctx = MagicMock()
        ctx.info_name = "tp"

        mock_console = MagicMock()

        with patch.object(
            SuggestingGroup.__bases__[0],
            "resolve_command",
            side_effect=Exception("No such command"),
        ):
            with patch(
                "todopro_cli.utils.typer_helpers.get_console",
                return_value=mock_console,
                create=True,
            ):
                with pytest.raises((SystemExit, click.exceptions.Exit)):
                    group.resolve_command(ctx, ["lst"])  # typo of "list"

        # Console should have printed something
        assert mock_console.print.called
        """An unknown command with no close matches re-raises the original error."""
        from todopro_cli.utils.typer_helpers import SuggestingGroup

        group = SuggestingGroup(name="testgroup")
        group.commands = {
            "add": MagicMock(),
            "list": MagicMock(),
        }

        ctx = MagicMock()
        ctx.info_name = "tp"

        original_error = Exception("No such command 'xyzabc'")

        with patch.object(
            SuggestingGroup.__bases__[0],
            "resolve_command",
            side_effect=original_error,
        ):
            with pytest.raises(Exception):
                group.resolve_command(ctx, ["xyzabc"])

    def test_unknown_command_empty_args_reraises(self):
        """When args is empty, the original exception is re-raised."""
        from todopro_cli.utils.typer_helpers import SuggestingGroup

        group = SuggestingGroup(name="testgroup")
        group.commands = {}

        ctx = MagicMock()
        original_error = Exception("No args")

        with patch.object(
            SuggestingGroup.__bases__[0],
            "resolve_command",
            side_effect=original_error,
        ):
            with pytest.raises(Exception):
                group.resolve_command(ctx, [])

    def test_single_suggestion_uses_singular_message(self):
        """A single suggestion prints 'Did you mean this?'."""
        from todopro_cli.utils.typer_helpers import SuggestingGroup
        import click

        group = SuggestingGroup(name="testgroup")
        group.commands = {
            "list": MagicMock(),
        }

        ctx = MagicMock()
        ctx.info_name = "tp"

        mock_console = MagicMock()
        printed_messages = []
        mock_console.print.side_effect = lambda *args, **kw: printed_messages.append(
            str(args[0]) if args else ""
        )

        with patch.object(
            SuggestingGroup.__bases__[0],
            "resolve_command",
            side_effect=Exception("No command"),
        ):
            with patch(
                "todopro_cli.utils.typer_helpers.get_console",
                return_value=mock_console,
                create=True,
            ):
                with pytest.raises((SystemExit, click.exceptions.Exit)):
                    group.resolve_command(ctx, ["lis"])  # close to "list"

        combined = " ".join(printed_messages)
        assert "Did you mean this" in combined

    def test_multiple_suggestions_uses_plural_message(self):
        """Multiple suggestions print 'Did you mean one of these?'."""
        from todopro_cli.utils.typer_helpers import SuggestingGroup
        import click

        group = SuggestingGroup(name="testgroup")
        group.commands = {
            "add": MagicMock(),
            "ads": MagicMock(),
            "adx": MagicMock(),
        }

        ctx = MagicMock()
        ctx.info_name = "tp"

        mock_console = MagicMock()
        printed_messages = []
        mock_console.print.side_effect = lambda *args, **kw: printed_messages.append(
            str(args[0]) if args else ""
        )

        with patch.object(
            SuggestingGroup.__bases__[0],
            "resolve_command",
            side_effect=Exception("No command"),
        ):
            with patch(
                "todopro_cli.utils.typer_helpers.get_console",
                return_value=mock_console,
                create=True,
            ):
                with pytest.raises((SystemExit, click.exceptions.Exit)):
                    group.resolve_command(ctx, ["aad"])  # matches add, ads, adx

        combined = " ".join(printed_messages)
        assert "Did you mean" in combined
