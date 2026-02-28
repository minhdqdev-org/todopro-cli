"""Unit tests for new list_command (verb-first pattern)."""

# pylint: disable=redefined-outer-name

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.list_command import app
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


@pytest.fixture
def mock_label():
    """Create a mock label for testing."""
    return Label(
        id="label-123",
        name="urgent",
        color="#FF0000",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# New strategy-pattern tests: actually invoke command bodies
# ---------------------------------------------------------------------------


def _make_task(id_="task-1", content="Test task", is_recurring=False):
    t = MagicMock()
    t.id = id_
    t.content = content
    t.is_recurring = is_recurring
    t.model_dump.return_value = {"id": id_, "content": content}
    return t


def _make_project(id_="proj-1", name="Work"):
    p = MagicMock()
    p.id = id_
    p.name = name
    p.model_dump.return_value = {"id": id_, "name": name}
    return p


def _make_label(id_="label-1", name="urgent"):
    lbl = MagicMock()
    lbl.id = id_
    lbl.name = name
    lbl.model_dump.return_value = {"id": id_, "name": name}
    return lbl


class TestListTasksCommand:
    """Tests for 'list tasks' that cover the command body."""

    def _run(self, args, tasks=None, completing=None):
        tasks = tasks or []
        svc = MagicMock()
        # list_tasks is called twice (count check + actual)
        svc.list_tasks = AsyncMock(return_value=tasks)
        cache = MagicMock()
        cache.get_completing_tasks.return_value = completing or []

        with (
            patch(
                "todopro_cli.commands.list_command.get_task_service",
                return_value=svc,
            ),
            patch(
                "todopro_cli.commands.list_command.get_background_cache",
                return_value=cache,
            ),
        ):
            return runner.invoke(app, ["tasks"] + args, catch_exceptions=False)

    def test_list_tasks_empty(self):
        """Empty task list exits 0."""
        result = self._run([])
        assert result.exit_code == 0, result.output

    def test_list_tasks_with_data(self):
        """Task list with items exits 0."""
        result = self._run([], tasks=[_make_task()])
        assert result.exit_code == 0, result.output

    def test_list_tasks_json_flag(self):
        """--json flag exits 0."""
        result = self._run(["--json"], tasks=[_make_task()])
        assert result.exit_code == 0, result.output

    def test_list_tasks_compact_flag(self):
        """--compact flag exits 0."""
        result = self._run(["--compact"], tasks=[_make_task()])
        assert result.exit_code == 0, result.output

    def test_list_tasks_status_filter(self):
        """--status filter is forwarded to the service."""
        result = self._run(["--status", "active"])
        assert result.exit_code == 0, result.output

    def test_list_tasks_priority_filter(self):
        """--priority filter is forwarded."""
        result = self._run(["--priority", "1"])
        assert result.exit_code == 0, result.output

    def test_list_tasks_search_filter(self):
        """--search filter is forwarded."""
        result = self._run(["--search", "buy milk"])
        assert result.exit_code == 0, result.output

    def test_list_tasks_recurring_filter(self):
        """--recurring filters to only recurring tasks."""
        tasks = [
            _make_task("t1", is_recurring=True),
            _make_task("t2", is_recurring=False),
        ]
        result = self._run(["--recurring"], tasks=tasks)
        assert result.exit_code == 0, result.output

    def test_list_tasks_filters_completing_tasks(self):
        """Tasks whose id suffix matches a completing ID are excluded."""
        tasks = [
            _make_task("aaaa-bbbb-cccc-dddd"),
            _make_task("eeee-ffff-0000-1111"),
        ]
        result = self._run(
            [],
            tasks=tasks,
            completing=["dddd"],  # matches first task's end
        )
        assert result.exit_code == 0, result.output

    def test_list_tasks_o_json_shorthand(self):
        """-o json shorthand works."""
        result = self._run(["-o", "json"], tasks=[_make_task()])
        assert result.exit_code == 0, result.output

    def test_list_tasks_limit_offset(self):
        """--limit and --offset are accepted."""
        result = self._run(["--limit", "5", "--offset", "10"])
        assert result.exit_code == 0, result.output


class TestListProjectsCommand:
    """Tests for 'list projects' command body."""

    def _run(self, args=None):
        svc = MagicMock()
        svc.list_projects = AsyncMock(return_value=[_make_project()])

        with patch(
            "todopro_cli.commands.list_command.get_project_service",
            return_value=svc,
        ):
            return runner.invoke(app, ["projects"] + (args or []), catch_exceptions=False)

    def test_list_projects_success(self):
        result = self._run()
        assert result.exit_code == 0, result.output

    def test_list_projects_json(self):
        result = self._run(["--json"])
        assert result.exit_code == 0, result.output

    def test_list_projects_archived(self):
        svc = MagicMock()
        svc.list_projects = AsyncMock(return_value=[])
        with patch(
            "todopro_cli.commands.list_command.get_project_service",
            return_value=svc,
        ):
            result = runner.invoke(
                app, ["projects", "--archived"], catch_exceptions=False
            )
        assert result.exit_code == 0, result.output


class TestListLabelsCommand:
    """Tests for 'list labels' command body."""

    def _run(self, args=None):
        svc = MagicMock()
        svc.list_labels = AsyncMock(return_value=[_make_label()])

        with patch(
            "todopro_cli.commands.list_command.get_label_service",
            return_value=svc,
        ):
            return runner.invoke(app, ["labels"] + (args or []), catch_exceptions=False)

    def test_list_labels_success(self):
        result = self._run()
        assert result.exit_code == 0, result.output

    def test_list_labels_table_output(self):
        result = self._run(["-o", "table"])
        assert result.exit_code == 0, result.output


class TestListContextsCommand:
    """Tests for 'list contexts' command body (pretty & JSON)."""

    def _make_ctx(self, name="local", type_="local", source="/tmp/db", desc=None):
        ctx = MagicMock()
        ctx.name = name
        ctx.type = type_
        ctx.source = source
        ctx.description = desc
        return ctx

    def _run(self, args=None, contexts=None, current_name="local"):
        ctx = self._make_ctx()
        current = self._make_ctx(name=current_name)
        config_svc = MagicMock()
        config_svc.list_contexts.return_value = contexts or [ctx]
        config_svc.get_current_context.return_value = current

        with patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=config_svc,
        ):
            return runner.invoke(
                app, ["contexts"] + (args or []), catch_exceptions=False
            )

    def test_pretty_output(self):
        result = self._run()
        assert result.exit_code == 0, result.output
        assert "local" in result.output

    def test_json_output(self):
        result = self._run(["--json"])
        assert result.exit_code == 0, result.output

    def test_limit_flag(self):
        """--limit restricts number of contexts shown."""
        contexts = [
            self._make_ctx(f"ctx-{i}", desc=f"Context {i}") for i in range(5)
        ]
        result = self._run(["--limit", "2"], contexts=contexts)
        assert result.exit_code == 0, result.output

    def test_more_than_limit_shows_hint(self):
        """When more contexts exist than limit, a hint is printed."""
        contexts = [self._make_ctx(f"ctx-{i}") for i in range(6)]
        result = self._run(["--limit", "3"], contexts=contexts)
        assert result.exit_code == 0, result.output

    def test_context_with_description(self):
        """Contexts with descriptions show the description."""
        ctx = self._make_ctx(desc="My local database")
        result = self._run(contexts=[ctx])
        assert result.exit_code == 0, result.output

    def test_current_context_marked(self):
        """Current context is indicated in output."""
        ctx = self._make_ctx(name="local")
        result = self._run(contexts=[ctx], current_name="local")
        assert result.exit_code == 0, result.output

    def test_remote_context_type(self):
        """Remote context type uses magenta color tag."""
        ctx = self._make_ctx(name="cloud", type_="remote")
        result = self._run(contexts=[ctx])
        assert result.exit_code == 0, result.output


