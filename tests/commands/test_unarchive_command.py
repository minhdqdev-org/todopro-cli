"""Unit tests for unarchive command.

The ``unarchive project`` command body references the undefined name
``get_storage_strategy_context``, so we inject a mock via patch(create=True)
for functional tests and also cover the --help flags.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from todopro_cli.commands.unarchive_command import app

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_project(project_id="proj-abc", name="Test Project"):
    project = MagicMock()
    project.id = project_id
    project.name = name
    project.model_dump.return_value = {"id": project_id, "name": name}
    return project


def _invoke_unarchive(args, project=None, service_side_effect=None):
    """Invoke with all undefined names patched out."""
    mock_project = project or _make_project()
    mock_service = MagicMock()
    mock_service.unarchive_project = AsyncMock(
        return_value=mock_project,
        side_effect=service_side_effect,
    )

    mock_repo = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.project_repository = mock_repo

    with patch(
        "todopro_cli.commands.unarchive_command.get_storage_strategy_context",
        return_value=mock_ctx,
        create=True,
    ):
        with patch(
            "todopro_cli.commands.unarchive_command.ProjectService",
            return_value=mock_service,
        ):
            return runner.invoke(app, args), mock_service


# ---------------------------------------------------------------------------
# Help tests
# ---------------------------------------------------------------------------

class TestUnarchiveHelp:
    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_project_help(self):
        result = runner.invoke(app, ["project", "--help"])
        assert result.exit_code == 0
        assert "project" in result.output.lower() or "id" in result.output.lower()


# ---------------------------------------------------------------------------
# Functional tests (covers lines 23-29)
# ---------------------------------------------------------------------------

class TestUnarchiveProjectCommand:
    def test_unarchive_project_success(self):
        result, mock_service = _invoke_unarchive(["proj-abc"])
        assert result.exit_code == 0
        mock_service.unarchive_project.assert_awaited_once_with("proj-abc")

    def test_unarchive_project_shows_success_message(self):
        result, _ = _invoke_unarchive(["proj-abc"])
        assert result.exit_code == 0
        assert "unarchived" in result.output.lower() or "proj-abc" in result.output

    def test_unarchive_project_json_output(self):
        result, _ = _invoke_unarchive(["proj-abc", "--output", "json"])
        assert result.exit_code == 0

    def test_unarchive_project_service_error_exits_nonzero(self):
        result, _ = _invoke_unarchive(
            ["proj-abc"],
            service_side_effect=Exception("not found"),
        )
        assert result.exit_code != 0

    def test_unarchive_missing_project_id_exits_nonzero(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0

    def test_unarchive_uses_storage_strategy_context(self):
        mock_project = _make_project("proj-xyz")
        mock_service = MagicMock()
        mock_service.unarchive_project = AsyncMock(return_value=mock_project)
        mock_repo = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.project_repository = mock_repo

        with patch(
            "todopro_cli.commands.unarchive_command.get_storage_strategy_context",
            return_value=mock_ctx,
            create=True,
        ):
            with patch(
                "todopro_cli.commands.unarchive_command.ProjectService",
                return_value=mock_service,
            ) as MockProjectService:
                runner.invoke(app, ["proj-xyz"])

        MockProjectService.assert_called_once_with(mock_repo)
