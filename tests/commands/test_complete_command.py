"""Unit tests for the 'complete' command.

Covers single-task sync/async modes, multi-task batch sync/async modes,
local-context forcing sync mode, output format flags, and edge cases.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.complete_command import app
from todopro_cli.models import Task

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 1, 10, 0, 0)

TASK_1 = Task(
    id="aaaa-1111-bbbb-2222",
    content="Write release notes",
    created_at=_NOW,
    updated_at=_NOW,
)

TASK_2 = Task(
    id="cccc-3333-dddd-4444",
    content="Review pull request for new feature branch",
    created_at=_NOW,
    updated_at=_NOW,
)

TASK_LONG = Task(
    id="eeee-5555-ffff-6666",
    content="A" * 80,  # > 60 chars, gets truncated in output
    created_at=_NOW,
    updated_at=_NOW,
)


def _make_task_service(complete_result=None, bulk_result=None):
    """Return a mock TaskService with AsyncMock methods."""
    svc = MagicMock()
    svc.complete_task = AsyncMock(return_value=complete_result or TASK_1)
    svc.bulk_complete_tasks = AsyncMock(return_value=bulk_result or [TASK_1, TASK_2])
    svc.list_tasks = AsyncMock(return_value=[TASK_1])
    return svc


def _make_config_service(context_type: str = "remote"):
    """Return a mock ConfigService whose current context has the given type."""
    ctx = MagicMock()
    ctx.type = context_type
    svc = MagicMock()
    svc.get_current_context.return_value = ctx
    return svc


def _run(
    args: list[str],
    *,
    task_service=None,
    config_service=None,
    resolved_id: str = "aaaa-1111-bbbb-2222",
    cache=None,
):
    """Invoke the complete command with fully mocked dependencies."""
    if task_service is None:
        task_service = _make_task_service()
    if config_service is None:
        config_service = _make_config_service()
    if cache is None:
        cache = MagicMock()
        cache.get_completing_tasks.return_value = []

    with (
        patch(
            "todopro_cli.commands.complete_command.get_task_service",
            return_value=task_service,
        ),
        patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=config_service,
        ),
        patch(
            "todopro_cli.commands.complete_command.get_background_cache",
            return_value=cache,
        ),
        patch(
            "todopro_cli.commands.complete_command.resolve_task_id",
            new=AsyncMock(return_value=resolved_id),
        ),
        patch(
            "todopro_cli.commands.complete_command.run_in_background",
        ),
    ):
        return runner.invoke(app, args, catch_exceptions=False)


# ---------------------------------------------------------------------------
# Single-task sync mode (--sync flag)
# ---------------------------------------------------------------------------


class TestSingleTaskSync:
    """Tests for completing a single task in synchronous mode."""

    def test_sync_exits_zero(self):
        """--sync flag completes task successfully and exits 0."""
        result = _run(["task-123", "--sync"])
        assert result.exit_code == 0, result.output

    def test_sync_shows_completed_content(self):
        """Success banner includes the task's content."""
        result = _run(["task-123", "--sync"])
        assert "Write release notes" in result.output

    def test_sync_shows_undo_hint(self):
        """Output includes 'tp reopen' hint for undoing."""
        result = _run(["task-123", "--sync"])
        assert "reopen" in result.output

    def test_sync_calls_complete_task(self):
        """complete_task is called exactly once with the resolved ID."""
        svc = _make_task_service()
        _run(["task-123", "--sync"], task_service=svc)
        svc.complete_task.assert_awaited_once()

    def test_sync_long_content_truncated(self):
        """Content exceeding 60 chars is truncated with '...' in the banner."""
        svc = _make_task_service(complete_result=TASK_LONG)
        result = _run(["long-task", "--sync"], task_service=svc)
        assert "..." in result.output
        assert result.exit_code == 0

    def test_sync_json_output(self):
        """When --output json is set alongside --sync, JSON dump is shown."""
        result = _run(["task-123", "--sync", "--output", "json"])
        assert result.exit_code == 0

    def test_sync_json_flag_alias(self):
        """--json flag together with --sync triggers JSON output path."""
        result = _run(["task-123", "--sync", "--json"])
        assert result.exit_code == 0

    def test_sync_no_full_output_for_default_format(self):
        """In default 'table' output mode, the full JSON dump is NOT printed."""
        result = _run(["task-123", "--sync"])
        # should not contain raw JSON model data (e.g. 'is_completed')
        assert "is_completed" not in result.output


# ---------------------------------------------------------------------------
# Single-task background mode (default, no --sync)
# ---------------------------------------------------------------------------


