"""Unit tests for the 'use' command.

Covers:
- Switching to a new context (happy path)
- Already on the same context → info message, no switch
- No current context (ValueError/KeyError) → still switches
- Context not found raises an error propagated to user
- Help text
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.use_command import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(name: str = "cloud", type_: str = "remote", source: str = "https://api.example.com"):
    ctx = MagicMock()
    ctx.name = name
    ctx.type = type_
    ctx.source = source
    return ctx


def _make_config_service(current_ctx=None, use_context_result=None, current_raises=None):
    """Build a mock config service."""
    svc = MagicMock()

    if current_raises is not None:
        svc.get_current_context.side_effect = current_raises
    elif current_ctx is not None:
        svc.get_current_context.return_value = current_ctx
    else:
        svc.get_current_context.return_value = _make_context(name="local", type_="local")

    if use_context_result is None:
        use_context_result = _make_context(name="cloud")
    svc.use_context.return_value = use_context_result

    return svc


def _run(args: list[str], *, config_service=None):
    if config_service is None:
        config_service = _make_config_service()

    with patch(
        "todopro_cli.commands.use_command.get_config_service",
        return_value=config_service,
    ):
        # use_command has a single sub-command "context" inside a SuggestingGroup
        # app. With only one registered command, SuggestingGroup routes directly
        # to it – so we pass just the positional NAME argument without repeating
        # the "context" subcommand token.
        return runner.invoke(app, args, catch_exceptions=False)


# ---------------------------------------------------------------------------
# Switching to a different context
# ---------------------------------------------------------------------------


class TestUseSwitchContext:
    """Happy-path: switching to a new (different) context."""

    def test_exits_zero(self):
        result = _run(["cloud"])
        assert result.exit_code == 0, result.output

    def test_shows_switched_message(self):
        result = _run(["cloud"])
        assert "cloud" in result.output.lower() or "switched" in result.output.lower()

    def test_use_context_called_with_name(self):
        svc = _make_config_service()
        _run(["cloud"], config_service=svc)
        svc.use_context.assert_called_once_with("cloud")

    def test_switch_to_local(self):
        local_ctx = _make_context(name="local", type_="local", source="/tmp/db")
        svc = _make_config_service(
            current_ctx=_make_context(name="cloud"),
            use_context_result=local_ctx,
        )
        result = _run(["local"], config_service=svc)
        assert result.exit_code == 0

    def test_switch_shows_context_name_in_output(self):
        new_ctx = _make_context(name="work-remote")
        svc = _make_config_service(use_context_result=new_ctx)
        result = _run(["work-remote"], config_service=svc)
        assert "work-remote" in result.output


# ---------------------------------------------------------------------------
# Already on the same context
# ---------------------------------------------------------------------------


class TestUseAlreadyOnContext:
    """When the current context is the same as requested, no switch occurs."""

    def test_exits_zero(self):
        same_ctx = _make_context(name="cloud")
        svc = _make_config_service(current_ctx=same_ctx)
        result = _run(["cloud"], config_service=svc)
        assert result.exit_code == 0, result.output

    def test_shows_already_using_message(self):
        same_ctx = _make_context(name="cloud")
        svc = _make_config_service(current_ctx=same_ctx)
        result = _run(["cloud"], config_service=svc)
        assert "already" in result.output.lower()

    def test_use_context_not_called_when_same(self):
        same_ctx = _make_context(name="cloud")
        svc = _make_config_service(current_ctx=same_ctx)
        _run(["cloud"], config_service=svc)
        svc.use_context.assert_not_called()

    def test_shows_source_in_output(self):
        same_ctx = _make_context(name="cloud", source="https://api.example.com")
        svc = _make_config_service(current_ctx=same_ctx)
        result = _run(["cloud"], config_service=svc)
        assert "https://api.example.com" in result.output


# ---------------------------------------------------------------------------
# No current context (exception paths)
# ---------------------------------------------------------------------------


class TestUseNoCurrentContext:
    """When get_current_context raises, the switch still proceeds."""

    def test_exits_zero_on_value_error(self):
        svc = _make_config_service(current_raises=ValueError("no context"))
        result = _run(["cloud"], config_service=svc)
        assert result.exit_code == 0, result.output

    def test_exits_zero_on_key_error(self):
        svc = _make_config_service(current_raises=KeyError("context"))
        result = _run(["cloud"], config_service=svc)
        assert result.exit_code == 0, result.output

    def test_use_context_called_after_exception(self):
        svc = _make_config_service(current_raises=ValueError("no context"))
        _run(["cloud"], config_service=svc)
        svc.use_context.assert_called_once_with("cloud")


# ---------------------------------------------------------------------------
# Context not found
# ---------------------------------------------------------------------------


class TestUseContextNotFound:
    """When use_context raises because the context doesn't exist."""

    def test_exits_nonzero_when_context_not_found(self):
        """command_wrapper catches ValueError from use_context and exits 1."""
        svc = _make_config_service()
        svc.use_context.side_effect = ValueError("Context 'nonexistent' not found")
        result = _run(["nonexistent"], config_service=svc)
        # command_wrapper converts unhandled exceptions to Exit(1)
        assert result.exit_code != 0

    def test_output_contains_error_message(self):
        """Error message from ValueError appears in output."""
        svc = _make_config_service()
        svc.use_context.side_effect = ValueError("Context 'nonexistent' not found")
        result = _run(["nonexistent"], config_service=svc)
        assert "nonexistent" in result.output or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------


class TestUseHelp:
    def test_context_help_exits_zero(self):
        result = runner.invoke(app, ["context", "--help"])
        assert result.exit_code == 0

    def test_context_help_mentions_name_argument(self):
        result = runner.invoke(app, ["context", "--help"])
        assert "NAME" in result.output or "name" in result.output.lower()

    def test_top_level_help_exits_zero(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
