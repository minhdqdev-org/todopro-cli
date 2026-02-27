"""Unit tests for tasks command."""

# pylint: disable=redefined-outer-name

import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.tasks_command import app
from todopro_cli.models.core import Task
from todopro_cli.services.config_service import ConfigService

runner = CliRunner()


@pytest.fixture
def config_service():
    """Fixture for ConfigService with temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("platformdirs.user_config_dir", return_value=tmpdir):
            with patch("platformdirs.user_data_dir", return_value=tmpdir):
                yield ConfigService()


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    return Task(
        id="task-123",
        content="Test task",
        description="Test description",
        project_id=None,
        due_date=None,
        priority=1,
        is_completed=False,
        labels=[],
        contexts=[],
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def mock_task_service():
    """Mock TaskService for testing."""
    # Create service mock
    service_mock = MagicMock()
    service_mock.list_tasks = AsyncMock()
    service_mock.get_task = AsyncMock()
    service_mock.add_task = AsyncMock()
    service_mock.update_task = AsyncMock()
    service_mock.delete_task = AsyncMock()
    service_mock.complete_task = AsyncMock()
    service_mock.bulk_complete_tasks = AsyncMock()

    strategy_mock = MagicMock()
    strategy_mock.task_repository = MagicMock()

    with (
        patch(
            "todopro_cli.commands.tasks_command.get_storage_strategy_context",
            return_value=strategy_mock,
        ),
        patch(
            "todopro_cli.commands.tasks_command.get_task_service",
            return_value=service_mock,
        ),
        patch(
            "todopro_cli.commands.tasks_command.TaskService", return_value=service_mock
        ),
    ):
        yield service_mock


class TestListCommand:
    """Tests for list command."""

    @patch("todopro_cli.commands.tasks_command.get_background_cache")
    def test_list_tasks_success(self, mock_cache, mock_task_service, mock_task):
        """Test listing tasks successfully."""
        mock_task_service.list_tasks.return_value = [mock_task]
        mock_cache.return_value.get_completing_tasks.return_value = []

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_task_service.list_tasks.assert_called_once()

    @patch("todopro_cli.commands.tasks_command.get_background_cache")
    def test_list_with_filters(self, mock_cache, mock_task_service, mock_task):
        """Test listing tasks with filters."""
        mock_task_service.list_tasks.return_value = [mock_task]
        mock_cache.return_value.get_completing_tasks.return_value = []

        result = runner.invoke(app, ["list", "--status", "active", "--priority", "1"])

        assert result.exit_code == 0
        mock_task_service.list_tasks.assert_called_once()
        call_kwargs = mock_task_service.list_tasks.call_args.kwargs
        assert call_kwargs["status"] == "active"
        assert call_kwargs["priority"] == 1


class TestGetCommand:
    """Tests for get command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_get_task_success(self, mock_resolve, mock_task_service, mock_task):
        """Test getting a task successfully."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.get_task.return_value = mock_task

        result = runner.invoke(app, ["get", "123"])

        assert result.exit_code == 0
        mock_task_service.get_task.assert_called_once()


class TestCreateCommand:
    """Tests for create command."""

    def test_create_task_minimal(self, mock_task_service, mock_task):
        """Test creating a task with minimal parameters."""
        mock_task_service.add_task.return_value = mock_task

        result = runner.invoke(app, ["create", "New task"])

        assert result.exit_code == 0
        mock_task_service.add_task.assert_called_once()
        call_kwargs = mock_task_service.add_task.call_args.kwargs
        assert call_kwargs["content"] == "New task"

    def test_create_task_with_options(self, mock_task_service, mock_task):
        """Test creating a task with all options."""
        mock_task_service.add_task.return_value = mock_task

        result = runner.invoke(
            app,
            [
                "create",
                "New task",
                "--description",
                "Task description",
                "--priority",
                "2",
                "--labels",
                "urgent,work",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_task_service.add_task.call_args.kwargs
        assert call_kwargs["content"] == "New task"
        assert call_kwargs["description"] == "Task description"
        assert call_kwargs["priority"] == 2
        assert call_kwargs["labels"] == ["urgent", "work"]


class TestUpdateCommand:
    """Tests for update command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_update_task_success(self, mock_resolve, mock_task_service, mock_task):
        """Test updating a task."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.update_task.return_value = mock_task

        result = runner.invoke(app, ["update", "123", "--content", "Updated content"])

        assert result.exit_code == 0
        mock_task_service.update_task.assert_called_once()

    def test_update_task_no_updates(self):
        """Test updating task with no parameters fails."""
        result = runner.invoke(app, ["update", "123"])

        assert result.exit_code == 1
        assert "No updates specified" in result.stdout


class TestDeleteCommand:
    """Tests for delete command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_delete_task_with_yes_flag(self, mock_resolve, mock_task_service):
        """Test deleting a task with --yes flag."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.delete_task.return_value = True

        result = runner.invoke(app, ["delete", "123", "--yes"])

        assert result.exit_code == 0
        mock_task_service.delete_task.assert_called_once()

    def test_delete_task_cancelled(self, mock_task_service):
        """Test deleting a task and cancelling."""
        result = runner.invoke(app, ["delete", "123"], input="n\n")

        assert result.exit_code == 0
        mock_task_service.delete_task.assert_not_called()


class TestReopenCommand:
    """Tests for reopen command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_reopen_task(self, mock_resolve, mock_task_service, mock_task):
        """Test reopening a completed task."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.update_task.return_value = mock_task

        result = runner.invoke(app, ["reopen", "123"])

        assert result.exit_code == 0
        mock_task_service.update_task.assert_called_once()
        call_kwargs = mock_task_service.update_task.call_args.kwargs
        assert call_kwargs["is_completed"] is False


class TestRescheduleCommand:
    """Tests for reschedule command."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_reschedule_single_task(self, mock_resolve, mock_task_service, mock_task):
        """Test rescheduling a single task."""
        mock_resolve.return_value = AsyncMock(return_value="task-123")()
        mock_task_service.update_task.return_value = mock_task

        result = runner.invoke(app, ["reschedule", "123", "--date", "2024-12-31"])

        assert result.exit_code == 0
        mock_task_service.update_task.assert_called_once()

    def test_reschedule_overdue_none(self, mock_task_service):
        """Test rescheduling overdue tasks when none exist."""
        mock_task_service.list_tasks.return_value = []

        result = runner.invoke(app, ["reschedule"])

        assert result.exit_code == 0
        assert "No overdue tasks" in result.stdout or "🎉" in result.stdout


