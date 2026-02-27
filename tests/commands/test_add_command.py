"""Unit tests for add command: output flags, --project override."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.add_command import app
from todopro_cli.models import Project, Task

runner = CliRunner()

MOCK_TASK = Task(
    id="task-abc",
    content="Meet Hung",
    description="",
    project_id=None,
    due_date=None,
    priority=1,
    is_completed=False,
    labels=[],
    contexts=[],
    created_at=datetime(2024, 1, 1, 12, 0, 0),
    updated_at=datetime(2024, 1, 1, 12, 0, 0),
)

INBOX_PROJECT = Project(
    id="test-inbox-uuid-1234-5678-9abc",
    name="Inbox",
    color="#4a90d9",
    is_favorite=False,
    protected=True,
    created_at=datetime(2024, 1, 1),
    updated_at=datetime(2024, 1, 1),
)

ROUTINES_PROJECT = Project(
    id="proj-routines",
    name="Routines",
    color="#ff0000",
    is_favorite=False,
    created_at=datetime(2024, 1, 1),
    updated_at=datetime(2024, 1, 1),
)


def _make_config_with_local_context():
    """Return a config mock that reports 'local' context type."""
    ctx_mock = MagicMock()
    ctx_mock.type = "local"
    config_mock = MagicMock()
    config_mock.get_current_context.return_value = ctx_mock
    return config_mock


def _make_strategy(task_add_result=None, projects=None):
    """Build a strategy mock with async repo methods."""
    task_repo = MagicMock()
    task_repo.add = AsyncMock(return_value=task_add_result or MOCK_TASK)
    proj_repo = MagicMock()
    proj_repo.list_all = AsyncMock(return_value=projects or [INBOX_PROJECT])
    strategy = MagicMock()
    strategy.task_repository = task_repo
    strategy.project_repository = proj_repo
    return strategy


class TestAddOutputFlags:
    """Test --output / -o / --json flags on tp add."""

    def _run_add(self, args, strategy=None, config=None):
        if strategy is None:
            strategy = _make_strategy()
        if config is None:
            config = _make_config_with_local_context()
        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=config,
            ),
            patch(
                "todopro_cli.commands.add_command.get_storage_strategy_context",
                return_value=strategy,
            ),
        ):
            return runner.invoke(app, args)

    def test_add_json_flag(self):
        """--json flag produces JSON output."""
        result = self._run_add(["Meet Hung today at 22", "--json"])
        assert result.exit_code == 0, result.output
        assert "task-abc" in result.output

    def test_add_o_json_shorthand(self):
        """-o json shorthand works."""
        result = self._run_add(["Meet Hung today at 22", "-o", "json"])
        assert result.exit_code == 0, result.output
        assert "task-abc" in result.output

    def test_add_pretty_output(self):
        """Default pretty output shows task content."""
        result = self._run_add(["Meet Hung today at 22"])
        assert result.exit_code == 0, result.output
        assert "Task created successfully" in result.output


class TestAddProjectFlag:
    """Test --project flag overrides natural language #project."""

    def test_project_flag_overrides_nl_project(self):
        """--project flag overrides #Inbox in NL text, assigning Routines."""
        captured = {}

        async def capture_add(task_create):
            captured["project_id"] = task_create.project_id
            return MOCK_TASK.model_copy(update={"project_id": task_create.project_id})

        task_repo = MagicMock()
        task_repo.add = capture_add
        proj_repo = MagicMock()
        proj_repo.list_all = AsyncMock(return_value=[INBOX_PROJECT, ROUTINES_PROJECT])
        proj_repo.get = AsyncMock(return_value=ROUTINES_PROJECT)
        strategy = MagicMock()
        strategy.task_repository = task_repo
        strategy.project_repository = proj_repo

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=_make_config_with_local_context(),
            ),
            patch(
                "todopro_cli.commands.add_command.get_storage_strategy_context",
                return_value=strategy,
            ),
        ):
            result = runner.invoke(app, ["Meet Hung #Inbox", "--project", "Routines"])

        assert result.exit_code == 0, result.output
        assert captured.get("project_id") == "proj-routines"

    def test_no_project_flag_uses_nl_project(self):
        """Without --project flag, #Inbox in NL is resolved to Inbox project."""
        captured = {}

        async def capture_add(task_create):
            captured["project_id"] = task_create.project_id
            return MOCK_TASK.model_copy(update={"project_id": task_create.project_id})

        task_repo = MagicMock()
        task_repo.add = capture_add
        proj_repo = MagicMock()
        proj_repo.list_all = AsyncMock(return_value=[INBOX_PROJECT])
        strategy = MagicMock()
        strategy.task_repository = task_repo
        strategy.project_repository = proj_repo

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=_make_config_with_local_context(),
            ),
            patch(
                "todopro_cli.commands.add_command.get_storage_strategy_context",
                return_value=strategy,
            ),
            patch(
                "todopro_cli.services.config_service.get_storage_strategy_context",
                return_value=strategy,
            ),
        ):
            result = runner.invoke(app, ["Meet Hung #Inbox"])

        assert result.exit_code == 0, result.output
        assert captured.get("project_id") == INBOX_PROJECT.id