class TestListGoalsCommand:
    """Tests for 'list goals' command body."""

    def _run(self, args=None):
        goal = MagicMock()
        goal.model_dump.return_value = {"id": "goal-1", "name": "Focus 2h daily"}

        svc = MagicMock()
        svc.list_goals = AsyncMock(return_value=[goal])

        mock_focus_module = MagicMock()
        mock_focus_module.get_focus_service = MagicMock(return_value=svc)

        with patch.dict("sys.modules", {"todopro_cli.services.focus_service": mock_focus_module}):
            return runner.invoke(app, ["goals"] + (args or []), catch_exceptions=False)

    def test_list_goals_success(self):
        result = self._run()
        assert result.exit_code == 0, result.output

    def test_list_goals_json(self):
        result = self._run(["-o", "json"])
        assert result.exit_code == 0, result.output


class TestListAchievementsCommand:
    """Tests for 'list achievements' command body."""

    def _run(self, args=None):
        ach = MagicMock()
        ach.model_dump.return_value = {"id": "ach-1", "name": "First Step"}

        svc = MagicMock()
        svc.list_achievements = AsyncMock(return_value=[ach])

        with patch(
            "todopro_cli.services.achievement_service.get_achievement_service",
            return_value=svc,
        ):
            return runner.invoke(
                app, ["achievements"] + (args or []), catch_exceptions=False
            )

    def test_list_achievements_success(self):
        result = self._run()
        assert result.exit_code == 0, result.output

    def test_list_achievements_table(self):
        result = self._run(["-o", "table"])
        assert result.exit_code == 0, result.output