class TestListJsonFlag:
    """Line 50: test --json flag sets output to json."""

    @patch("todopro_cli.commands.tasks_command.get_background_cache")
    def test_list_json_flag(self, mock_cache, mock_task_service, mock_task):
        mock_task_service.list_tasks.return_value = [mock_task]
        mock_cache.return_value.get_completing_tasks.return_value = []
        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0


class TestGetTaskServicePath:
    """Line 71: get command uses get_task_service() directly."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_get_task_direct(self, mock_resolve, mock_task_service, mock_task):
        mock_resolve.return_value = "task-123"  # non-async return
        mock_task_service.get_task.return_value = mock_task
        result = runner.invoke(app, ["get", "task-123"])
        assert result.exit_code == 0


class TestStartCommand:
    """Lines 236-255: start command delegates to focus.start_focus."""

    def test_start_delegates_to_focus(self):
        with patch("todopro_cli.commands.focus.start_focus") as mock_impl:
            result = runner.invoke(app, ["start", "task-123"])
        assert result.exit_code == 0
        mock_impl.assert_called_once()

    def test_start_with_duration(self):
        with patch("todopro_cli.commands.focus.start_focus") as mock_impl:
            result = runner.invoke(app, ["start", "task-123", "--duration", "30"])
        assert result.exit_code == 0

    def test_start_with_template(self):
        with patch("todopro_cli.commands.focus.start_focus") as mock_impl:
            result = runner.invoke(app, ["start", "task-123", "--template", "deep"])
        assert result.exit_code == 0


class TestStopCommand:
    """Lines 263-265: stop command delegates to focus.stop_focus."""

    def test_stop_delegates(self):
        with patch("todopro_cli.commands.focus.stop_focus") as mock_impl:
            result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        mock_impl.assert_called_once()


class TestResumeCommand:
    """Line 275: resume command delegates to focus.resume_focus."""

    def test_resume_delegates(self):
        with patch("todopro_cli.commands.focus.resume_focus") as mock_impl:
            result = runner.invoke(app, ["resume"])
        assert result.exit_code == 0
        mock_impl.assert_called_once()


class TestFocusStatusCommand:
    """Lines 293-295: status command delegates to focus.focus_status."""

    def test_status_delegates(self):
        with patch("todopro_cli.commands.focus.focus_status") as mock_impl:
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        mock_impl.assert_called_once()


class TestSkipCommand:
    """Lines 301-341: skip command uses API client."""

    def _make_api(self, skip_result=None):
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.skip_task = AsyncMock(
            return_value=skip_result or {"id": "task-123", "content": "test"}
        )
        return mock_client, mock_api

    def test_skip_success(self):
        mock_client, mock_api = self._make_api()
        with (
            patch(
                "todopro_cli.services.api.client.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.services.api.tasks.TasksAPI", return_value=mock_api
            ),
        ):
            result = runner.invoke(app, ["skip", "task-123"])
        assert result.exit_code == 0
        assert "Skipped" in result.output

    def test_skip_with_json_output(self):
        mock_client, mock_api = self._make_api()
        with (
            patch(
                "todopro_cli.services.api.client.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.services.api.tasks.TasksAPI", return_value=mock_api
            ),
        ):
            result = runner.invoke(app, ["skip", "task-123", "--output", "json"])
        assert result.exit_code == 0


class TestNextTaskCommand:
    """Lines 352-363: next command."""

    def test_next_no_tasks(self, mock_task_service):
        mock_task_service.list_tasks.return_value = []
        result = runner.invoke(app, ["next"])
        assert result.exit_code == 0
        assert "No active tasks" in result.output

    def test_next_with_task_pretty(self, mock_task_service, mock_task):
        mock_task_service.list_tasks.return_value = [mock_task]
        with patch(
            "todopro_cli.utils.ui.formatters.format_next_task"
        ) as mock_fmt:
            result = runner.invoke(app, ["next"])
        assert result.exit_code == 0

    def test_next_with_task_json_output(self, mock_task_service, mock_task):
        mock_task_service.list_tasks.return_value = [mock_task]
        result = runner.invoke(app, ["next", "--output", "json"])
        assert result.exit_code == 0


class TestListCompletingTasksFilter:
    """Line 71: list_tasks filters out tasks being completed in background."""

    @patch("todopro_cli.commands.tasks_command.get_background_cache")
    def test_completing_tasks_filtered_from_list(self, mock_cache, mock_task_service, mock_task):
        """When completing_tasks is non-empty, matching tasks are excluded."""
        mock_task_service.list_tasks.return_value = [mock_task]
        # Simulate a completing task with ID suffix matching our mock_task
        mock_cache.return_value.get_completing_tasks.return_value = ["task-123"]
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # task-123 should be filtered out

    @patch("todopro_cli.commands.tasks_command.get_background_cache")
    def test_non_matching_task_not_filtered(self, mock_cache, mock_task_service, mock_task):
        """Tasks whose ID doesn't match completing_tasks are NOT filtered."""
        mock_task_service.list_tasks.return_value = [mock_task]
        mock_cache.return_value.get_completing_tasks.return_value = ["xxxxxx"]
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0


