"""Unit tests for archive_command (archive/unarchive projects).

Note: this app compiles to a single TyperCommand named 'project' (not a
group), so we invoke it WITHOUT the subcommand name prefix.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.archive_command import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(project_id="proj-abc", name="My Project"):
    project = MagicMock()
    project.id = project_id
    project.name = name
    project.model_dump.return_value = {"id": project_id, "name": name}
    return project


def _invoke_archive(args, project=None, resolve_uuid_result=None):
    """Invoke archive command with service mocks pre-wired.

    ``args`` should NOT include the subcommand name 'project'; just the
    positional argument and any options (e.g. ``["proj-abc"]``).
    """
    mock_project = project or _make_project()
    resolved_id = resolve_uuid_result or mock_project.id

    mock_service = MagicMock()
    mock_service.archive_project = AsyncMock(return_value=mock_project)
    mock_service.repository = MagicMock()

    with patch(
        "todopro_cli.commands.archive_command.get_project_service",
        return_value=mock_service,
    ):
        with patch(
            "todopro_cli.commands.archive_command.resolve_project_uuid",
            new_callable=AsyncMock,
            return_value=resolved_id,
        ):
            return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# archive project tests
# ---------------------------------------------------------------------------


class TestArchiveProject:
    """Tests for 'archive project' subcommand (invoked as top-level command)."""

    def test_archive_project_success(self):
        result = _invoke_archive(["proj-abc"])
        assert result.exit_code == 0

    def test_archive_project_shows_archived_message(self):
        result = _invoke_archive(["proj-abc"])
        assert "archived" in result.output.lower()

    def test_archive_project_calls_service(self):
        project = _make_project("proj-xyz")
        mock_service = MagicMock()
        mock_service.archive_project = AsyncMock(return_value=project)
        mock_service.repository = MagicMock()

        with patch(
            "todopro_cli.commands.archive_command.get_project_service",
            return_value=mock_service,
        ):
            with patch(
                "todopro_cli.commands.archive_command.resolve_project_uuid",
                new_callable=AsyncMock,
                return_value="proj-xyz",
            ):
                runner.invoke(app, ["proj-xyz"])
        mock_service.archive_project.assert_awaited_once_with("proj-xyz")

    def test_archive_project_resolves_uuid(self):
        mock_service = MagicMock()
        mock_service.archive_project = AsyncMock(return_value=_make_project())
        mock_service.repository = MagicMock()

        resolve_mock = AsyncMock(return_value="proj-full-uuid")
        with patch(
            "todopro_cli.commands.archive_command.get_project_service",
            return_value=mock_service,
        ):
            with patch(
                "todopro_cli.commands.archive_command.resolve_project_uuid",
                resolve_mock,
            ):
                runner.invoke(app, ["proj-short"])
        resolve_mock.assert_awaited_once_with("proj-short", mock_service.repository)

    def test_archive_project_default_output_format(self):
        result = _invoke_archive(["proj-abc"])
        assert result.exit_code == 0  # table output (default) should not error

    def test_archive_project_json_output(self):
        result = _invoke_archive(["proj-abc", "--output", "json"])
        assert result.exit_code == 0

    def test_archive_project_service_error_exits_nonzero(self):
        mock_service = MagicMock()
        mock_service.archive_project = AsyncMock(side_effect=Exception("DB error"))
        mock_service.repository = MagicMock()

        with patch(
            "todopro_cli.commands.archive_command.get_project_service",
            return_value=mock_service,
        ):
            with patch(
                "todopro_cli.commands.archive_command.resolve_project_uuid",
                new_callable=AsyncMock,
                return_value="proj-abc",
            ):
                result = runner.invoke(app, ["proj-abc"])
        assert result.exit_code != 0

    def test_archive_project_missing_id_exits_nonzero(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0

    def test_archive_project_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "project" in result.output.lower() or "archive" in result.output.lower()


# ---------------------------------------------------------------------------
# CLI structure
# ---------------------------------------------------------------------------


class TestArchiveCommandStructure:
    """Tests for overall archive command structure."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_app_accepts_project_id(self):
        """Verify PROJECT_ID argument is accepted (listed in help)."""
        result = runner.invoke(app, ["--help"])
        assert "PROJECT_ID" in result.output or "project" in result.output.lower()