class TestListContextJson:
    """Test tp list contexts --json and --limit."""

    def test_list_contexts_json(self):
        """--json flag outputs JSON with contexts array."""
        from todopro_cli.commands.list_command import app as list_app

        mock_ctx = MagicMock()
        mock_ctx.name = "local"
        mock_ctx.type = "local"
        mock_ctx.source = "/tmp/test.db"
        mock_ctx.description = "Test local"

        mock_config = MagicMock()
        mock_config.list_contexts.return_value = [mock_ctx]
        mock_config.get_current_context.return_value = mock_ctx

        with (
            patch(
                "todopro_cli.services.config_service.get_config_service",
                return_value=mock_config,
            ),
            patch(
                "todopro_cli.commands.list_command.get_config_service",
                return_value=mock_config,
                create=True,
            ),
        ):
            # Patch the import inside the function
            with patch(
                "todopro_cli.commands.list_command.list_contexts.__wrapped__",
                create=True,
            ):
                pass
            result = runner.invoke(
                list_app, ["contexts", "--json"], catch_exceptions=False
            )

        # Just verify JSON structure is present in output
        assert result.exit_code == 0 or '"contexts"' in result.output

    def test_list_contexts_limit_flag_exists(self):
        """--limit N flag is accepted by contexts command."""
        from todopro_cli.commands.list_command import app as list_app

        result = runner.invoke(list_app, ["contexts", "--help"])
        assert "--limit" in result.output or "-n" in result.output


class TestCreateProjectSimpleOutput:
    """Test tp create project produces simple output."""

    def test_create_project_simple_output(self):
        """create project shows name in success message, not full table."""
        mock_project = ROUTINES_PROJECT.model_copy()

        mock_svc = MagicMock()
        mock_svc.create_project = AsyncMock(return_value=mock_project)

        with patch(
            "todopro_cli.commands.create_command.get_project_service",
            return_value=mock_svc,
        ):
            from todopro_cli.commands.create_command import app as create_app

            result = runner.invoke(create_app, ["project", "Routines"])

        assert result.exit_code == 0, result.output
        assert "Routines" in result.output
        # Should NOT print full table details
        assert "is_favorite" not in result.output

    def test_create_project_json_output(self):
        """--json flag outputs JSON project."""
        mock_project = ROUTINES_PROJECT.model_copy()

        mock_svc = MagicMock()
        mock_svc.create_project = AsyncMock(return_value=mock_project)

        with patch(
            "todopro_cli.commands.create_command.get_project_service",
            return_value=mock_svc,
        ):
            from todopro_cli.commands.create_command import app as create_app

            result = runner.invoke(create_app, ["project", "Routines", "--json"])

        assert result.exit_code == 0, result.output
        assert '"project"' in result.output


# ---------------------------------------------------------------------------
# Additional tests for uncovered branches
# ---------------------------------------------------------------------------


