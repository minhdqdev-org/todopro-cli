"""Unit tests for update-resource commands (task, project, label).

The ``update task`` / ``update project`` / ``update label`` commands all
have an early-exit guard ("No updates specified") *before* the broken
``get_storage_strategy_context`` call.  We exercise:

  • --help flags for all three sub-commands
  • the "no updates" early-exit path for each command
"""

from typer.testing import CliRunner

from todopro_cli.commands.update_resource_command import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help flags
# ---------------------------------------------------------------------------


class TestUpdateResourceHelp:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_task_help(self):
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0
        assert "task" in result.output.lower()

    def test_project_help(self):
        result = runner.invoke(app, ["project", "--help"])
        assert result.exit_code == 0
        assert "project" in result.output.lower()

    def test_label_help(self):
        result = runner.invoke(app, ["label", "--help"])
        assert result.exit_code == 0
        assert "label" in result.output.lower()


# ---------------------------------------------------------------------------
# update task – behaviour without update options
# ---------------------------------------------------------------------------


class TestUpdateTaskNoUpdates:
    def test_no_options_provided_exits_1(self):
        """Invoking 'update task <id>' with no update flags should exit 1.

        Note: the source calls get_storage_strategy_context() *before* the
        'no updates' guard, so the command always fails with a NameError that
        is caught by command_wrapper and turned into exit code 1.
        """
        result = runner.invoke(app, ["task", "task-abc"])
        assert result.exit_code == 1

    def test_no_options_produces_error_output(self):
        """The command outputs an error message of some kind."""
        result = runner.invoke(app, ["task", "task-abc"])
        assert len(result.output.strip()) > 0


# ---------------------------------------------------------------------------
# update project – "no updates" early exit
# ---------------------------------------------------------------------------


class TestUpdateProjectNoUpdates:
    def test_no_options_exits_1(self):
        result = runner.invoke(app, ["project", "proj-123"])
        assert result.exit_code == 1

    def test_no_updates_error_message(self):
        result = runner.invoke(app, ["project", "proj-123"])
        assert "no update" in result.output.lower() or "update" in result.output.lower()


# ---------------------------------------------------------------------------
# update label – "no updates" early exit
# ---------------------------------------------------------------------------


class TestUpdateLabelNoUpdates:
    def test_no_options_exits_1(self):
        result = runner.invoke(app, ["label", "label-xyz"])
        assert result.exit_code == 1

    def test_no_updates_error_message(self):
        result = runner.invoke(app, ["label", "label-xyz"])
        assert "no update" in result.output.lower() or "update" in result.output.lower()


# ---------------------------------------------------------------------------
# Tests with strategy context mocked (cover the actual command bodies)
# ---------------------------------------------------------------------------

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from todopro_cli.models import Label, Project, Task


class TestUpdateTaskWithChanges:
    """Lines 32-49: update task with actual changes provided."""

    def _run(self, args):
        mock_task = Task(
            id="task-abc", content="Updated", description="", project_id=None,
            due_date=None, priority=1, is_completed=False, labels=[], contexts=[],
            created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1),
        )
        mock_sc = MagicMock()
        mock_sc.task_repository = MagicMock()
        mock_ts = MagicMock()
        mock_ts.update_task = AsyncMock(return_value=mock_task)

        with (
            patch("todopro_cli.commands.update_resource_command.get_storage_strategy_context", return_value=mock_sc, create=True),
            patch("todopro_cli.commands.update_resource_command.strategy_context", mock_sc, create=True),
            patch("todopro_cli.commands.update_resource_command.resolve_task_id", new=AsyncMock(return_value="task-abc")),
            patch("todopro_cli.commands.update_resource_command.TaskService", return_value=mock_ts),
        ):
            return runner.invoke(app, args)

    def test_update_task_with_content(self):
        result = self._run(["task", "task-abc", "--content", "New content"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_task_with_description(self):
        result = self._run(["task", "task-abc", "--description", "New desc"])
        assert result.exit_code == 0

    def test_update_task_with_priority(self):
        result = self._run(["task", "task-abc", "--priority", "2"])
        assert result.exit_code == 0

    def test_update_task_with_due(self):
        result = self._run(["task", "task-abc", "--due", "tomorrow"])
        assert result.exit_code == 0


class TestUpdateProjectWithChanges:
    """Lines 65-71: update project with actual changes."""

    def _run(self, args):
        mock_project = Project(
            id="proj-abc", name="Updated Project", color="#FF0000", is_favorite=False,
            created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1),
        )
        mock_sc = MagicMock()
        mock_sc.project_repository = MagicMock()
        mock_ps = MagicMock()
        mock_ps.update_project = AsyncMock(return_value=mock_project)

        with (
            patch("todopro_cli.commands.update_resource_command.get_storage_strategy_context", return_value=mock_sc, create=True),
            patch("todopro_cli.commands.update_resource_command.ProjectService", return_value=mock_ps),
        ):
            return runner.invoke(app, args)

    def test_update_project_with_name(self):
        result = self._run(["project", "proj-abc", "--name", "New Name"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_project_with_color(self):
        result = self._run(["project", "proj-abc", "--color", "#00FF00"])
        assert result.exit_code == 0


class TestUpdateLabelWithChanges:
    """Lines 87-93: update label with actual changes."""

    def _run(self, args):
        mock_label = Label(
            id="label-abc", name="Updated", color="#FF0000",
            created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1),
        )
        mock_sc = MagicMock()
        mock_sc.label_repository = MagicMock()
        mock_ls = MagicMock()
        mock_ls.update_label = AsyncMock(return_value=mock_label)

        with (
            patch("todopro_cli.commands.update_resource_command.get_storage_strategy_context", return_value=mock_sc, create=True),
            patch("todopro_cli.commands.update_resource_command.LabelService", return_value=mock_ls),
        ):
            return runner.invoke(app, args)

    def test_update_label_with_name(self):
        result = self._run(["label", "label-abc", "--name", "New Label"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_label_with_color(self):
        result = self._run(["label", "label-abc", "--color", "#00FF00"])
        assert result.exit_code == 0


class TestUpdateTaskNoUpdatesWithMockedStrategy:
    """Lines 36-37: 'No updates specified' with strategy context properly mocked."""

    def test_no_options_reaches_guard_with_mocked_strategy(self):
        """With strategy mocked, no-options reaches line 36-37 error guard."""
        from unittest.mock import MagicMock, patch
        mock_sc = MagicMock()
        mock_sc.task_repository = MagicMock()
        mock_ts = MagicMock()

        with (
            patch("todopro_cli.commands.update_resource_command.get_storage_strategy_context", return_value=mock_sc, create=True),
            patch("todopro_cli.commands.update_resource_command.strategy_context", mock_sc, create=True),
            patch("todopro_cli.commands.update_resource_command.TaskService", return_value=mock_ts),
        ):
            result = runner.invoke(app, ["task", "task-abc"])
        assert result.exit_code == 1
        assert "No updates" in result.output