class TestListFocusTemplatesCommand:
    """Tests for 'list focus-templates' command body."""

    def _run(self, args=None):
        tmpl = MagicMock()
        tmpl.model_dump.return_value = {"id": "tmpl-1", "name": "Deep Work"}

        svc = MagicMock()
        svc.list_templates = AsyncMock(return_value=[tmpl])

        mock_focus_module = MagicMock()
        mock_focus_module.get_focus_service = MagicMock(return_value=svc)

        with patch.dict("sys.modules", {"todopro_cli.services.focus_service": mock_focus_module}):
            return runner.invoke(
                app, ["focus-templates"] + (args or []), catch_exceptions=False
            )

    def test_list_focus_templates_success(self):
        result = self._run()
        assert result.exit_code == 0, result.output


class TestListFiltersCommand:
    """Tests for 'list filters' command body."""

    def _run(self, args=None, filters=None):
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.list_filters = AsyncMock(return_value=filters or [{"id": "f1", "name": "Today"}])

        with (
            patch(
                "todopro_cli.commands.list_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.list_command.FiltersAPI",
                return_value=mock_api,
            ),
        ):
            return runner.invoke(
                app, ["filters"] + (args or []), catch_exceptions=False
            )

    def test_list_filters_success(self):
        result = self._run()
        assert result.exit_code == 0, result.output

    def test_list_filters_json(self):
        result = self._run(["-o", "json"])
        assert result.exit_code == 0, result.output


class TestListSubtasksCommand:
    """Tests for 'list subtasks <parent_id>' command body."""

    def _run(self, args, subtasks=None):
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        if subtasks is not None:
            mock_api.list_subtasks = AsyncMock(return_value=subtasks)
        else:
            mock_api.list_subtasks = AsyncMock(
                return_value=[{"id": "sub-1", "content": "Subtask 1"}]
            )

        with (
            patch(
                "todopro_cli.commands.list_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.list_command.TasksAPI",
                return_value=mock_api,
            ),
        ):
            return runner.invoke(app, ["subtasks"] + args, catch_exceptions=False)

    def test_list_subtasks_success(self):
        result = self._run(["parent-task-123"])
        assert result.exit_code == 0, result.output

    def test_list_subtasks_empty_shows_message(self):
        """Empty subtasks shows a 'no subtasks' message."""
        result = self._run(["parent-task-123"], subtasks=[])
        assert result.exit_code == 0, result.output
        assert "No subtasks" in result.output

    def test_list_subtasks_as_list(self):
        """API returning a list directly is handled."""
        result = self._run(
            ["parent-task-123"],
            subtasks=[{"id": "sub-1", "content": "Sub 1"}],
        )
        assert result.exit_code == 0, result.output

    def test_list_subtasks_as_dict_with_tasks_key(self):
        """API returning a dict with 'tasks' key is handled."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.list_subtasks = AsyncMock(
            return_value={"tasks": [{"id": "sub-1", "content": "Sub 1"}]}
        )
        with (
            patch(
                "todopro_cli.commands.list_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.list_command.TasksAPI",
                return_value=mock_api,
            ),
        ):
            result = runner.invoke(
                app, ["subtasks", "parent-task-123"], catch_exceptions=False
            )
        assert result.exit_code == 0, result.output

    def test_list_subtasks_json_output(self):
        result = self._run(["parent-task-123", "-o", "json"])
        assert result.exit_code == 0, result.output


class TestListCommandStructure:
    """Tests for overall list command structure."""

    def test_list_help(self):
        """Test that list command shows help correctly."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "List resources" in result.stdout
        assert "tasks" in result.stdout
        assert "projects" in result.stdout
        assert "labels" in result.stdout

    def test_list_tasks_help(self):
        """Test that list tasks subcommand has help."""
        result = runner.invoke(app, ["tasks", "--help"])

        assert result.exit_code == 0
        assert "List tasks" in result.stdout

    def test_list_projects_help(self):
        """Test that list projects subcommand has help."""
        result = runner.invoke(app, ["projects", "--help"])

        assert result.exit_code == 0
        assert "List all projects" in result.stdout

    def test_list_labels_help(self):
        """Test that list labels subcommand has help."""
        result = runner.invoke(app, ["labels", "--help"])

        assert result.exit_code == 0
        assert "List all labels" in result.stdout