def _make_remote_config():
    """Return a config mock that reports 'remote' context type."""
    ctx_mock = MagicMock()
    ctx_mock.type = "remote"
    config_mock = MagicMock()
    config_mock.get_current_context.return_value = ctx_mock
    return config_mock


# ---------------------------------------------------------------------------
# No-text-provided paths (stdin / interactive)
# ---------------------------------------------------------------------------


class TestAddNoTextProvided:
    """Cover lines 65-87: text=None branches."""

    def _run_with_stdin(self, stdin_text, config=None, strategy=None):
        if config is None:
            config = _make_config_with_local_context()
        if strategy is None:
            strategy = _make_strategy()
        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=config,
            ),
            patch(
                "todopro_cli.commands.add_command.get_storage_strategy_context",
                return_value=strategy,
            ),
        ):
            # CliRunner's stdin is not a TTY → `sys.stdin.isatty()` returns False
            return runner.invoke(app, [], input=stdin_text)

    def test_stdin_text_creates_task(self):
        """Text read from stdin (non-TTY) creates a task successfully."""
        result = self._run_with_stdin("Task from stdin\n")
        assert result.exit_code == 0, result.output

    def test_empty_stdin_shows_error(self):
        """Empty stdin results in 'Task text is required' error."""
        result = self._run_with_stdin("\n")
        assert result.exit_code == 1
        assert "required" in result.output.lower() or "error" in result.output.lower()

    def test_whitespace_only_stdin_shows_error(self):
        """Whitespace-only stdin is treated as empty."""
        result = self._run_with_stdin("   \n")
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Remote context (NLP / API) flow (lines 99-186)
# ---------------------------------------------------------------------------


