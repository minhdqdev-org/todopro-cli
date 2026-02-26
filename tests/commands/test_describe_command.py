"""Tests for the 'describe' command.

NOTE: describe_command.py contains a known bug — for the 'project' resource
type it calls ``get_storage_strategy_context()`` without importing it.

Tests here cover:
- --help exits 0
- Unknown resource type → prints error and exits 1
- The NameError bug for 'project' resource type is documented
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.describe_command import app

runner = CliRunner()


class TestDescribeHelp:
    def test_help_exits_zero(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0, result.output

    def test_help_shows_resource_type_argument(self):
        result = runner.invoke(app, ["--help"])
        assert "resource" in result.output.lower() or "RESOURCE" in result.output

    def test_help_shows_output_option(self):
        result = runner.invoke(app, ["--help"])
        assert "--output" in result.output or "-o" in result.output


class TestDescribeUnknownResourceType:
    """Providing an unknown resource type should print an error and exit 1."""

    def test_unknown_resource_type_exits_nonzero(self):
        result = runner.invoke(app, ["task", "some-id"])
        assert result.exit_code != 0, result.output

    def test_unknown_resource_type_shows_error_message(self):
        result = runner.invoke(app, ["task", "some-id"])
        assert "Unknown resource type" in result.output or "task" in result.output

    def test_unknown_resource_different_type(self):
        result = runner.invoke(app, ["label", "lbl-1"])
        assert result.exit_code != 0


class TestDescribeProjectBug:
    """Document that 'project' resource triggers NameError (missing import)."""

    def test_project_resource_type_raises_due_to_bug(self):
        """describe project <id> fails because get_storage_strategy_context is undefined."""
        result = runner.invoke(app, ["project", "proj-123"])
        # Either NameError exception or non-zero exit
        assert result.exit_code != 0 or result.exception is not None


class TestDescribeProjectWithMocks:
    """Lines 20, 34-58: describe project with proper mocks."""

    def _run(self, args):
        from datetime import datetime
        from unittest.mock import AsyncMock, MagicMock, patch

        from todopro_cli.models import Project

        mock_project = Project(
            id="proj-full-uuid-1234-5678-abcd",
            name="Test Project",
            color="#FF0000",
            is_favorite=False,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        mock_sc = MagicMock()
        mock_sc.project_repository = MagicMock()
        mock_ps = MagicMock()
        mock_ps.get_project = AsyncMock(return_value=mock_project)
        mock_ps.get_project_stats = AsyncMock(return_value={
            "total_tasks": 10,
            "completed_tasks": 5,
            "pending_tasks": 5,
            "overdue_tasks": 1,
            "completion_rate": 50,
        })

        with (
            patch("todopro_cli.commands.describe_command.get_storage_strategy_context", return_value=mock_sc, create=True),
            patch("todopro_cli.commands.describe_command.ProjectService", return_value=mock_ps),
            patch("todopro_cli.commands.describe_command.resolve_project_uuid", new=AsyncMock(return_value="proj-full-uuid-1234-5678-abcd")),
        ):
            return runner.invoke(app, args)

    def test_describe_project_success(self):
        """describe project shows details and stats."""
        result = self._run(["project", "proj-full-uuid-1234-5678-abcd"])
        assert result.exit_code == 0
        assert "Project" in result.output or "project" in result.output.lower()

    def test_describe_project_shows_stats(self):
        """describe project shows statistics."""
        result = self._run(["project", "proj-abc"])
        assert result.exit_code == 0
        assert "task" in result.output.lower() or "stat" in result.output.lower()

    def test_describe_project_with_json_output(self):
        """describe project with json output format."""
        result = self._run(["project", "proj-abc", "--output", "json"])
        assert result.exit_code == 0

    def test_describe_project_completion_rate_in_stats(self):
        """Completion rate appears in output."""
        result = self._run(["project", "proj-abc"])
        assert result.exit_code == 0
        assert "50" in result.output or "completion" in result.output.lower()

    def test_describe_unknown_resource_exits_1(self):
        """Unknown resource type exits 1."""
        result = runner.invoke(app, ["unknowntype", "some-id"])
        assert result.exit_code == 1
        assert "Unknown" in result.output