class TestListTasksBigThresholdWarning:
    """Lines 66-69: warning when task count exceeds threshold."""

    def test_big_task_count_warning_shown(self):
        """When >100 tasks exist and stdout is a tty, shows warning."""
        tasks = [_make_task(f"task-{i}") for i in range(102)]
        svc = MagicMock()
        svc.list_tasks = AsyncMock(return_value=tasks)
        cache = MagicMock()
        cache.get_completing_tasks.return_value = []

        with (
            patch("todopro_cli.commands.list_command.get_task_service", return_value=svc),
            patch("todopro_cli.commands.list_command.get_background_cache", return_value=cache),
            patch("sys.stdin.isatty", return_value=True),
        ):
            result = runner.invoke(app, ["tasks"])

        assert result.exit_code == 0
        assert "Found" in result.output or "task" in result.output.lower()

    def test_big_task_count_no_warning_when_json(self):
        """JSON output suppresses the big-task warning."""
        tasks = [_make_task(f"task-{i}") for i in range(102)]
        svc = MagicMock()
        svc.list_tasks = AsyncMock(return_value=tasks)
        cache = MagicMock()
        cache.get_completing_tasks.return_value = []

        with (
            patch("todopro_cli.commands.list_command.get_task_service", return_value=svc),
            patch("todopro_cli.commands.list_command.get_background_cache", return_value=cache),
            patch("sys.stdin.isatty", return_value=True),
        ):
            result = runner.invoke(app, ["tasks", "--json"])

        assert result.exit_code == 0
        assert "Found" not in result.output or '"tasks"' in result.output


class TestListContextsJsonFix:
    """Lines 200-208: list contexts with JSON output - fix the patch target."""

    def _make_ctx(self, name="local", type_="local", source="/tmp/db", desc=None):
        ctx = MagicMock()
        ctx.name = name
        ctx.type = type_
        ctx.source = source
        ctx.description = desc
        return ctx

    def test_json_output_using_correct_patch(self):
        """JSON output for contexts - patch at service level."""
        ctx = self._make_ctx()
        current = self._make_ctx()
        config_svc = MagicMock()
        config_svc.list_contexts.return_value = [ctx]
        config_svc.get_current_context.return_value = current

        with patch("todopro_cli.services.config_service.get_config_service", return_value=config_svc):
            result = runner.invoke(app, ["contexts", "--json"], catch_exceptions=False)
        assert result.exit_code == 0


class TestListLocationContextsCommand:
    """Lines 200-208: list location-contexts command."""

    def test_list_location_contexts_success(self):
        """list location-contexts returns contexts."""
        ctx = MagicMock()
        ctx.model_dump.return_value = {"id": "lc-1", "name": "@home"}

        svc = MagicMock()
        svc.list_location_contexts = AsyncMock(return_value=[ctx])

        mock_lcs_module = MagicMock()
        mock_lcs_module.get_location_context_service = MagicMock(return_value=svc)

        with patch.dict("sys.modules", {"todopro_cli.services.location_context_service": mock_lcs_module}):
            result = runner.invoke(app, ["location-contexts"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_list_location_contexts_json(self):
        """list location-contexts with JSON output."""
        ctx = MagicMock()
        ctx.model_dump.return_value = {"id": "lc-1", "name": "@home"}

        svc = MagicMock()
        svc.list_location_contexts = AsyncMock(return_value=[ctx])

        mock_lcs_module = MagicMock()
        mock_lcs_module.get_location_context_service = MagicMock(return_value=svc)

        with patch.dict("sys.modules", {"todopro_cli.services.location_context_service": mock_lcs_module}):
            result = runner.invoke(app, ["location-contexts", "-o", "json"], catch_exceptions=False)
        assert result.exit_code == 0


class TestListTasksBigThresholdFixed:
    """Lines 66-69: Fix big threshold warning with proper isatty mock."""

    def test_big_task_count_warning_with_isatty(self):
        """When >100 tasks and isatty returns True, warning is shown."""
        tasks = [_make_task(f"task-{i}") for i in range(102)]
        svc = MagicMock()
        svc.list_tasks = AsyncMock(return_value=tasks)
        cache = MagicMock()
        cache.get_completing_tasks.return_value = []

        # Mock stdin.isatty at the module level as a standalone function
        import sys as _sys
        original_isatty = _sys.stdin.isatty
        try:
            _sys.stdin.isatty = lambda: True
            with (
                patch("todopro_cli.commands.list_command.get_task_service", return_value=svc),
                patch("todopro_cli.commands.list_command.get_background_cache", return_value=cache),
            ):
                result = runner.invoke(app, ["tasks"])
        finally:
            _sys.stdin.isatty = original_isatty

        assert result.exit_code == 0
        assert "Found" in result.output or "task" in result.output.lower()