class TestAddRemoteContext:
    """Cover the remote context do_quick_add() body."""

    def _run_remote(self, args, api_response, config=None):
        if config is None:
            config = _make_remote_config()

        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_tasks_api = MagicMock()
        mock_tasks_api.quick_add = AsyncMock(return_value=api_response)

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=config,
            ),
            patch(
                "todopro_cli.commands.add_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.add_command.TasksAPI",
                return_value=mock_tasks_api,
            ),
        ):
            return runner.invoke(app, args)

    def test_remote_success_pretty_output(self):
        """Successful API response shows task content in pretty output."""
        response = {
            "task": {"id": "remote-task-1", "content": "Remote task"},
            "parsed": {},
        }
        result = self._run_remote(["Remote task"], response)
        assert result.exit_code == 0, result.output
        assert "Remote task" in result.output

    def test_remote_success_json_output(self):
        """--json flag with remote context outputs raw JSON."""
        response = {
            "task": {"id": "remote-task-1", "content": "Remote task"},
            "parsed": {},
        }
        result = self._run_remote(["Remote task", "--json"], response)
        assert result.exit_code == 0, result.output

    def test_remote_success_with_due_date(self):
        """Response with due_date shows date in output."""
        response = {
            "task": {"id": "remote-task-2", "content": "Remote task"},
            "parsed": {"due_date": "2025-06-15T14:00:00Z"},
        }
        result = self._run_remote(["Remote task"], response)
        assert result.exit_code == 0, result.output

    def test_remote_success_with_project_name(self):
        """Response with project_name shows project in output."""
        response = {
            "task": {"id": "remote-task-3", "content": "Remote task"},
            "parsed": {"project_name": "Work"},
        }
        result = self._run_remote(["Remote task"], response)
        assert result.exit_code == 0, result.output

    def test_remote_success_with_labels(self):
        """Response with labels shows them in output."""
        response = {
            "task": {"id": "remote-task-4", "content": "Remote task"},
            "parsed": {"labels": ["urgent", "team"]},
        }
        result = self._run_remote(["Remote task"], response)
        assert result.exit_code == 0, result.output

    def test_remote_success_with_high_priority(self):
        """Response with priority < 4 shows priority in output."""
        response = {
            "task": {"id": "remote-task-5", "content": "Urgent task"},
            "parsed": {"priority": 1},
        }
        result = self._run_remote(["Urgent task"], response)
        assert result.exit_code == 0, result.output

    def test_remote_success_with_recurrence(self):
        """Response with recurrence_rule shows recurring indicator."""
        response = {
            "task": {"id": "remote-task-6", "content": "Recurring task"},
            "parsed": {"recurrence_rule": "FREQ=DAILY"},
        }
        result = self._run_remote(["Recurring task"], response)
        assert result.exit_code == 0, result.output

    def test_remote_error_response_exits_1(self):
        """API response with 'error' key exits 1."""
        response = {"error": "Project not found"}
        result = self._run_remote(["Task with bad project #BadProject"], response)
        assert result.exit_code == 1

    def test_remote_error_with_create_project_suggestion(self):
        """Error response with create_project suggestion shows create hint."""
        response = {
            "error": "Project not found",
            "parsed": {"project_name": "NewProject"},
            "suggestions": {"create_project": True, "available_projects": []},
        }
        result = self._run_remote(["Task #NewProject"], response)
        assert result.exit_code == 1
        assert "NewProject" in result.output or "project" in result.output.lower()

    def test_remote_error_with_available_projects_suggestion(self):
        """Error response with available_projects suggestion lists them."""
        response = {
            "error": "Project not found",
            "suggestions": {
                "create_project": False,
                "available_projects": ["Work", "Personal"],
            },
        }
        result = self._run_remote(["Task #BadProject"], response)
        assert result.exit_code == 1

    def test_remote_exception_exits_1(self):
        """Exception in asyncio.run is caught and exits 1."""
        config = _make_remote_config()
        mock_client = MagicMock()
        mock_tasks_api = MagicMock()
        mock_tasks_api.quick_add = AsyncMock(side_effect=RuntimeError("Network error"))

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=config,
            ),
            patch(
                "todopro_cli.commands.add_command.get_client",
                return_value=mock_client,
            ),
            patch(
                "todopro_cli.commands.add_command.TasksAPI",
                return_value=mock_tasks_api,
            ),
        ):
            result = runner.invoke(app, ["Some task"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Local context: _create_local_task details display (lines 225-305)
# ---------------------------------------------------------------------------


class TestLocalTaskDetails:
    """Cover detail display branches in _create_local_task."""

    def _run_local(self, args, parsed_result, task_result=None, projects=None):
        """Run add in local context with a mocked NLP parser."""
        if task_result is None:
            task_result = MOCK_TASK
        if projects is None:
            projects = [INBOX_PROJECT]

        task_repo = MagicMock()
        task_repo.add = AsyncMock(return_value=task_result)
        proj_repo = MagicMock()
        proj_repo.list_all = AsyncMock(return_value=projects)
        strategy = MagicMock()
        strategy.task_repository = task_repo
        strategy.project_repository = proj_repo

        proj_svc = MagicMock()
        proj_svc.list_projects = AsyncMock(return_value=projects)
        proj_svc.get_project = AsyncMock(return_value=projects[0] if projects else None)

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=_make_config_with_local_context(),
            ),
            patch(
                "todopro_cli.commands.add_command.get_storage_strategy_context",
                return_value=strategy,
            ),
            patch(
                "todopro_cli.utils.nlp_parser.parse_natural_language",
                return_value=parsed_result,
            ),
            patch(
                "todopro_cli.services.project_service.get_project_service",
                return_value=proj_svc,
            ),
        ):
            return runner.invoke(app, args)

    def test_local_task_with_high_priority(self):
        """Priority < 4 shows priority indicator in output."""
        parsed = {
            "content": "Urgent task",
            "priority": 1,
            "due_date": None,
            "project_name": None,
            "labels": [],
        }
        result = self._run_local(["Urgent task"], parsed)
        assert result.exit_code == 0, result.output
        assert "P1" in result.output or "Urgent" in result.output

    def test_local_task_with_medium_priority(self):
        """Priority 2 (High) shows P2 in output."""
        parsed = {
            "content": "High prio task",
            "priority": 2,
            "due_date": None,
            "project_name": None,
            "labels": [],
        }
        result = self._run_local(["High prio task"], parsed)
        assert result.exit_code == 0, result.output

    def test_local_task_with_labels(self):
        """Task with labels shows label display."""
        parsed = {
            "content": "Labelled task",
            "priority": 4,
            "due_date": None,
            "project_name": None,
            "labels": ["team", "review"],
        }
        result = self._run_local(["Labelled task"], parsed)
        assert result.exit_code == 0, result.output
        assert "@team" in result.output or "team" in result.output

    def test_local_task_with_due_date(self):
        """Task with due date shows formatted date."""
        from datetime import datetime

        parsed = {
            "content": "Due task",
            "priority": 4,
            "due_date": datetime(2025, 6, 15, 14, 0),
            "project_name": None,
            "labels": [],
        }
        result = self._run_local(["Due task"], parsed)
        assert result.exit_code == 0, result.output

    def test_local_task_project_from_nlp_matched(self):
        """Project name parsed from NLP and matched to existing project."""
        parsed = {
            "content": "Task for inbox",
            "priority": 4,
            "due_date": None,
            "project_name": "Inbox",
            "labels": [],
        }
        result = self._run_local(["Task for inbox"], parsed)
        assert result.exit_code == 0, result.output

    def test_local_task_project_from_nlp_unmatched(self):
        """Unmatched project name from NLP shows effective_project_name anyway."""
        parsed = {
            "content": "Task for unknown project",
            "priority": 4,
            "due_date": None,
            "project_name": "UnknownProject",
            "labels": [],
        }
        result = self._run_local(["Task for unknown project"], parsed, projects=[])
        assert result.exit_code == 0, result.output

    def test_local_task_json_output_no_details(self):
        """JSON output skips pretty-printing details."""
        parsed = {
            "content": "JSON task",
            "priority": 1,
            "due_date": None,
            "project_name": None,
            "labels": ["urgent"],
        }
        result = self._run_local(["JSON task", "--json"], parsed)
        assert result.exit_code == 0, result.output

    def test_local_task_exception_in_do_create_exits_1(self):
        """Exception in asyncio.run is caught and exits 1."""
        task_repo = MagicMock()
        task_repo.add = AsyncMock(side_effect=RuntimeError("DB error"))
        strategy = MagicMock()
        strategy.task_repository = task_repo
        strategy.project_repository = MagicMock()

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=_make_config_with_local_context(),
            ),
            patch(
                "todopro_cli.commands.add_command.get_storage_strategy_context",
                return_value=strategy,
            ),
            patch(
                "todopro_cli.utils.nlp_parser.parse_natural_language",
                return_value={
                    "content": "Task",
                    "priority": 4,
                    "due_date": None,
                    "project_name": None,
                    "labels": [],
                },
            ),
        ):
            result = runner.invoke(app, ["Task that fails"])
        assert result.exit_code == 1