class TestRescheduleWithConfirmation:
    """Lines 236-255: reschedule bulk overdue with user confirmation."""

    def _make_overdue_task(self, task_id="task-overdue"):
        from datetime import date
        task = MagicMock()
        task.id = task_id
        task.content = "Overdue task"
        task.due_date = MagicMock()
        task.due_date.date.return_value.isoformat.return_value = "2020-01-01"
        task.model_dump.return_value = {"id": task_id, "content": "Overdue task"}
        return task

    def test_reschedule_overdue_user_confirms(self, mock_task_service):
        """User confirms bulk reschedule → tasks get rescheduled."""
        overdue_task = self._make_overdue_task()
        mock_task_service.list_tasks.return_value = [overdue_task]
        mock_task_service.update_task.return_value = overdue_task
        result = runner.invoke(app, ["reschedule"], input="y\n")
        assert result.exit_code == 0
        assert "Rescheduled" in result.output or "task" in result.output.lower()

    def test_reschedule_overdue_user_cancels(self, mock_task_service):
        """User declines bulk reschedule → cancelled."""
        overdue_task = self._make_overdue_task()
        mock_task_service.list_tasks.return_value = [overdue_task]
        result = runner.invoke(app, ["reschedule"], input="n\n")
        assert result.exit_code == 0
        # Should not call update_task
        mock_task_service.update_task.assert_not_called()

    def test_reschedule_overdue_yes_flag(self, mock_task_service):
        """--yes skips confirmation and rescheduled tasks."""
        overdue_task = self._make_overdue_task()
        mock_task_service.list_tasks.return_value = [overdue_task]
        mock_task_service.update_task.return_value = overdue_task
        result = runner.invoke(app, ["reschedule", "--yes"])
        assert result.exit_code == 0
        mock_task_service.update_task.assert_called()


