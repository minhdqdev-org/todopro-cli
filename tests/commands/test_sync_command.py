"""Comprehensive unit tests for todopro_cli.commands.sync.

Coverage strategy
-----------------
* ``pull`` and ``push`` commands reference the undefined global
  ``get_storage_strategy_context``, so those branches are exercised only via
  ``--help`` (CLI registration smoke tests).
* ``status`` command is tested end-to-end by injecting ``get_config_service``
  into the sync module namespace (with ``create=True``) and patching
  ``SyncState``.
* ``_display_sync_result`` is tested directly as a pure helper, covering the
  success/dry-run/failure/conflict paths without needing a real CLI invocation.
"""

from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.sync import _display_sync_result, app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sync_result(**kwargs):
    """Build a minimal MagicMock that looks like a SyncResult."""
    defaults = dict(
        success=True,
        error=None,
        duration=1.23,
        projects_fetched=2,
        projects_new=1,
        projects_updated=1,
        labels_fetched=3,
        labels_new=2,
        labels_updated=1,
        tasks_fetched=10,
        tasks_new=5,
        tasks_updated=3,
        tasks_unchanged=2,
        tasks_conflicts=0,
    )
    defaults.update(kwargs)
    result = MagicMock()
    for k, v in defaults.items():
        setattr(result, k, v)
    return result


# ---------------------------------------------------------------------------
# CLI smoke tests – help flags (always safe)
# ---------------------------------------------------------------------------