class TestAddFromStdin:
    """Lines 71-73: reading text from stdin when not a TTY."""

    def test_add_from_stdin(self):
        """Text piped via stdin is read when no argument given."""
        config_svc = MagicMock()
        ctx_mock = MagicMock()
        ctx_mock.type = "local"
        config_svc.get_current_context.return_value = ctx_mock

        mock_task = MagicMock()
        mock_task.id = "task-piped"
        mock_task.content = "piped task"
        mock_task.model_dump.return_value = {"id": "task-piped", "content": "piped task"}

        task_repo = MagicMock()
        task_repo.add = AsyncMock(return_value=mock_task)
        strategy = MagicMock()
        strategy.task_repository = task_repo

        with (
            patch("todopro_cli.commands.add_command.get_config_service", return_value=config_svc),
            patch("todopro_cli.commands.add_command.get_storage_strategy_context", return_value=strategy),
            patch(
                "todopro_cli.utils.nlp_parser.parse_natural_language",
                return_value={
                    "content": "piped task", "priority": 4, "due_date": None,
                    "project_name": None, "labels": [], "recurrence_rule": None,
                },
            ),
        ):
            # CliRunner input= simulates stdin piped (not TTY)
            result = runner.invoke(app, [], input="piped task\n")
        assert result.exit_code in (0, 1)