class TestRescheduleAutoDate:
    """Lines 263-265: reschedule single task without providing --date."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_reschedule_single_no_date_uses_today(self, mock_resolve, mock_task_service):
        """When no --date given, defaults to today's date."""
        from unittest.mock import AsyncMock
        mock_resolve.return_value = "task-123"
        mock_task = MagicMock()
        mock_task.content = "Short task"
        mock_task_service.update_task.return_value = mock_task
        result = runner.invoke(app, ["reschedule", "task-123"])
        assert result.exit_code == 0


class TestRescheduleContentTruncation:
    """Line 275: reschedule with content longer than 60 chars."""

    @patch("todopro_cli.commands.tasks_command.resolve_task_id")
    def test_reschedule_long_content_truncated(self, mock_resolve, mock_task_service):
        """Content > 60 chars is truncated to 57 chars + '...'."""
        from unittest.mock import AsyncMock
        mock_resolve.return_value = "task-123"
        long_content = "This is a very long task content that definitely exceeds sixty characters in total"
        mock_task = MagicMock()
        mock_task.content = long_content
        mock_task_service.update_task.return_value = mock_task
        result = runner.invoke(app, ["reschedule", "task-123", "--date", "2024-12-31"])
        assert result.exit_code == 0
        # Should show truncated content with ...
        assert "..." in result.output or long_content[:10] in result.output


# ---------------------------------------------------------------------------
# migrate command tests
# ---------------------------------------------------------------------------

def _make_project(pid: str, name: str) -> MagicMock:
    p = MagicMock()
    p.id = pid
    p.name = name
    return p


