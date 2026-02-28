"""Unit tests for new create_command (verb-first pattern)."""

# pylint: disable=redefined-outer-name

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.create_command import app
from todopro_cli.models import Label, Project, Task

runner = CliRunner()


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
def mock_project():
    """Create a mock project for testing."""
    return Project(
        id="proj-123",
        name="Test Project",
        color="#FF0000",
        is_favorite=False,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


class TestCreateCommandStructure:
    """Tests for overall create command structure."""

    def test_create_help(self):
        """Test that create command shows help correctly."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Create" in result.stdout
        assert "task" in result.stdout
        assert "project" in result.stdout
        assert "label" in result.stdout

    def test_create_task_help(self):
        """Test that create task subcommand has help."""
        result = runner.invoke(app, ["task", "--help"])

        assert result.exit_code == 0
        assert "Create a new task" in result.stdout

    def test_create_project_help(self):
        """Test that create project subcommand has help."""
        result = runner.invoke(app, ["project", "--help"])

        assert result.exit_code == 0
        assert "Create a new project" in result.stdout


class TestCreateTaskWithService:
    """Tests using get_task_service mock."""

    def _run(self, args, task=None):
        from datetime import datetime
        from unittest.mock import AsyncMock, MagicMock, patch

        from todopro_cli.models import Task
        if task is None:
            task = Task(
                id="task-new-1", content="New task", description="", project_id=None,
                due_date=None, priority=4, is_completed=False, labels=[], contexts=[],
                created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1),
            )
        svc = MagicMock()
        svc.add_task = AsyncMock(return_value=task)

        with patch("todopro_cli.commands.create_command.get_task_service", return_value=svc):
            return runner.invoke(app, ["task"] + args, catch_exceptions=False)

    def test_create_task_minimal(self):
        result = self._run(["New task"])
        assert result.exit_code == 0
        assert "Task created" in result.output

    def test_create_task_with_recurrence(self):
        """Line 48: if recur: branch."""
        result = self._run(["Daily standup", "--recur", "daily"])
        assert result.exit_code == 0
        assert "Recurrence" in result.output or "daily" in result.output

    def test_create_task_with_parent(self):
        """Line 77: if parent: branch."""
        result = self._run(["Subtask", "--parent", "parent-task-id"])
        assert result.exit_code == 0
        assert "Subtask" in result.output or "parent" in result.output.lower()

    def test_create_task_invalid_recurrence(self):
        """Invalid recur pattern → exit 1."""
        result = self._run(["Task", "--recur", "invalid-pattern"])
        assert result.exit_code == 1
        assert "Unknown recurrence" in result.output or "Error" in result.output

    def test_create_task_with_labels(self):
        result = self._run(["Labelled task", "--labels", "urgent,work"])
        assert result.exit_code == 0


class TestCreateProjectWithService:
    """Lines 118-122: create project json output."""

    def _run(self, args, project=None):
        from datetime import datetime
        from unittest.mock import AsyncMock, MagicMock, patch

        from todopro_cli.models import Project
        if project is None:
            project = Project(
                id="proj-new-1", name="New Project", color=None, is_favorite=False,
                created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1),
            )
        svc = MagicMock()
        svc.create_project = AsyncMock(return_value=project)

        with patch("todopro_cli.commands.create_command.get_project_service", return_value=svc):
            return runner.invoke(app, ["project"] + args, catch_exceptions=False)

    def test_create_project_pretty(self):
        result = self._run(["My Project"])
        assert result.exit_code == 0
        assert "New Project" in result.output or "created" in result.output.lower()

    def test_create_project_json_output(self):
        """Lines 118-122: json_opt branch."""
        result = self._run(["My Project", "--json"])
        assert result.exit_code == 0

    def test_create_project_with_color(self):
        result = self._run(["Colored Project", "--color", "#FF5733"])
        assert result.exit_code == 0

    def test_create_project_as_favorite(self):
        result = self._run(["Fav Project", "--favorite"])
        assert result.exit_code == 0


class TestCreateContextCommand:
    """Lines 135-140: create context command."""

    def test_create_context_success(self):
        """create context creates a new storage context."""
        from unittest.mock import MagicMock, patch

        mock_ctx_svc_class = MagicMock()
        mock_ctx_svc_instance = MagicMock()
        mock_ctx_svc_instance.create_context.return_value = {"name": "myctx", "backend_type": "sqlite"}
        mock_ctx_svc_class.return_value = mock_ctx_svc_instance

        with patch("todopro_cli.services.location_context_service.ContextService", mock_ctx_svc_class, create=True):
            result = runner.invoke(app, ["context", "myctx"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_create_context_with_backend(self):
        """create context with --backend option."""
        from unittest.mock import MagicMock, patch

        mock_ctx_svc_class = MagicMock()
        mock_ctx_svc_instance = MagicMock()
        mock_ctx_svc_instance.create_context.return_value = {"name": "remote-ctx", "backend_type": "rest"}
        mock_ctx_svc_class.return_value = mock_ctx_svc_instance

        with patch("todopro_cli.services.location_context_service.ContextService", mock_ctx_svc_class, create=True):
            result = runner.invoke(app, ["context", "remote-ctx", "--backend", "rest"], catch_exceptions=False)
        assert result.exit_code == 0


class TestCreateLabelCommand:
    """Lines 118-122: create label command body."""

    def _run(self, args, label=None):
        from datetime import datetime
        from unittest.mock import AsyncMock, MagicMock, patch
        from todopro_cli.models import Label
        if label is None:
            label = Label(
                id="label-new-1", name="urgent", color="#FF0000",
                created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1),
            )
        svc = MagicMock()
        svc.create_label = AsyncMock(return_value=label)
        with patch("todopro_cli.commands.create_command.get_label_service", return_value=svc):
            return runner.invoke(app, ["label"] + args, catch_exceptions=False)

    def test_create_label_minimal(self):
        """create label name → success."""
        result = self._run(["urgent"])
        assert result.exit_code == 0
        assert "Label created" in result.output

    def test_create_label_with_color(self):
        """create label name --color → success."""
        result = self._run(["bug", "--color", "#FF0000"])
        assert result.exit_code == 0

    def test_create_label_help(self):
        result = runner.invoke(app, ["label", "--help"])
        assert result.exit_code == 0
        assert "Create a new label" in result.stdout