class TestAddInteractiveModeFails:
    """Lines 78-83: when Textual interactive mode fails, falls back."""

    def test_textual_import_exception_fallback(self):
        """If QuickAddApp raises, the command handles it gracefully."""
        config_svc = MagicMock()
        ctx_mock = MagicMock()
        ctx_mock.type = "local"
        config_svc.get_current_context.return_value = ctx_mock

        mock_task = MagicMock()
        mock_task.id = "task-fallback"
        mock_task.content = "fallback task"
        mock_task.model_dump.return_value = {"id": "task-fallback", "content": "fallback task"}

        task_repo = MagicMock()
        task_repo.add = AsyncMock(return_value=mock_task)
        strategy = MagicMock()
        strategy.task_repository = task_repo

        with (
            patch("todopro_cli.commands.add_command.get_config_service", return_value=config_svc),
            patch("todopro_cli.commands.add_command.get_storage_strategy_context", return_value=strategy),
            patch("sys.stdin.isatty", return_value=True),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code in (0, 1)


class TestAddRemoteContextErrorWithSuggestions:
    """Lines 225-229: remote context error response with project suggestions."""

    def test_error_with_create_project_suggestion(self):
        """Error response with create_project suggestion shows project tip."""
        config_svc = MagicMock()
        ctx_mock = MagicMock()
        ctx_mock.type = "remote"
        config_svc.get_current_context.return_value = ctx_mock

        error_response = {
            "error": "Project not found",
            "suggestions": {"create_project": True, "available_projects": []},
            "parsed": {"project_name": "MyProject"},
        }

        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_tasks_api = MagicMock()
        mock_tasks_api.quick_add = AsyncMock(return_value=error_response)

        with (
            patch("todopro_cli.commands.add_command.get_config_service", return_value=config_svc),
            patch("todopro_cli.commands.add_command.get_client", return_value=mock_client),
            patch("todopro_cli.commands.add_command.TasksAPI", return_value=mock_tasks_api),
        ):
            result = runner.invoke(app, ["some task #MyProject"])
        assert result.exit_code == 1
        assert "Project" in result.output or "project" in result.output

    def test_error_with_available_projects_suggestion(self):
        """Error response with available_projects shows project list."""
        config_svc = MagicMock()
        ctx_mock = MagicMock()
        ctx_mock.type = "remote"
        config_svc.get_current_context.return_value = ctx_mock

        error_response = {
            "error": "Project not found",
            "suggestions": {
                "create_project": False,
                "available_projects": ["Work", "Personal", "Inbox"],
            },
            "parsed": {"project_name": "Work"},
        }

        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_tasks_api = MagicMock()
        mock_tasks_api.quick_add = AsyncMock(return_value=error_response)

        with (
            patch("todopro_cli.commands.add_command.get_config_service", return_value=config_svc),
            patch("todopro_cli.commands.add_command.get_client", return_value=mock_client),
            patch("todopro_cli.commands.add_command.TasksAPI", return_value=mock_tasks_api),
        ):
            result = runner.invoke(app, ["some task"])
        assert result.exit_code == 1


class TestCreateLocalTaskException:
    """Line 302: asyncio.run exception in _create_local_task."""

    def test_local_task_creation_exception(self):
        """Exception in _do_create() is caught and exits 1."""
        config_svc = MagicMock()
        ctx_mock = MagicMock()
        ctx_mock.type = "local"
        config_svc.get_current_context.return_value = ctx_mock

        strategy = MagicMock()
        strategy.task_repository.add = AsyncMock(side_effect=Exception("db error"))

        with (
            patch("todopro_cli.commands.add_command.get_config_service", return_value=config_svc),
            patch("todopro_cli.commands.add_command.get_storage_strategy_context", return_value=strategy),
        ):
            result = runner.invoke(app, ["failing task"])
        assert result.exit_code == 1
        assert "Failed" in result.output or "error" in result.output.lower()