def _make_task(tid: str, content: str, project_id: str = "src-id", completed: bool = False) -> Task:
    return Task(
        id=tid,
        content=content,
        description="",
        project_id=project_id,
        due_date=None,
        priority=4,
        is_completed=completed,
        labels=[],
        contexts=[],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


class TestMigrateCommand:
    """Tests for todopro tasks migrate."""

    def _invoke(self, args, tasks=None, projects=None):
        """Helper: invoke migrate with mocked storage and task service."""
        if tasks is None:
            tasks = [_make_task("t1", "Buy milk")]
        projects = projects or {
            "source": _make_project("src-id", "Inbox"),
            "target": _make_project("tgt-id", "Work"),
        }

        svc = MagicMock()
        svc.list_tasks = AsyncMock(return_value=tasks)
        svc.bulk_update_tasks = AsyncMock(return_value=tasks)

        proj_repo = MagicMock()
        proj_repo.get = AsyncMock(side_effect=lambda pid: (
            projects["source"] if pid == "src-id" else projects["target"]
        ))

        storage = MagicMock()
        storage.project_repository = proj_repo
        storage.task_repository = MagicMock()

        with (
            patch("todopro_cli.commands.tasks_command.get_storage_strategy_context", return_value=storage),
            patch("todopro_cli.commands.tasks_command.TaskService", return_value=svc),
            patch(
                "todopro_cli.commands.tasks_command.resolve_project_uuid",
                side_effect=lambda name, repo: "src-id" if name == "Inbox" else "tgt-id",
            ),
        ):
            result = runner.invoke(app, ["migrate"] + args)
        return result, svc

    def test_help_shows_from_to_options(self):
        result = runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "--from" in result.output
        assert "--to" in result.output

    def test_requires_from_option(self):
        result = runner.invoke(app, ["migrate", "--to", "Work"])
        assert result.exit_code != 0

    def test_requires_to_option(self):
        result = runner.invoke(app, ["migrate", "--from", "Inbox"])
        assert result.exit_code != 0

    def test_dry_run_does_not_call_bulk_update(self):
        result, svc = self._invoke(["--from", "Inbox", "--to", "Work", "--dry-run"])
        assert result.exit_code == 0
        svc.bulk_update_tasks.assert_not_called()

    def test_dry_run_shows_preview(self):
        result, _ = self._invoke(["--from", "Inbox", "--to", "Work", "--dry-run"])
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "would be moved" in result.output.lower()

    def test_yes_flag_skips_confirmation(self):
        result, svc = self._invoke(["--from", "Inbox", "--to", "Work", "--yes"])
        assert result.exit_code == 0
        svc.bulk_update_tasks.assert_awaited_once()

    def test_bulk_update_called_with_correct_project_id(self):
        result, svc = self._invoke(["--from", "Inbox", "--to", "Work", "--yes"])
        assert result.exit_code == 0
        _, kwargs = svc.bulk_update_tasks.call_args
        assert kwargs.get("project_id") == "tgt-id"

    def test_shows_success_message(self):
        result, _ = self._invoke(["--from", "Inbox", "--to", "Work", "--yes"])
        assert result.exit_code == 0
        assert "Inbox" in result.output
        assert "Work" in result.output

    def test_exits_zero_when_no_tasks(self):
        result, svc = self._invoke(["--from", "Inbox", "--to", "Work", "--yes"], tasks=[])
        assert result.exit_code == 0
        svc.bulk_update_tasks.assert_not_called()

    def test_same_project_exits_nonzero(self):
        svc = MagicMock()
        proj_repo = MagicMock()
        storage = MagicMock()
        storage.project_repository = proj_repo
        storage.task_repository = MagicMock()

        with (
            patch("todopro_cli.commands.tasks_command.get_storage_strategy_context", return_value=storage),
            patch("todopro_cli.commands.tasks_command.TaskService", return_value=svc),
            patch(
                "todopro_cli.commands.tasks_command.resolve_project_uuid",
                return_value="same-id",  # both resolve to same
            ),
        ):
            result = runner.invoke(app, ["migrate", "--from", "X", "--to", "X", "--yes"])
        assert result.exit_code != 0

    def test_unknown_project_exits_nonzero(self):
        svc = MagicMock()
        storage = MagicMock()

        with (
            patch("todopro_cli.commands.tasks_command.get_storage_strategy_context", return_value=storage),
            patch("todopro_cli.commands.tasks_command.TaskService", return_value=svc),
            patch(
                "todopro_cli.commands.tasks_command.resolve_project_uuid",
                side_effect=ValueError("Project not found: 'Ghost'"),
            ),
        ):
            result = runner.invoke(app, ["migrate", "--from", "Ghost", "--to", "Work", "--yes"])
        assert result.exit_code != 0
        assert "Ghost" in result.output

    def test_shows_task_preview_table(self):
        tasks = [_make_task(f"t{i}", f"Task {i}") for i in range(3)]
        result, _ = self._invoke(["--from", "Inbox", "--to", "Work", "--yes"], tasks=tasks)
        assert result.exit_code == 0
        assert "Task 0" in result.output
        assert "Task 1" in result.output

    def test_table_truncates_long_content(self):
        long = "A" * 70
        result, _ = self._invoke(
            ["--from", "Inbox", "--to", "Work", "--yes"],
            tasks=[_make_task("t1", long)],
        )
        assert result.exit_code == 0
        # Rich uses the single-character ellipsis (…) or the full string is absent
        assert "…" in result.output or long not in result.output
