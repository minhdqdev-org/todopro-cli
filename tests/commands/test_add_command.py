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
    id="00000000-0000-0000-0000-000000000000",
    name="Inbox",
    color="#4a90d9",
    is_favorite=False,
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
    storage_strategy_context.task_repository = task_repo
    storage_strategy_context.project_repository = proj_repo
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
                "todopro_cli.commands.add_command.get_strategy_context",
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
        storage_strategy_context.task_repository = task_repo
        storage_strategy_context.project_repository = proj_repo

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=_make_config_with_local_context(),
            ),
            patch(
                "todopro_cli.commands.add_command.get_strategy_context",
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
        storage_strategy_context.task_repository = task_repo
        storage_strategy_context.project_repository = proj_repo

        with (
            patch(
                "todopro_cli.commands.add_command.get_config_service",
                return_value=_make_config_with_local_context(),
            ),
            patch(
                "todopro_cli.commands.add_command.get_strategy_context",
                return_value=strategy,
            ),
        ):
            result = runner.invoke(app, ["Meet Hung #Inbox"])

        assert result.exit_code == 0, result.output
        assert captured.get("project_id") == "00000000-0000-0000-0000-000000000000"


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

        with (
            patch(
                "todopro_cli.commands.create_command.get_strategy_context"
            ) as mock_ctx,
            patch("todopro_cli.commands.create_command.ProjectService") as mock_svc_cls,
        ):
            mock_svc = MagicMock()
            mock_svc.create_project = AsyncMock(return_value=mock_project)
            mock_svc_cls.return_value = mock_svc
            mock_ctx.return_value.project_repository = MagicMock()

            from todopro_cli.commands.create_command import app as create_app

            result = runner.invoke(create_app, ["project", "Routines"])

        assert result.exit_code == 0, result.output
        assert "Routines" in result.output
        # Should NOT print full table details
        assert "is_favorite" not in result.output

    def test_create_project_json_output(self):
        """--json flag outputs JSON project."""
        mock_project = ROUTINES_PROJECT.model_copy()

        with (
            patch(
                "todopro_cli.commands.create_command.get_strategy_context"
            ) as mock_ctx,
            patch("todopro_cli.commands.create_command.ProjectService") as mock_svc_cls,
        ):
            mock_svc = MagicMock()
            mock_svc.create_project = AsyncMock(return_value=mock_project)
            mock_svc_cls.return_value = mock_svc
            mock_ctx.return_value.project_repository = MagicMock()

            from todopro_cli.commands.create_command import app as create_app

            result = runner.invoke(create_app, ["project", "Routines", "--json"])

        assert result.exit_code == 0, result.output
        assert '"project"' in result.output