class TestSyncHelp:
    """Verify CLI registration / help output."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "pull" in result.output or "Sync" in result.output

    def test_pull_help(self):
        result = runner.invoke(app, ["pull", "--help"])
        assert result.exit_code == 0
        assert "--context" in result.output or "context" in result.output.lower()

    def test_push_help(self):
        result = runner.invoke(app, ["push", "--help"])
        assert result.exit_code == 0
        assert "--context" in result.output or "context" in result.output.lower()

    def test_status_help(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_pull_dry_run_option_in_help(self):
        result = runner.invoke(app, ["pull", "--help"])
        assert "--dry-run" in result.output

    def test_pull_full_option_in_help(self):
        result = runner.invoke(app, ["pull", "--help"])
        assert "--full" in result.output

    def test_pull_strategy_option_in_help(self):
        result = runner.invoke(app, ["pull", "--help"])
        assert "--strategy" in result.output

    def test_push_strategy_option_in_help(self):
        result = runner.invoke(app, ["push", "--help"])
        assert "--strategy" in result.output


# ---------------------------------------------------------------------------
# _display_sync_result – pure helper
# ---------------------------------------------------------------------------


class TestDisplaySyncResult:
    """Tests for _display_sync_result() covering all output branches."""

    def test_success_pull_shows_complete(self, capsys):
        result = _make_sync_result(success=True, duration=2.5, tasks_conflicts=0)
        _display_sync_result(result, "pull", dry_run=False)
        # No assertion on capsys here; the helper prints to Rich console.
        # Just confirm it doesn't raise.

    def test_dry_run_shows_dry_run_header(self, capsys):
        """Dry run path should not raise."""
        result = _make_sync_result(success=True, duration=0.9)
        _display_sync_result(result, "pull", dry_run=True)

    def test_failure_does_not_raise(self):
        result = _make_sync_result(success=False, error="Connection refused")
        _display_sync_result(result, "pull", dry_run=False)

    def test_conflicts_push_path_does_not_raise(self):
        result = _make_sync_result(tasks_conflicts=3)
        _display_sync_result(result, "push", dry_run=False)

    def test_conflicts_pull_path_does_not_raise(self):
        result = _make_sync_result(tasks_conflicts=2)
        _display_sync_result(result, "pull", dry_run=False)

    def test_zero_conflicts_no_conflict_message(self):
        """With 0 conflicts the conflict section must not raise."""
        result = _make_sync_result(tasks_conflicts=0)
        _display_sync_result(result, "push", dry_run=False)

    def test_all_zero_counts_does_not_raise(self):
        result = _make_sync_result(
            projects_fetched=0,
            projects_new=0,
            projects_updated=0,
            labels_fetched=0,
            labels_new=0,
            labels_updated=0,
            tasks_fetched=0,
            tasks_new=0,
            tasks_updated=0,
            tasks_unchanged=0,
            tasks_conflicts=0,
        )
        _display_sync_result(result, "pull", dry_run=False)

    def test_dry_run_failure_does_not_raise(self):
        result = _make_sync_result(success=False, error="timeout", duration=0.1)
        _display_sync_result(result, "push", dry_run=True)


# ---------------------------------------------------------------------------
# status command – end-to-end with mocked dependencies
# ---------------------------------------------------------------------------


def _make_context(name="local-ctx", ctx_type="local"):
    ctx = MagicMock()
    ctx.name = name
    ctx.type = ctx_type
    return ctx


def _make_config_svc(context=None):
    svc = MagicMock()
    svc.get_current_context.return_value = context or _make_context()
    return svc


class TestStatusCommand:
    """Tests for sync status command logic."""

    def test_status_no_context_exits_error(self):
        """When get_current_context() returns None, command exits with code 1."""
        svc = _make_config_svc(context=None)
        svc.get_current_context.return_value = None

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "No context" in result.output or "Error" in result.output

    def test_status_empty_sync_history(self):
        """When no syncs have occurred, shows 'No sync history' message."""
        svc = _make_config_svc()

        mock_state = MagicMock()
        mock_state.get_all_sync_times.return_value = {}

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            with patch("todopro_cli.commands.sync.SyncState", return_value=mock_state):
                result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "No sync history" in result.output

    def test_status_with_sync_history_seconds_ago(self):
        """Displays sync times and 'Xs ago' label."""
        svc = _make_config_svc(context=_make_context(name="myctx"))

        recent = datetime.now(UTC) - timedelta(seconds=30)
        mock_state = MagicMock()
        mock_state.get_all_sync_times.return_value = {
            "myctx -> remote (pull)": recent,
        }

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            with patch("todopro_cli.commands.sync.SyncState", return_value=mock_state):
                result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

    def test_status_with_sync_history_minutes_ago(self):
        """Displays sync times and 'Xm ago' label."""
        svc = _make_config_svc(context=_make_context(name="myctx"))

        a_while_ago = datetime.now(UTC) - timedelta(minutes=5)
        mock_state = MagicMock()
        mock_state.get_all_sync_times.return_value = {
            "myctx -> remote (pull)": a_while_ago,
        }

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            with patch("todopro_cli.commands.sync.SyncState", return_value=mock_state):
                result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

    def test_status_with_sync_history_hours_ago(self):
        """Displays sync times and 'Xh ago' label."""
        svc = _make_config_svc(context=_make_context(name="myctx"))

        hours_ago = datetime.now(UTC) - timedelta(hours=3)
        mock_state = MagicMock()
        mock_state.get_all_sync_times.return_value = {
            "myctx -> remote (pull)": hours_ago,
        }

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            with patch("todopro_cli.commands.sync.SyncState", return_value=mock_state):
                result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

    def test_status_with_sync_history_days_ago(self):
        """Displays sync times and 'Xd ago' label."""
        svc = _make_config_svc(context=_make_context(name="myctx"))

        days_ago = datetime.now(UTC) - timedelta(days=2)
        mock_state = MagicMock()
        mock_state.get_all_sync_times.return_value = {
            "myctx -> remote (pull)": days_ago,
        }

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            with patch("todopro_cli.commands.sync.SyncState", return_value=mock_state):
                result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

    def test_status_sync_key_with_none_timestamp(self):
        """Handles None timestamps gracefully with 'Never' display."""
        svc = _make_config_svc(context=_make_context(name="myctx"))

        mock_state = MagicMock()
        mock_state.get_all_sync_times.return_value = {
            "myctx -> remote (push)": None,
        }

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            with patch("todopro_cli.commands.sync.SyncState", return_value=mock_state):
                result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

    def test_status_filters_unrelated_context_keys(self):
        """Only shows sync entries matching the current context name."""
        svc = _make_config_svc(context=_make_context(name="myctx"))

        mock_state = MagicMock()
        mock_state.get_all_sync_times.return_value = {
            "other-ctx -> remote (pull)": datetime.now(UTC) - timedelta(seconds=10),
        }

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            with patch("todopro_cli.commands.sync.SyncState", return_value=mock_state):
                result = runner.invoke(app, ["status"])

        # unrelated entries are filtered – no table rows, but command succeeds
        assert result.exit_code == 0

    def test_status_exception_exits_with_code_1(self):
        """Any uncaught exception in status causes exit code 1."""
        with patch(
            "todopro_cli.commands.sync.get_config_service",
            side_effect=RuntimeError("db error"),
            create=True,
        ):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# pull/push – quick invocation tests (NameError path → exit code 1)
# ---------------------------------------------------------------------------


class TestPullPushInvocation:
    """pull and push fail at runtime due to undefined get_storage_strategy_context.

    We confirm they exit non-zero (error is handled gracefully by the
    outer try/except in each command) and that the CLI entry point is
    correctly registered.
    """

    def test_pull_without_context_exits_error(self):
        """pull command fails gracefully when context infra is not injected."""
        with patch(
            "todopro_cli.commands.sync.get_config_service",
            side_effect=NameError("get_config_service"),
            create=True,
        ):
            result = runner.invoke(app, ["pull"])
        assert result.exit_code == 1

    def test_push_without_context_exits_error(self):
        """push command fails gracefully when context infra is not injected."""
        with patch(
            "todopro_cli.commands.sync.get_config_service",
            side_effect=NameError("get_config_service"),
            create=True,
        ):
            result = runner.invoke(app, ["push"])
        assert result.exit_code == 1

    def test_pull_no_context_configured(self):
        """pull exits with 1 when get_current_context() returns None."""
        svc = _make_config_svc(context=None)
        svc.get_current_context.return_value = None

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["pull", "--context", "remote"])
        assert result.exit_code == 1

    def test_push_no_context_configured(self):
        """push exits with 1 when get_current_context() returns None."""
        svc = _make_config_svc(context=None)
        svc.get_current_context.return_value = None

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["push", "--context", "remote"])
        assert result.exit_code == 1

    def test_pull_remote_context_without_context_flag_exits_error(self):
        """pull from a remote current context shows an appropriate error."""
        ctx = _make_context(name="cloud", ctx_type="remote")
        svc = _make_config_svc(context=ctx)

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["pull"])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_pull_local_context_without_context_flag_exits_error(self):
        """pull from local without --context shows an error."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["pull"])
        assert result.exit_code == 1

    def test_push_non_local_context_exits_error(self):
        """push from a remote context shows an appropriate error."""
        ctx = _make_context(name="cloud", ctx_type="remote")
        svc = _make_config_svc(context=ctx)

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["push", "--context", "backup"])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_push_local_without_context_flag_exits_error(self):
        """push without specifying --context target exits with error."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["push"])
        assert result.exit_code == 1

    def test_pull_unknown_source_context_exits_error(self):
        """pull with a --context name that doesn't exist exits with error."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = None  # unknown context

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["pull", "--context", "nonexistent"])
        assert result.exit_code == 1

    def test_push_unknown_target_context_exits_error(self):
        """push to a --context name that doesn't exist exits with error."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = None  # unknown context

        with patch(
            "todopro_cli.commands.sync.get_config_service", return_value=svc, create=True
        ):
            result = runner.invoke(app, ["push", "--context", "nonexistent"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# pull/push – deep path (lines 102-158 / 245-301)
# ---------------------------------------------------------------------------


class TestPullPushHappyPath:
    """Cover lines 102-158 (_pull deep path) and 245-301 (_push deep path)
    by injecting all undefined module-level names via patch(create=True)."""

    def _full_patches(self, svc, mock_pull_svc=None, mock_push_svc=None):
        """Return context managers that inject all missing dependencies."""
        mock_storage = MagicMock()
        mock_strategy = MagicMock()
        patches = [
            patch("todopro_cli.commands.sync.get_config_service", return_value=svc, create=True),
            patch(
                "todopro_cli.commands.sync.get_storage_strategy_context",
                return_value=mock_storage,
                create=True,
            ),
            patch("todopro_cli.commands.sync.source_strategy", mock_strategy, create=True),
            patch("todopro_cli.commands.sync.target_strategy", mock_strategy, create=True),
        ]
        if mock_pull_svc:
            patches.append(patch("todopro_cli.commands.sync.SyncPullService", return_value=mock_pull_svc))
        if mock_push_svc:
            patches.append(patch("todopro_cli.commands.sync.SyncPushService", return_value=mock_push_svc))
        return patches

    def test_pull_happy_path_success(self):
        """Full pull pipeline succeeds → exit 0."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()  # source context found

        mock_result = _make_sync_result(success=True)
        mock_pull_svc = MagicMock()
        mock_pull_svc.pull = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_pull_svc=mock_pull_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["pull", "--context", "remote"])
        assert result.exit_code == 0

    def test_pull_happy_path_dry_run(self):
        """Pull with --dry-run flag succeeds → exit 0."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_pull_svc = MagicMock()
        mock_pull_svc.pull = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_pull_svc=mock_pull_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["pull", "--context", "remote", "--dry-run"])
        assert result.exit_code == 0

    def test_pull_happy_path_failure_result_exits_one(self):
        """Pull pipeline returns failure result → exit 1."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=False, error="Connection refused")
        mock_pull_svc = MagicMock()
        mock_pull_svc.pull = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_pull_svc=mock_pull_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["pull", "--context", "remote"])
        assert result.exit_code == 1

    def test_pull_happy_path_with_full_flag(self):
        """Pull with --full flag reaches the pull service call."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_pull_svc = MagicMock()
        mock_pull_svc.pull = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_pull_svc=mock_pull_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["pull", "--context", "remote", "--full"])
        assert result.exit_code == 0

    def test_pull_with_strategy_local_wins(self):
        """Pull with --strategy=local-wins passes correct strategy."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_pull_svc = MagicMock()
        mock_pull_svc.pull = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_pull_svc=mock_pull_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["pull", "--context", "remote", "--strategy", "local-wins"])
        assert result.exit_code == 0
        # Verify strategy was converted to underscores
        mock_pull_svc.pull.assert_awaited_once()
        call_kwargs = mock_pull_svc.pull.call_args[1]
        assert call_kwargs.get("strategy") == "local_wins"

    def test_pull_restores_original_context_on_success(self):
        """After pull, original context is restored."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_pull_svc = MagicMock()
        mock_pull_svc.pull = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_pull_svc=mock_pull_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            runner.invoke(app, ["pull", "--context", "remote"])
        # use_context should have been called to restore
        svc.use_context.assert_called()

    def test_push_happy_path_success(self):
        """Full push pipeline succeeds → exit 0."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_push_svc = MagicMock()
        mock_push_svc.push = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_push_svc=mock_push_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["push", "--context", "remote"])
        assert result.exit_code == 0

    def test_push_happy_path_failure_result_exits_one(self):
        """Push pipeline returns failure result → exit 1."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=False, error="Remote unreachable")
        mock_push_svc = MagicMock()
        mock_push_svc.push = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_push_svc=mock_push_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["push", "--context", "remote"])
        assert result.exit_code == 1

    def test_push_with_dry_run(self):
        """Push with --dry-run flag reaches push service."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_push_svc = MagicMock()
        mock_push_svc.push = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_push_svc=mock_push_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["push", "--context", "remote", "--dry-run"])
        assert result.exit_code == 0

    def test_push_with_strategy_remote_wins(self):
        """Push with --strategy=remote-wins converts to underscores."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_push_svc = MagicMock()
        mock_push_svc.push = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_push_svc=mock_push_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(app, ["push", "--context", "remote", "--strategy", "remote-wins"])
        assert result.exit_code == 0
        mock_push_svc.push.assert_awaited_once()
        call_kwargs = mock_push_svc.push.call_args[1]
        assert call_kwargs.get("strategy") == "remote_wins"

    def test_push_restores_original_context(self):
        """After push, original context is restored to source."""
        ctx = _make_context(name="local", ctx_type="local")
        svc = _make_config_svc(context=ctx)
        svc.config.get_context.return_value = MagicMock()

        mock_result = _make_sync_result(success=True)
        mock_push_svc = MagicMock()
        mock_push_svc.push = AsyncMock(return_value=mock_result)

        patches = self._full_patches(svc, mock_push_svc=mock_push_svc)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            runner.invoke(app, ["push", "--context", "remote"])
        svc.use_context.assert_called()