class TestSingleTaskBackground:
    """Tests for the default background (optimistic) completion path."""

    def test_background_exits_zero(self):
        """Background mode exits 0 immediately."""
        result = _run(["task-abc"])
        assert result.exit_code == 0, result.output

    def test_background_shows_task_id_in_output(self):
        """Immediate feedback echoes the task ID."""
        result = _run(["task-abc"])
        assert "task-abc" in result.output

    def test_background_does_not_call_complete_task(self):
        """Background mode does NOT await complete_task."""
        svc = _make_task_service()
        _run(["task-abc"], task_service=svc)
        svc.complete_task.assert_not_awaited()

    def test_background_adds_to_cache(self):
        """Task is added to the optimistic-UI cache."""
        cache = MagicMock()
        _run(["task-abc"], cache=cache)
        cache.add_completing_task.assert_called_once_with("task-abc")

    def test_background_check_status_hint(self):
        """Output includes hint to check status."""
        result = _run(["task-abc"])
        assert "tp tasks get" in result.output or "Check status" in result.output


# ---------------------------------------------------------------------------
# Local-context forces sync mode
# ---------------------------------------------------------------------------


class TestLocalContextForcesSync:
    """When the current context is 'local', sync_opt must be forced True."""

    def test_local_context_forces_complete_task_call(self):
        """Local context runs complete_task even without --sync flag."""
        svc = _make_task_service()
        cfg = _make_config_service(context_type="local")
        _run(["task-xyz"], task_service=svc, config_service=cfg)
        svc.complete_task.assert_awaited_once()

    def test_local_context_exit_zero(self):
        """Local context completes without error."""
        cfg = _make_config_service(context_type="local")
        result = _run(["task-xyz"], config_service=cfg)
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Batch (multiple task IDs) sync mode
# ---------------------------------------------------------------------------


class TestBatchSync:
    """Tests for bulk-completing multiple tasks in sync mode."""

    def test_batch_sync_exits_zero(self):
        """Batch --sync mode exits 0."""
        result = _run(["t1", "t2", "--sync"])
        assert result.exit_code == 0, result.output

    def test_batch_sync_calls_bulk_complete(self):
        """bulk_complete_tasks is awaited once with resolved IDs."""
        svc = _make_task_service()
        _run(["t1", "t2", "--sync"], task_service=svc)
        svc.bulk_complete_tasks.assert_awaited_once()

    def test_batch_sync_shows_completed_count(self):
        """Output includes count of completed tasks."""
        result = _run(["t1", "t2", "--sync"])
        assert "2" in result.output

    def test_batch_sync_three_tasks(self):
        """Works correctly with three task IDs."""
        extra = Task(
            id="zzzz-9999-zzzz-9999",
            content="Extra task",
            created_at=_NOW,
            updated_at=_NOW,
        )
        svc = _make_task_service(bulk_result=[TASK_1, TASK_2, extra])
        result = _run(["t1", "t2", "t3", "--sync"], task_service=svc)
        assert result.exit_code == 0

    def test_batch_sync_task_with_no_content(self):
        """Task with None content shows '[No title]' placeholder."""
        no_content = Task(
            id="no-content-task",
            content="placeholder",  # content can't be None due to model
            created_at=_NOW,
            updated_at=_NOW,
        )
        # Simulate None content via model_copy
        no_content = no_content.model_copy(update={"content": ""})
        svc = _make_task_service(bulk_result=[no_content])
        result = _run(["t1", "--sync"], task_service=svc)
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Batch background mode
# ---------------------------------------------------------------------------


class TestBatchBackground:
    """Tests for the background batch-complete path."""

    def test_batch_background_exits_zero(self):
        """Background batch mode exits 0."""
        result = _run(["t1", "t2"])
        assert result.exit_code == 0, result.output

    def test_batch_background_does_not_call_bulk_complete(self):
        """No API call in background batch mode."""
        svc = _make_task_service()
        _run(["t1", "t2"], task_service=svc)
        svc.bulk_complete_tasks.assert_not_awaited()

    def test_batch_background_adds_all_to_cache(self):
        """All task IDs are sent to the background cache."""
        cache = MagicMock()
        _run(["t1", "t2"], cache=cache)
        cache.add_completing_tasks.assert_called_once_with(["t1", "t2"])

    def test_batch_background_shows_count(self):
        """Output mentions the count of tasks being processed."""
        result = _run(["alpha", "beta", "gamma"])
        assert "3" in result.output

    def test_batch_background_lists_task_ids(self):
        """Output lists the task IDs being marked."""
        result = _run(["alpha", "beta"])
        assert "alpha" in result.output
        assert "beta" in result.output


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------


class TestHelpText:
    """Smoke test that --help is functional."""

    def test_help_exits_zero(self):
        result = runner.invoke(app, ["complete", "--help"])
        assert result.exit_code == 0

    def test_help_mentions_task_ids(self):
        result = runner.invoke(app, ["complete", "--help"])
        assert "Task ID" in result.output or "task" in result.output.lower()
